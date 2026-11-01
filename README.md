# Atlas-AI

Atlas personal AI companion: a .NET MAUI Blazor Hybrid client alongside the Python/FastAPI/Groq backend and existing Telegram agent. The Kotlin Android client remains available during migration.

## Project structure

| Directory | Purpose |
|---|---|
| `mobile/` | .NET MAUI Blazor Hybrid solution: C# core, Razor UI, Android/Windows native host and tests |\n| `android/` | Kotlin, Compose, Material 3; MVVM/repository; Retrofit/OkHttp; Room; Keystore credentials |
| `backend/app/agent/` | Existing Groq agent loop and tools |
| `backend/app/services/` | Working Markdown memory service; reserved future services |
| `backend/app/repositories/` | Existing optional GitHub memory storage |
| `backend/app/api/` | Authenticated FastAPI endpoints for Android |
| `backend/telegram/` | Existing Telegram transport |
| `backend/seed/` | Initial agent identity and memory |
| `backend/tests/` | Migration and package-import regression checks |
| `deployment/termux/` | Supervised API service, boot hook, crash recovery, rotated logs; separate Telegram helpers |
| `deployment/cloudflare/` | HTTPS tunnel connection instructions |
| `docs/` | Architecture, API contract, and setup |
| `.github/workflows/` | Android build and backend tests |

For the new C# client, open **[mobile/Atlas.sln](mobile/Atlas.sln)** in Visual Studio with the .NET 10 MAUI workload. See [the migration guide](docs/maui-migration.md). It installs alongside Kotlin as **Atlas Hybrid**, with its own cache and credentials. Connect to restore conversations held by your backend.\n\nFor the existing Kotlin client, open **android/** in Android Studio and choose **Explore demo** to start. The native app includes chat, memory search/manual creation, profile, files, status, settings, and a dark blue interface. Demo replies are explanatory local text, not AI inference. Live Android chat connects to the authenticated FastAPI backend after you configure server credentials and an HTTPS tunnel.

Start the existing Telegram agent from the repository root with `python -m backend.telegram.bot` after installing `backend/requirements.txt` and configuring `backend/.env`.

- [MAUI Blazor Hybrid client and build instructions](mobile/README.md)\n- [Setup and migration instructions](docs/setup.md)
- [Test the Android API on Render](deployment/render/README.md)
- [Termux API service installation](deployment/termux/README.md)
- [Architecture and implementation status](docs/architecture.md)
- [Android API contract](docs/api.md)
- [Android frontend details](android/README.md)
- [Legacy Telegram deployment guide](docs/telegram-legacy.md)

## Status

Android v0.5 adds workspace file controls, memory maintenance and live monitoring, building on reply recovery and supervised Termux service setup. The project also includes named persistent conversations, full server transcript restore, paged history, remembered selection, renaming, and confirmed deletion. Live chat also includes durable delivery status, waiting indicators, safe reply recovery, and confirmed resends. Existing local history is preserved by a Room migration. The Android frontend and API share a working contract: authenticated health, Groq-backed chat, memory management, agent profile, managed file access, and monitoring. Conversation metadata, full completed transcripts, bounded AI context, and duplicate-request responses persist in SQLite. Markdown memory stays compatible with Telegram. Configure backend/.env and run `python -m backend.app`; see the setup guide for HTTPS access and Termux helpers.

Task automation, multi-user accounts, and permanent tunnel setup remain future work. Android CI builds the debug APK. Backend tests cover authentication, persistence, concurrency, provider errors, model-tool memory saves, and local HTTP startup using mocked provider responses. Real Groq/tunnel/device integration requires your configured server and credentials.

Secrets stay in environment configuration. Android stores only an Atlas access token with Keystore encryption; Groq keys remain on the backend. Do not commit runtime data, credentials, or signing keys.

The GitHub repository remains `LMS147/atlas-agent`; **Atlas-AI** is the project title and checkout folder name. Renaming the GitHub repository is a separate settings change.

## License

No open-source license has been selected. See LICENSE. The source is not granted an MIT, Apache, or other open-source license by this restructuring.

### v0.5 — File controls, memory maintenance and live monitoring

The Android Files screen uploads/downloads documents through the system picker and opens UTF-8 workspace files for conflict-safe editing. The Memory screen edits/deletes saved facts and previews conservative, backed-up compaction. Server status samples real CPU/RAM/storage/uptime/API counters every ten seconds while visible, with explicit unavailable values for Android-restricted metrics. See [API contracts](docs/api.md) and [setup](docs/setup.md) for limits and operation.

