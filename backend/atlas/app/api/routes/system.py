import time
import os
from fastapi import APIRouter, Request
from backend.atlas.app.api.dependencies import Owner
from backend.atlas.app.models.api import AgentProfile, Health
from backend.atlas.app.services import memory_service as memory

router = APIRouter()

@router.get("/health", response_model=Health)
def health(request: Request, owner: Owner):
    return Health(pid=os.getpid(), uptime_seconds=max(0, int(time.monotonic() - request.app.state.started)))

@router.get("/agent", response_model=AgentProfile)
def profile(owner: Owner):
    return AgentProfile(content=memory.load_agent())
