# Atlas API v1

The FastAPI backend implements the contract used by the current Android app. Start it from the repository root with `python -m backend.app` after configuring backend/.env. It binds to `127.0.0.1:8000` by default; expose it to Android through authenticated HTTPS, such as Cloudflare Tunnel.

## Authentication

Every `/api/v1/*` route requires `Authorization: Bearer <ATLAS_API_TOKEN>`, including health. Use a separate randomly generated token with at least 32 printable ASCII characters and no whitespace. The Groq key stays on the server. This is a single-owner workspace: everyone with the token has the same access. Rotating the token does not erase server history. Multi-user accounts and token management are not implemented.

`/docs` and `/openapi.json` expose API documentation, not workspace data. Use Swagger's **Authorize** button with the Atlas token to try the protected endpoints. Missing/incorrect credentials return 401.

| Method | Route | Response |
|---|---|---|
| GET | `/api/v1/health` | `{"status":"ok","version":"0.2.0","uptime_seconds":120}` |
| POST | `/api/v1/chat` | `{"reply":"Hello!"}` |
| GET | `/api/v1/memory` | `[{"id":"stable-content-hash","section":"Projects","fact":"Build Atlas"}]` |
| POST | `/api/v1/memory` | A memory object with `id`, `section`, `fact` |
| GET | `/api/v1/agent` | `{"name":"Atlas","content":"contents of agent.md"}` |
| GET | `/api/v1/files` | `[{"name":"agent.md","path":"agent.md","directory":false,"size_bytes":1254}]` |

Health confirms successful local configuration/storage startup. It does not spend a Groq request or verify provider credentials/quota. Provider failures are reported when sending chat.

## Chat and persistence

```json
{
  "message": "Help me plan my project",
  "conversation_id": "android-my-workspace",
  "request_id": "21c37b36-981d-4214-b48c-717627d003f3"
}
```

`message` is nonblank with a maximum of 8,000 characters. `conversation_id` is 1–128 letters/digits or `.`, `_`, `:`, `-`. `request_id` is a UUID. Extra fields are rejected. Android already sends these fields.

Conversation context and request results persist in `DATA_DIR/atlas.sqlite3`. The current agent context retains up to 24 messages without splitting a tool turn. Completed requests with the same conversation, request ID, and message return the cached reply without calling Groq again. Reusing the ID with a changed message returns 409.

A failed or interrupted request is not silently run again: reuse of its ID returns 409. Some tools may have run before a failure. Review the conversation/memory before explicitly sending a new request. This prevents automatic duplicate execution, not an exactly-once guarantee for external side effects. Context/results are retained until the local database is removed; an HTTP history/reset management endpoint is not yet implemented.

Run **one API worker only**. Requests in a conversation are serialized in that process. The startup recovery policy assumes a single API process; do not use multiple workers, replicas, or development reload for the same DATA_DIR. Telegram runs separately and uses its existing independent sessions.

## Memory and files

Memory uses the existing Markdown/GitHub storage, not a second SQLite copy. Allowed sections: `User Preferences`, `Projects`, `Decisions`, `People`. POST `/memory` accepts:

```json
{"section":"Projects","fact":"Build the Atlas companion app."}
```

Facts are normalized, nonblank, and limited to 300 characters. Existing duplicate detection is retained. IDs are hashes of section and fact content, stable across reloads/reordering. Memory-full/rejected-save outcomes return 409. Local writes use file locks and atomic replacement so Telegram and the API can share the directory. For GitHub storage, its existing conditional writes can still conflict across separate hosts.

The profile is read-only. `/files` lists only `agent.md`, `memory.md`, and the local `backups` folder when present. It omits symlinks, secrets, logs, the SQLite database, and arbitrary filesystem paths. In GitHub storage mode it lists the two Markdown files. File downloading/editing, task execution, and hardware monitoring are not implemented.

## Errors

| Status | Meaning |
|---|---|
| 401 | Missing/incorrect Atlas token |
| 409 | Conflicting/incomplete request ID or memory save conflict/full memory |
| 422 | Invalid request fields |
| 429 | Groq rate limit |
| 502 | Groq connection or upstream API failure |
| 504 | Provider/agent timeout |
| 500 | Unexpected local failure; response excludes internal details |

Server configuration fails at startup if ATLAS_API_TOKEN or GROQ_API_KEY is missing/invalid. The provider key's actual permissions are checked by Groq only when making an inference request.
