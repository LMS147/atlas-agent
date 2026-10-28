"""Authenticated Atlas API. Run one worker; Telegram remains a separate process."""
from contextlib import asynccontextmanager
from functools import partial
import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from backend.app.config import Settings, load_settings
from backend.app.api.routes import chat, memory, files, system
from backend.app.repositories.sessions import SessionRepository
from backend.app.services import memory_service
from backend.app.services.chat_service import run_agent


def create_app(settings: Settings | None = None, agent_runner=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or load_settings()
        app.state.settings = config
        def initialize():
            memory_service.configure(config.data_dir)
            memory_service.ensure_files()
            return SessionRepository(config.data_dir / "atlas.sqlite3")
        app.state.sessions = await run_in_threadpool(initialize)
        app.state.agent_runner = agent_runner or partial(run_agent, api_key=config.groq_api_key)
        app.state.started = time.monotonic()
        yield

    app = FastAPI(title="Atlas AI", version="0.2.0", lifespan=lifespan)
    for module in (chat, memory, files, system):
        app.include_router(module.router, prefix="/api/v1")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logging.getLogger(__name__).error("Atlas API operation failed")
        return JSONResponse(status_code=500, content={"detail": "Atlas could not complete this operation"})

    return app

app = create_app()
