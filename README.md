# Atlas-AI

Atlas personal AI companion: a native Android app alongside the existing Python/Groq Telegram agent.

## Project structure

| Directory | Purpose |
|---|---|
| `android/` | Kotlin, Compose, Material 3; MVVM/repository; Retrofit/OkHttp; Room; Keystore credentials |
| `backend/app/agent/` | Existing Groq agent loop and tools |
| `backend/app/services/` | Working Markdown memory service; reserved future services |
| `backend/app/repositories/` | Existing optional GitHub memory storage |
| `backend/app/api/` | FastAPI route scaffolding, not a working API yet |
| `backend/telegram/` | Existing Telegram transport |
| `backend/seed/` | Initial agent identity and memory |
| `backend/tests/` | Migration and package-import regression checks |
| `deployment/termux/` | Manual Telegram start/stop/process checks |
| `deployment/cloudflare/` | Planned HTTPS tunnel integration notes |
| `docs/` | Architecture, API contract, and setup |
| `.github/workflows/` | Android build and backend tests |

Open **android/** in Android Studio and choose **Explore demo** to start. The native app includes chat, memory search/manual creation, profile, files, status, settings, and a dark blue interface. Demo replies are explanatory local text, not AI inference. Live Android chat requires the next FastAPI implementation.

Start the existing Telegram agent from the repository root with `python -m backend.telegram.bot` after installing `backend/requirements.txt` and configuring `backend/.env`.

- [Setup and migration instructions](docs/setup.md)
- [Architecture and implementation status](docs/architecture.md)
- [Proposed Android API contract](docs/api.md)
- [Android frontend details](android/README.md)
- [Legacy Telegram deployment guide](docs/telegram-legacy.md)

## Status

This change reorganizes the existing project and adds the first Android frontend. FastAPI routes, persistent server sessions, automation, file editing, monitoring metrics, tunnel configuration, and the Termux API service are not implemented. Reserved directories are intentionally tracked placeholders. Android CI has passed the unit tests and debug APK build; the `atlas-debug-apk` artifact is available in [this Actions run](https://github.com/LMS147/atlas-agent/actions/runs/40656515106). Backend CI passed all five migration tests. Device rendering and live API integration remain unverified.

Secrets stay in environment configuration. Android stores only an Atlas access token with Keystore encryption; Groq keys remain on the backend. Do not commit runtime data, credentials, or signing keys.

The GitHub repository remains `LMS147/atlas-agent`; **Atlas-AI** is the project title and checkout folder name. Renaming the GitHub repository is a separate settings change.

## License

No open-source license has been selected. See LICENSE. The source is not granted an MIT, Apache, or other open-source license by this restructuring.
