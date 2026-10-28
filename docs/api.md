# Proposed Atlas API v1

This is a new contract for the future FastAPI adapter, not a description of endpoints that exist in the Python repository today. All routes require `Authorization: Bearer <Atlas token>` and HTTPS, including health. Responses are JSON; failed calls use appropriate non-2xx status codes. The client does not follow redirects.

| Method | Route | Response |
|---|---|---|
| GET | `/api/v1/health` | `{"status":"ok","version":"0.1.0","uptime_seconds":120}` |
| POST | `/api/v1/chat` | `{"reply":"Hello!"}` |
| GET | `/api/v1/memory` | `[{"id":"stable-id","section":"Projects","fact":"Build Atlas"}]` |
| POST | `/api/v1/memory` | A memory object with stable `id`, `section`, `fact` |
| GET | `/api/v1/agent` | `{"name":"Atlas","content":"contents of agent.md"}` |
| GET | `/api/v1/files` | `[{"name":"agent.md","path":"agent.md","directory":false,"size_bytes":1254}]` |

Chat request:

```json
{
  "message": "Help me plan my project",
  "conversation_id": "android-<workspace hash>",
  "request_id": "<unique UUID>"
}
```

The server should scope sessions by authenticated principal and conversation ID, serialize messages within each session, and deduplicate request IDs. A timed-out request may already have executed; the client does not retry automatically. Do not trust a client-supplied conversation ID as an authorization boundary. Adapt `agent.py` with its actual signatures when implementing this endpoint.

Manual memory request:

```json
{"section":"Projects","fact":"Build the Atlas companion app."}
```

Use Atlas's existing sections: `User Preferences`, `Projects`, `Decisions`, `People`. Enforce the existing `memory.py` validation on the server too. Map save/reject outcomes to explicit API responses. Return stable IDs across reads; don't use a transient list index as identity.

`agent.md` is human-managed and read-only in this app. Do not expose arbitrary filesystem access: the file listing must be confined to an approved data directory and omit secrets. No file download or command execution endpoint is used by this version.

The client caches successful memory lists and messages. A failed refresh retains the previous cache with a visible error. Error response bodies are deliberately not displayed, to avoid exposing server internals or secrets.
