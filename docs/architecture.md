# Atlas-AI architecture

## Current implementation

Android: Kotlin + Jetpack Compose + Material 3, MVVM, repository interface, Retrofit/OkHttp, Room, Android Keystore. The app ID and namespace are `com.atlas.ai`. This changes the starter's earlier `com.atlas.app` identifier; it installs as a separate app from any build using that old ID.

- `core/network`: HTTPS URL validation and Retrofit construction.
- `core/database`: Room database and DAO.
- `core/security`: encrypted credential storage.
- `core/datastore`: reserved for future persistent UI preferences.
- `data/remote`, `data/local`, `data/model`, `data/repository`: API interface, entities, wire models, and repository implementation.
- `domain/model`, `domain/repository`, `domain/usecase`: shared state, repository contract, and send-message use case. The initial contract still exposes data models; fully independent domain mapping is deferred.
- `feature/chat`, `dashboard`, `memory`, `files`, `automation`, `monitoring`, `settings`: Compose screen code. Automation is currently a labelled tools placeholder.
- `navigation`: app shell, navigation drawer, and shared ViewModel.
- `ui/theme`: common colors, branding, and components.

Backend: the existing Groq agent, memory service, GitHub storage, Telegram transport, and seed files have moved into Python packages. All runtime imports use `backend.*`; launch from the repository root. This avoids the `backend/telegram` folder shadowing the external `telegram` library. Local memory continues to use `DATA_DIR`, defaulting to `./data` relative to the process working directory. Seed lookup is now relative to the relocated backend package.

## Planned API and infrastructure

The FastAPI app and route/service modules are scaffolding. They expose no endpoints yet. The Android live API contract in api.md remains proposed. API authentication, SQLite-backed server sessions, file access, tasks, monitoring, Cloudflare Tunnel, and a persistent Termux API service are future work.

The existing Python backend still uses local Markdown files or GitHub storage, with in-memory Telegram sessions. The Termux scripts manage the current Telegram process, not an API server. `healthcheck.sh` verifies process identity only.

Empty reserved directories use `.gitkeep` (Android/issue templates) or Python `__init__.py` files so they appear in GitHub. Neither placeholder indicates completed functionality.
