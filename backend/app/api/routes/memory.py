from fastapi import APIRouter, HTTPException
from backend.app.api.dependencies import Owner
from backend.app.models.api import MemoryItem, MemoryRequest, CompactRequest
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

@router.patch("/memory/{identifier}", status_code=204)
def edit_memory(identifier: str, body: MemoryRequest, owner: Owner):
    try:
        memory.change_item(identifier, body.section, body.fact)
    except KeyError:
        raise HTTPException(409, "Memory changed; refresh before editing") from None
    except ValueError as error:
        raise HTTPException(409, str(error)) from None

@router.delete("/memory/{identifier}", status_code=204)
def delete_memory(identifier: str, owner: Owner):
    try:
        memory.change_item(identifier)
    except KeyError:
        raise HTTPException(409, "Memory changed; refresh before deleting") from None

@router.get("/memory/compact")
def preview_compact(owner: Owner):
    return memory.compact_plan()

@router.post("/memory/compact")
def compact(body: CompactRequest, owner: Owner):
    try:
        return memory.compact_plan(body.revision)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
