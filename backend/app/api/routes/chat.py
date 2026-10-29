import logging
from fastapi import APIRouter, HTTPException, Request
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from backend.app.api.dependencies import Owner
from backend.app.models.api import ChatReply, ChatRequest
from backend.app.repositories.sessions import RequestConflict, ConversationGone, ConversationMissing

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat", response_model=ChatReply)
def chat(body: ChatRequest, request: Request, owner: Owner):
    try:
        reply = request.app.state.sessions.chat(owner, body.conversation_id, str(body.request_id), body.message, request.app.state.agent_runner, require_existing=body.require_existing)
        return ChatReply(reply=reply)
    except ConversationMissing as exc:
        raise HTTPException(404, str(exc)) from None
    except ConversationGone as exc:
        raise HTTPException(410, str(exc)) from None
    except RequestConflict as exc:
        raise HTTPException(409, str(exc)) from None
    except RateLimitError as error:
        try:
            delay = max(1,min(3600,int(error.response.headers.get("Retry-After","30"))))
        except (ValueError,TypeError):
            delay = 30
        raise HTTPException(429, "AI provider is rate limited; try again later", headers={"Retry-After":str(delay)}) from None
    except (APITimeoutError, TimeoutError):
        raise HTTPException(504, "AI provider timed out") from None
    except (APIConnectionError, APIStatusError):
        raise HTTPException(502, "AI provider is unavailable") from None
    except Exception:
        # Do not expose/log prompts, access tokens, or upstream response bodies.
        logger.error("Atlas chat request failed")
        raise HTTPException(500, "Atlas could not complete this request") from None
