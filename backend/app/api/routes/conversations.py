from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from backend.app.api.dependencies import Owner
from backend.app.models.api import ConversationItem, ConversationName, MessagePage, ChatRequestStatus
from backend.app.repositories.sessions import ConversationMissing, ConversationGone, RequestConflict

router = APIRouter()
ConversationId = Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9._:-]+$")]

def operation(function, *args):
    try:
        return function(*args)
    except ConversationMissing as error:
        raise HTTPException(404, str(error)) from None
    except ConversationGone as error:
        raise HTTPException(410, str(error)) from None
    except RequestConflict as error:
        raise HTTPException(409, str(error)) from None

@router.get("/conversations", response_model=list[ConversationItem])
def list_conversations(request: Request, owner: Owner, include_deleted: bool = False):
    return request.app.state.sessions.list_conversations(owner, include_deleted)

@router.post("/conversations", response_model=ConversationItem, status_code=201)
def create_conversation(body: ConversationName, request: Request, owner: Owner):
    return request.app.state.sessions.create_conversation(owner, body.title)

@router.patch("/conversations/{identifier}", response_model=ConversationItem)
def rename_conversation(identifier: ConversationId, body: ConversationName, request: Request, owner: Owner):
    return operation(request.app.state.sessions.rename_conversation, owner, identifier, body.title)

@router.delete("/conversations/{identifier}", status_code=204)
def delete_conversation(identifier: ConversationId, request: Request, owner: Owner):
    operation(request.app.state.sessions.delete_conversation, owner, identifier)
    return Response(status_code=204)

@router.get("/conversations/{identifier}/messages", response_model=MessagePage)
def messages(identifier: ConversationId, request: Request, owner: Owner,
             before: Annotated[int | None, Query(gt=0)] = None,
             limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return operation(request.app.state.sessions.messages, owner, identifier, before, limit)

@router.get("/conversations/{identifier}", response_model=ConversationItem)
def conversation(identifier: ConversationId, request: Request, owner: Owner):
    return operation(request.app.state.sessions.get_conversation, owner, identifier)

@router.get("/conversations/{identifier}/requests/{request_id}", response_model=ChatRequestStatus)
def request_status(identifier: ConversationId, request_id: UUID, request: Request, owner: Owner):
    return operation(request.app.state.sessions.request_status, owner, identifier, str(request_id))
