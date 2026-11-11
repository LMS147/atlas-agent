"""Authenticated Atlas API. Run one worker; Telegram remains a separate process."""
from contextlib import asynccontextmanager
from functools import partial
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from filelock import FileLock, Timeout
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from backend.atlas.app.config import Settings, load_settings
from backend.atlas.app.api.routes import chat, memory, files, system, conversations
from backend.atlas.app.repositories.sessions import SessionRepository
from backend.atlas.app.services import memory_service
from backend.atlas.app.services.chat_service import run_agent, run_agent_stream


def create_app(settings: Settings | None = None, agent_runner=None, streaming_runner=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or load_settings()
        config.data_dir.mkdir(parents=True, exist_ok=True)
        lease = FileLock(str(config.data_dir / ".atlas-api.lock"), timeout=0)
        try:
            lease.acquire()
        except Timeout:
            raise RuntimeError("Another Atlas API process is already using DATA_DIR") from None
        try:
            app.state.settings = config
            def initialize():
                memory_service.configure(config.data_dir)
                memory_service.ensure_files()
                return SessionRepository(config.data_dir / "atlas.sqlite3")
            app.state.sessions = await run_in_threadpool(initialize)
            app.state.agent_runner = agent_runner or partial(run_agent, api_key=config.groq_api_key)
            app.state.streaming_runner = streaming_runner or partial(run_agent_stream, api_key=config.groq_api_key)
            app.state.stream_slots = threading.BoundedSemaphore(4)
            app.state.stream_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="atlas-chat")
            app.state.started = time.monotonic()
            app.state.ready = True
            yield
        finally:
            app.state.ready = False
            if hasattr(app.state, "stream_pool"):
                await run_in_threadpool(app.state.stream_pool.shutdown, wait=True)
            lease.release()

    app = FastAPI(title="Atlas AI", version="0.5.0", lifespan=lifespan)
    app.state.ready = False

    @app.get("/healthz", include_in_schema=False)
    def readiness():
        # Public platform probe; never return tokens, version, metrics or workspace data.
        return Response(status_code=204 if app.state.ready else 503)

    app.state.metrics_lock = threading.Lock()
    app.state.metrics = dict(requests=0, errors=0, active_requests=0)

    @app.middleware("http")
    async def count_requests(request: Request, call_next):
        with app.state.metrics_lock:
            app.state.metrics["requests"] += 1
            app.state.metrics["active_requests"] += 1
        failed = False
        try:
            response = await call_next(request)
            failed = response.status_code >= 500
            return response
        except Exception:
            failed = True
            raise
        finally:
            with app.state.metrics_lock:
                app.state.metrics["active_requests"] -= 1
                app.state.metrics["errors"] += int(failed)

    for module in (chat, memory, files, system, conversations):
        app.include_router(module.router, prefix="/api/v1")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logging.getLogger(__name__).error("Atlas API operation failed")
        return JSONResponse(status_code=500, content={"detail": "Atlas could not complete this operation"})

    return app

app = create_app()
