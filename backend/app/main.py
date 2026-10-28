"""FastAPI scaffold. No data routes are exposed until authentication is implemented."""
from fastapi import FastAPI
from backend.app.api.routes import chat, memory, files, tasks, system

app = FastAPI(title="Atlas AI", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
for module in (chat, memory, files, tasks, system):
    app.include_router(module.router, prefix="/api/v1")
