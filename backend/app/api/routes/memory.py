from fastapi import APIRouter, HTTPException
from backend.app.api.dependencies import Owner
from backend.app.models.api import MemoryItem, MemoryRequest
from backend.app.services import memory_service as memory

router = APIRouter()

@router.get("/memory", response_model=list[MemoryItem])
def list_memory(owner: Owner):
    return memory.list_items()

@router.post("/memory", response_model=MemoryItem)
def remember(body: MemoryRequest, owner: Owner):
    status = memory.append_memory(body.section, body.fact)
    if status.startswith("rejected:"):
        raise HTTPException(409, "Atlas memory is full or the fact was rejected")
    # Existing memory deduplication is case-insensitive and permits substring matches.
    for item in memory.list_items():
        if body.fact.casefold() in item["fact"].casefold():
            return item
    raise HTTPException(409, "Memory changed during the save; refresh and check before retrying")
