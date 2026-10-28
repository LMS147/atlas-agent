import logging
from fastapi import APIRouter, HTTPException, Request
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from backend.app.api.dependencies import Owner
from backend.app.models.api import ChatReply, ChatRequest
from backend.app.repositories.sessions import RequestConflict

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat", response_model=ChatReply)
def chat(body: ChatRequest, request: Request, owner: Owner):
    try:
        reply = request.app.state.sessions.chat(owner, body.conversation_id, str(body.request_id), body.message, request.app.state.agent_runner)
        return ChatReply(reply=reply)
    except RequestConflict as exc:
        raise HTTPException(409, str(exc)) from None
    except RateLimitError:
        raise HTTPException(429, "AI provider is rate limited; try again later") from None
    except (APITimeoutError, TimeoutError):
        raise HTTPException(504, "AI provider timed out") from None
    except (APIConnectionError, APIStatusError):
        raise HTTPException(502, "AI provider is unavailable") from None
    except Exception:
        # Do not expose/log prompts, access tokens, or upstream response bodies.
        logger.error("Atlas chat request failed")
        raise HTTPException(500, "Atlas could not complete this request") from None
