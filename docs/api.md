# Atlas API v1

The FastAPI backend implements the contract used by the current Android app. Start it from the repository root with `python -m backend.app` after configuring backend/.env. It binds to `127.0.0.1:8000` by default; expose it to Android through authenticated HTTPS, such as Cloudflare Tunnel.

## Authentication

Render can use the separate public `GET /healthz` readiness probe (empty 204 after startup, 503 while not ready). It discloses no configuration or workspace information.

Every `/api/v1/*` route requires `Authorization: Bearer <ATLAS_API_TOKEN>`, including health. Use a separate randomly generated token with at least 32 printable ASCII characters and no whitespace. The Groq key stays on the server. This is a single-owner workspace: everyone with the token has the same access. Rotating the token does not erase server history. Multi-user accounts and token management are not implemented.

`/docs` and `/openapi.json` expose API documentation, not workspace data. Use Swagger's **Authorize** button with the Atlas token to try the protected endpoints. Missing/incorrect credentials return 401.

| Method | Route | Response |
|---|---|---|
| GET | `/api/v1/health` | `{"status":"ok","version":"0.5.0","uptime_seconds":120}` |
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

A failed or interrupted request is not silently run again: reuse of its ID returns 409. Some tools may have run before a failure. Review the conversation/memory before explicitly sending a new request. This prevents automatic duplicate execution, not an exactly-once guarantee for external side effects. Full completed transcripts and request results persist separately from the bounded model context. Use the conversation history/deletion endpoints below to manage saved chats.

Run **one API worker only**. Requests in a conversation are serialized in that process. The startup recovery policy assumes a single API process; do not use multiple workers, replicas, or development reload for the same DATA_DIR. Telegram runs separately and uses its existing independent sessions.

## Memory and files

Memory uses the existing Markdown/GitHub storage, not a second SQLite copy. Allowed sections: `User Preferences`, `Projects`, `Decisions`, `People`. POST `/memory` accepts:

```json
{"section":"Projects","fact":"Build the Atlas companion app."}
```

Facts are normalized, nonblank, and limited to 300 characters. Existing duplicate detection is retained. IDs are hashes of section and fact content, stable across reloads/reordering. Memory-full/rejected-save outcomes return 409. Local writes use file locks and atomic replacement so Telegram and the API can share the directory. For GitHub storage, its existing conditional writes can still conflict across separate hosts.

The profile is read-only. `/files` lists canonical documents and the local `backups` and managed `workspace` folders. It omits symlinks, secrets, logs, the SQLite database, and arbitrary filesystem paths. File controls, memory maintenance and monitoring are documented below. Task execution remains future work.

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

## Persistent conversations (v0.3)

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v1/conversations` | List saved chats, newest first |
| POST | `/api/v1/conversations` | Create a chat with `{"title":"New chat"}`; returns 201 |
| GET | `/api/v1/conversations/{id}` | Get its title, timestamps, preview, and message count |
| PATCH | `/api/v1/conversations/{id}` | Rename with `{"title":"Work projects"}` |
| DELETE | `/api/v1/conversations/{id}` | Delete messages/context; returns 204 |
| GET | `/api/v1/conversations/{id}/messages` | Read a page of the saved transcript |

These routes use the same bearer authentication. Titles contain 1–80 characters. POST returns a server-generated conversation ID; pass that ID as `conversation_id` on chat requests. The first successful turn automatically titles an unnamed chat. Message counts/previews include completed turns; failed/pending requests retain their separate deduplication records.

Message pages accept `limit` (1–100, default 50) and `before` (the previous page's `next_before`). They return `items`, `has_more`, and `next_before`. Items are in chronological sequence order and contain `seq`, `id`, `request_id`, `role`, `text`, and `created_at`. All timestamps use Unix milliseconds. Read successive pages to retrieve the entire transcript; the 24-message limit applies only to model context, not stored history.

For synchronization, `GET /conversations?include_deleted=true` also returns content-free tombstones marked `deleted=true`. A deleted ID returns 410 and cannot be recreated by an older client. Deletion during an active reply returns 409; retry after it finishes. Deletion leaves shared Markdown memories intact. This is logical deletion, not a promise of forensic secure erasure of SQLite storage.

Startup upgrades the existing SQLite schema in place and imports completed request-log entries exactly once. Their original timestamps were not recorded by older versions, so imported records use the import time and preserved request order. Existing prompt context and request IDs remain intact. Older Android clients can continue posting their fixed legacy conversation ID; those chats also appear in the history list.

The API is still a single-owner workspace with one API worker. SQLite remains on DATA_DIR's persistent storage. Back up that directory before moving servers. Telegram sessions remain separate; their in-memory conversation history is not imported into API chats.

## Read-only recovery and startup ownership (v0.4)

`GET /api/v1/conversations/{id}/requests/{request_id}` requires the same bearer token and accepts a UUID. It returns:

```json
{"request_id":"21c37b36-981d-4214-b48c-717627d003f3","status":"done","reply":"Saved reply"}
```

Statuses are `not_found`, `pending`, `done`, `failed`, or `interrupted`. Only `done` includes a reply. Checking status reads SQLite and never invokes Groq, waits for a conversation's agent lock, or creates a request. Unknown/deleted conversations return 404/410. A `not_found` result describes the current database view, not proof that an earlier network packet can never arrive; use the original UUID if explicitly retrying delivery.

New Android clients send `require_existing:true` on chat requests. Missing conversation IDs then return 404 before any agent call instead of creating empty replacement history. The default remains false for older clients that used their fixed legacy ID. Deleted IDs always return 410.

Groq 429 responses now include a bounded Retry-After delay in seconds (1–3600; default 30 if unavailable/invalid). Android displays it and requires explicit resend confirmation; it does not automatically create new inference requests.

Health now also includes the API process `pid` for the local supervisor's authenticated readiness check. It does not measure provider quota or external tunnel availability. An exclusive process lock is held for the API lifespan in DATA_DIR/.atlas-api.lock. Duplicate startups fail before memory/session initialization; OS process exit releases the lock. Use a single API worker. Termux supervision/boot setup is documented in ../deployment/termux/README.md.

### Files and memory management (v0.5)

All endpoints below require the existing bearer token. `GET /files?directory=` lists the virtual root; `workspace` and `backups` list those folders. `agent.md`, `memory.md`, and backups are read-only through Files. Only Atlas-generated `memory-YYYYMMDD-HHMMSS-microseconds.md` snapshots are exposed from the backup directory. Workspace files live in `DATA_DIR/workspace`, independently of GitHub-backed memory. Nested paths, hidden names, symlinks, credentials, databases, logs and arbitrary filesystem access are excluded.

- `POST /files/upload?name=notes.txt`: raw bytes, 5 MiB maximum, creates a new workspace file (201). Existing name returns 409; upload never overwrites.
- `GET /files/content?path=workspace/notes.txt`: raw bytes (5 MiB maximum), SHA-256 ETag. Downloads are authenticated; no public file URLs.
- `GET /files/text?path=workspace/notes.txt`: `{path,content,revision,writable}`, UTF-8 text up to 256 KiB. Binary files return 415 and should be downloaded.
- `PUT /files/text?path=workspace/notes.txt`: `{content,revision}`; revision is the SHA-256 from opening the file. Stale saves return 409. Writes are atomic and confined to workspace files.
- `PATCH /memory/{id}`: `{section,fact}` using the same section and 300-character fact rules as creation. Returns 204. Content IDs change after editing; stale IDs return 409.
- `DELETE /memory/{id}`: 204; removes the fact from future agent context, leaving chat transcripts unchanged.
- `GET /memory/compact`: preview `{revision,before_chars,after_chars,removed_entries}`.
- `POST /memory/compact`: `{revision}` applies that preview, or returns 409 if memory changed. Conservative compaction removes normalized exact duplicate bullets within their section and repeated blank lines; it does not summarize, call an LLM, discard unique facts or strip unknown Markdown. Edits/deletes/compaction use the shared memory lock and local backups (last 30); GitHub mode uses commit history.

### Monitoring (v0.5)

`GET /monitoring` samples CPU for 0.2 seconds and returns `sampled_at` (Unix milliseconds), `device_cpu_percent`, `process_cpu_percent`, `ram` (`total_bytes`, `available_bytes`, `used_bytes`), `process_rss_bytes`, `storage` (`total_bytes`, `used_bytes`, `free_bytes`), `device_uptime_seconds`, `service` (`pid`, `uptime_seconds`, Python `threads`, `requests`, `errors`, `active_requests`), and `unavailable` labels. Process CPU counts 100% per core. Storage describes the data directory's filesystem, not the app's file sizes. Counters reset when the API process restarts, count all HTTP requests and 5xx responses, and include the monitoring request itself. Android may deny `/proc/stat`, `/proc/meminfo`, `/proc/uptime` or process RSS reads: affected values are null, never invented zeroes. The app refreshes every 10 seconds while this screen is visible and the app is in the foreground; failed refreshes retain the visibly dated last sample. These are API-process metrics, not claims about Cloudflare or Telegram service health.

## Streamed chat

Authenticated health advertises `streaming_chat: true` for the streaming backend. `POST /api/v1/chat/stream` accepts the existing chat request body and returns SSE status/progress snapshots, a committed complete reply, or a sanitized error event. The ordinary chat and request-status contracts are unchanged. See [streaming protocol and recovery](chat-streaming.md) for event fields, duplicate protection, limits and upgrade steps.
