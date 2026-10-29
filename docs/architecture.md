# Atlas-AI architecture

## Current implementation

Android: Kotlin + Jetpack Compose + Material 3, MVVM, repository interface, Retrofit/OkHttp, Room, Android Keystore. The app ID and namespace are `com.atlas.ai`. This changes the starter's earlier `com.atlas.app` identifier; it installs as a separate app from any build using that old ID.

- `core/network`: HTTPS URL validation and Retrofit construction.
- `core/database`: Room database/DAO and a non-destructive v1/v2-to-v3 migrations for delivery and conversation state.
- `core/security`: encrypted credential storage.
- `core/datastore`: reserved for future persistent UI preferences.
- `data/remote`, `data/local`, `data/model`, `data/repository`: API interface, entities, wire models, and repository implementation.
- `domain/model`, `domain/repository`, `domain/usecase`: shared state, repository contract, and send-message use case. The initial contract still exposes data models; fully independent domain mapping is deferred.
- `feature/chat`, `dashboard`, `memory`, `files`, `automation`, `monitoring`, `settings`: Compose screen code. Automation is currently a labelled tools placeholder.
- `navigation`: app shell, navigation drawer, and shared ViewModel.
- `ui/theme`: common colors, branding, and components.

Backend: the existing Groq agent, memory service, GitHub storage, Telegram transport, and seed files have moved into Python packages. All runtime imports use `backend.*`; launch from the repository root. This avoids the `backend/telegram` folder shadowing the external `telegram` library. Local memory continues to use `DATA_DIR`, defaulting to `./data` relative to the process working directory. Seed lookup is now relative to the relocated backend package.

## Android live chat

The repository validates authenticated health before entering a live workspace and posts messages to /api/v1/chat through Retrofit/OkHttp. The Room cache tracks pending, sent, recoverable, and failed delivery. Reply recovery reuses the original UUID; a fresh resend requires user confirmation. The UI shows the actual configured server and connection/request state, never fabricated online status or demo replies on a failed live request.

A process restart leaves uncertain requests recoverable rather than automatically replaying them. A mutex serializes repository send/recovery operations. Deterministic reply IDs and a transactional cache completion avoid duplicate bubbles. Version 2 preserves the existing cache with an explicit migration; message upserts retain ordering.

## API and persistence

FastAPI now implements bearer-authenticated health, chat, memory list/create, agent profile, and allowlisted file listing endpoints. API configuration loads backend/.env at startup, with exported variables taking precedence. Startup initializes the existing Markdown memory and a local SQLite database at DATA_DIR/atlas.sqlite3.

Chat routes invoke the existing synchronous Groq agent from worker-thread route handlers. Conversation metadata, full completed transcripts, bounded model context, and deduplicated request results persist in SQLite; UUID request IDs prevent silent duplicate execution. Failed/interrupted requests return a conflict on replay. Per-conversation locks assume one API worker, enforced by the provided launcher. This is a single-owner API, not multi-user account authentication.

The existing Python memory backend still uses local Markdown or GitHub storage. Local file locks and atomic replacement let Telegram and the API share memory. Telegram's own conversation sessions remain in RAM and separate from API histories.

Termux has a managed termux-services/runit API service with a separate boot hook, crash backoff, rotated logs, and authenticated process-aware health. Its default start/stop/health scripts delegate to that registration, with manual fallback when unregistered. The original Telegram scripts remain under explicit *-telegram.sh names. Existing Render/Fly configurations still serve Telegram. Cloudflare instructions describe HTTPS forwarding; no tunnel is configured automatically.

## Remaining features

Task/automation modules, multi-user accounts, permanent tunnel integration, and independent domain/data mapping remain future work. Workspace file editing, memory management and monitoring are described below; the canonical profile stays read-only. Public /docs and /openapi.json describe the API; workspace routes require the Atlas token.

Reserved directories use .gitkeep or Python __init__.py. Their presence does not indicate a completed feature.

## Conversation synchronization

The server generates conversation IDs and keeps transcript rows separately from the 24-message agent context. Metadata/history routes support renaming, cursor paging, and deletion. Startup imports the older request log once, preserving IDs and message order. Deleted IDs remain reserved with content-free tombstones, preventing old clients from reviving them.

Android's Room v3 cache keys messages by workspace and conversation, persists a selected-conversation row, and hydrates completed turns by their request IDs. A confirmed server deletion purges its cache; missing history without a tombstone remains read-only locally. Saved-token startup can open cached chats during connection failures. The single-owner bearer-token model is unchanged, and Telegram sessions remain separate.

## Service ownership and read-only recovery

A file lock held over the API lifespan enforces one API process per DATA_DIR, before recovery can mark stale requests interrupted. The Termux supervisor runs that process in the foreground and restarts it after crashes. Health includes the API PID, allowing service readiness to reject a response from another process on the port.

Android recovery reads a persisted request-status endpoint without starting another inference. Unknown delivery and known failed/interrupted work have distinct confirmation paths. New clients require a known server conversation when posting chat; legacy auto-creation remains compatible for older clients. No Room migration is needed for the new text-based delivery state. Existing SSH and tunnel services remain independently managed.

### Management and monitoring

Workspace operations use a dedicated `DATA_DIR/workspace` and a cross-process file lock. Uploads exclusively create names; text edits require a SHA-256 revision and use atomic replacement. Canonical agent/memory documents are never writable through the file API. Memory mutations share Telegram's memory lock, preserve unrelated Markdown, retain backups and reject stale content IDs or compaction revisions. Android uses authenticated Retrofit operations behind the repository and Android document pickers for external file access. Monitoring uses standard-library Linux reads and process accounting, with nullable restricted metrics and a lifecycle-bound ten-second refresh. HTTP metrics are in-memory per-process counters and reset on restart.
