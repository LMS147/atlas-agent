import logging
from fastapi import APIRouter, HTTPException, Request
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from backend.atlas.app.api.dependencies import Owner
from backend.atlas.app.models.api import ChatReply, ChatRequest
from backend.atlas.app.repositories.sessions import RequestConflict, ConversationGone, ConversationMissing

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



@router.post("/chat/stream")
def stream_chat(body: ChatRequest, request: Request, owner: Owner):
    """Bounded latest-snapshot SSE; disconnect never replays or cancels tool effects."""
    import json
    import queue
    import threading
    from fastapi.responses import StreamingResponse

    state = request.app.state
    if not state.stream_slots.acquire(blocking=False):
        raise HTTPException(429, "Atlas is busy; check existing requests before retrying", headers={"Retry-After": "5"})
    events = queue.Queue(maxsize=1)
    detached = threading.Event()
    rid = str(body.request_id)
    last_progress = [0.0, None]

    def publish(kind, payload):
        if detached.is_set():
            return
        if kind == "progress":
            import time
            now = time.monotonic()
            if payload["phase"] == last_progress[1] and now - last_progress[0] < 0.05:
                return
            last_progress[:] = [now, payload["phase"]]
        event = (kind, dict(request_id=rid, **payload))
        try:
            events.put_nowait(event)
        except queue.Full:
            try: events.get_nowait()
            except queue.Empty: pass
            events.put_nowait(event)

    def work():
        try:
            def runner(history, message):
                return state.streaming_runner(history, message,
                    lambda phase, text: publish("progress", dict(phase=phase, text=text)))
            reply = state.sessions.chat(owner, body.conversation_id, rid, body.message, runner,
                                        require_existing=body.require_existing)
            # Only emit completion after the transcript and request are committed.
            publish("complete", dict(reply=reply))
        except (ConversationMissing, ConversationGone, RequestConflict) as exc:
            code = 404 if isinstance(exc, ConversationMissing) else 410 if isinstance(exc, ConversationGone) else 409
            publish("error", dict(status=code))
        except RateLimitError:
            publish("error", dict(status=429))
        except (APITimeoutError, TimeoutError):
            publish("error", dict(status=504))
        except (APIConnectionError, APIStatusError):
            publish("error", dict(status=502))
        except Exception:
            logger.error("Atlas streaming request failed")
            publish("error", dict(status=500))
        finally:
            state.stream_slots.release()

    try:
        state.stream_pool.submit(work)
    except Exception:
        state.stream_slots.release()
        raise HTTPException(503, "Atlas is stopping") from None

    def generate():
        try:
            yield "event: status\ndata: " + json.dumps(dict(request_id=rid, phase="thinking")) + "\n\n"
            while True:
                try:
                    kind, payload = events.get(timeout=10)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue
                yield "event: " + kind + "\ndata: " + json.dumps(payload, ensure_ascii=True) + "\n\n"
                if kind in {"complete", "error"}:
                    return
        finally:
            detached.set()
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
