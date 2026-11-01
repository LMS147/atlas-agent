# Streamed replies

Atlas 0.9.0 streams user-visible Groq response content through the authenticated FastAPI API into the MAUI chat screen. Tool argument fragments and provider reasoning metadata are never forwarded. Thinking status is a UI processing label, not a chain-of-thought feed. Existing ordinary chat and request-status endpoints remain compatible.

## Upgrade

1. Back up the server workspace and retain the current configuration/signing key.
2. Update the server checkout and install `backend/requirements.txt` in its existing Python environment. Restart the supervised API using the deployment's normal service controls, preserving `DATA_DIR`, token and Groq key. Use one API worker.
3. Reconnect the updated MAUI app. Authenticated `GET /api/v1/health` now advertises `streaming_chat: true`. A backend without this flag uses ordinary chat, without a speculative second inference call.
4. Build/install 0.9.0 using the permanent-signing release workflow for distributed updates. The regular CI artifact remains a development APK.
5. Test a prompt on the actual server: text should appear while the reply is generated. Disconnect during generation, reconnect, then Check for reply. Confirm exactly one completed transcript pair. Test a memory-saving request with disposable data, and check that its tool effect occurs once.

The source commit does not automatically deploy Render (`[skip render]`). No live provider token or production workspace was used in automated tests. Proxy buffering may delay display: preserve `text/event-stream`, `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no`; disable buffering in any additional reverse proxy. Never put the bearer token in a URL.

## Protocol

POST `/api/v1/chat/stream` accepts the same body and bearer authentication as `/chat`: `conversation_id`, UUID `request_id`, `message`, and `require_existing`. MAUI sends `require_existing: true`. The response is SSE over the POST response body, consumed with authenticated HttpClient, not browser EventSource.

| SSE event | JSON fields | Meaning |
|---|---|---|
| `status` | `request_id`, `phase: thinking` | Connection established; no saved reply yet |
| `progress` | `request_id`, `phase: thinking` or `replying`, `text` | Full current tentative text snapshot; replace previous text, do not append |
| `complete` | `request_id`, `reply` | Final reply committed to SQLite/transcript; replaces tentative text |
| `error` | `request_id`, numeric `status` | Sanitized failure; inspect existing request status before a fresh request |
| comment | `: heartbeat` | Keeps idle stream active; no inference or storage operation |

Progress snapshots are held in a bounded latest-value queue, so a slow client may miss intermediate snapshots but completion contains the full saved reply. Tool rounds reset tentative content to thinking. Only the final user-facing assistant turn is committed. SSE errors after headers use an error event (HTTP is already 200); pre-stream authentication, validation and admission failures use HTTP errors.

## Reliability and limits

The original durable request table and conversation lock govern streaming and ordinary chat together. Same-ID/same-message completed requests return the saved reply; mismatched messages conflict. Failed/interrupted IDs are not replayed. Client disconnection does not cancel accepted inference or tool effects: the bounded server worker finishes and saves the result. On orderly shutdown, accepted workers finish before the workspace lease is released. A crash leaves pending IDs interrupted on restart, requiring inspection before a fresh request.

Partial text is deliberately not an authoritative transcript and is not restored after process death. The app clears transient progress on errors, marks the user message recoverable for an incomplete connection, and offers the existing status check. Provider/validation errors retain the explicit resend confirmation. No automatic inference retries or fallback after a stream starts. Four streaming workers are admitted at once; excess requests receive 429 before inference. Provider turns retain the 75-second overall agent deadline, five tool-round limit and provider timeouts; the app caps stream duration, frame size and aggregate text. Large or truncated provider turns fail rather than executing incomplete tool calls.

Automated coverage includes provider delta assembly, private fragmented tool arguments, incomplete-turn rejection, authenticated SSE completion/replay/conflict, sanitized failures, admission limits, a real HTTP disconnect with eventual persistence, fragmented UTF-8 in the app parser, and saved-reply recovery without another inference. Real Groq model compatibility, tunnel buffering, device lifecycle and signed-release installation still need acceptance testing.
