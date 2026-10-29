import time
import os
from fastapi import APIRouter, Request
from backend.app.api.dependencies import Owner
from backend.app.models.api import AgentProfile, Health
from backend.app.services import memory_service as memory

router = APIRouter()

@router.get("/health", response_model=Health)
def health(request: Request, owner: Owner):
    return Health(pid=os.getpid(), uptime_seconds=max(0, int(time.monotonic() - request.app.state.started)))

@router.get("/agent", response_model=AgentProfile)
def profile(owner: Owner):
    return AgentProfile(content=memory.load_agent())

@router.get("/monitoring")
def monitoring(request: Request, owner: Owner):
    from backend.app.services.monitoring_service import snapshot
    return snapshot(request.app)
