# Atlas-AI

Atlas personal AI companion: a .NET MAUI Blazor Hybrid client alongside the Python/FastAPI/Groq backend and existing Telegram agent. The retired Kotlin Android client has been removed; use `mobile/` for the Android and Windows app.

This repository contains the Atlas mobile app and AI backend. Phone host management is maintained in [Server-management](https://github.com/LMS147/Server-management). See [Atlas backend commands](backend/README.md).

## Project structure

| Directory | Purpose |
|---|---|
| `mobile/` | .NET MAUI Blazor Hybrid solution: C# core, Razor UI, Android/Windows native host and tests |
| `backend/atlas/app/agent/` | Existing Groq agent loop and tools |
| `backend/atlas/app/services/` | Working Markdown memory service; reserved future services |
| `backend/atlas/app/repositories/` | Existing optional GitHub memory storage |
| `backend/atlas/app/api/` | Authenticated FastAPI endpoints for Android |
| `backend/atlas/telegram/` | Existing Telegram transport |
| `backend/atlas/seed/` | Initial agent identity and memory |
| `backend/atlas/tests/` | Atlas application regression checks |
| `docs/` | Architecture, API contract, and setup |
| `.github/workflows/` | Android build and backend tests |

For the new C# client, open **[mobile/Atlas.sln](mobile/Atlas.sln)** in Visual Studio with the .NET 10 MAUI workload. See [the migration guide](docs/maui-migration.md). It installs alongside Kotlin as **Atlas**, with its own cache and credentials. Connect to restore conversations held by your backend.

Start the existing Telegram agent from the repository root with `python -m backend.atlas.telegram.bot` after installing `backend/requirements.txt` and configuring `backend/.env`.

- [MAUI Blazor Hybrid client and build instructions](mobile/README.md)
- [Setup and migration instructions](docs/setup.md)
- [Test the Android API on Render](deployment/render/README.md)
- [Termux API service installation](https://github.com/LMS147/Server-management/blob/main/deployment/termux/README.md)
- [Architecture and implementation status](docs/architecture.md)
- [Android API contract](docs/api.md)
- [Legacy Telegram deployment guide](docs/telegram-legacy.md)

## Status

Android v0.5 adds workspace file controls and memory maintenance, building on reply recovery and supervised Termux service setup. The project also includes named persistent conversations, full server transcript restore, paged history, remembered selection, renaming, and confirmed deletion. Live chat also includes durable delivery status, waiting indicators, safe reply recovery, and confirmed resends. Existing local history is preserved by a Room migration. The Android frontend and API share a working contract: authenticated health, Groq-backed chat, memory management, agent profile and managed file access. Conversation metadata, full completed transcripts, bounded AI context, and duplicate-request responses persist in SQLite. Markdown memory stays compatible with Telegram. Configure backend/.env and run `python -m backend.atlas.app`; see the setup guide for HTTPS access and Termux helpers.

Task automation, multi-user accounts, and permanent tunnel setup remain future work. MAUI CI builds the Android debug APK. Backend tests cover authentication, persistence, concurrency, provider errors, model-tool memory saves, and local HTTP startup using mocked provider responses. Real Groq/tunnel/device integration requires your configured server and credentials.

Secrets stay in environment configuration. Android stores only an Atlas access token with Keystore encryption; Groq keys remain on the backend. Do not commit runtime data, credentials, or signing keys.

The GitHub repository remains `LMS147/atlas-agent`; **Atlas-AI** is the project title and checkout folder name. Renaming the GitHub repository is a separate settings change.

## Improvement roadmap

The core Atlas features are implemented. The next phase prioritises reliability and release readiness before expanding the app. The table describes the target scope; the progress section below distinguishes delivered work from remaining tasks.

| Priority | Improvement | Planned work |
|---|---|---|
| 1 | Permanent APK signing key | Configure a durable signing key through CI secrets so distributed builds can receive compatible updates. Keep signing keys out of source control. |
| 2 | Server backups and recovery | Back up SQLite data, conversations, memories and uploaded files; document retention and test restoration. |
| 3 | Real-device testing | Test against the configured backend: chat, file operations, secure credential storage, keyboard and Android Back, interrupted connections, background/resume and reopening the app. |
| 4 | Chat experience | Add streamed responses, clearer processing states, formatted replies and conversation search while preserving duplicate-request protection and safe recovery. |
| 5 | Accessibility and polish | Validate larger text, TalkBack labels, contrast, touch targets and layouts on small screens. |
| 6 | Complete the MAUI migration | Clarify which client to use and provide an export/import path for recoverable history stored only in the Kotlin app. |
| 7 | Automation tools | Extend the current Tools shortcuts into useful actions with previews and confirmation for changes to files or server data. |
| 8 | Orb presence | Refine the procedural blue particle orb and validate playback-driven animation on devices. |

Recommended order: permanent APK signing, backups and recovery, then real-device testing. Automated builds and smoke tests do not replace testing with the actual server and device.

### Roadmap implementation progress (0.8.0)

| Area | Delivered | Still required |
|---|---|---|
| Signing | Manual Release APK workflow, signature verification and permanent-key setup guide | Owner configures signing secrets; exercise release build and compatible-update test |
| Backups | Offline full local workspace backup/verify/restore CLI, SQLite integrity checks, archive checksums and regression tests | Schedule protected copies, back up external GitHub memory separately, and run a production restore drill |
| Device testing | Physical-device acceptance checklist | Execute on the owner's phone and real backend; record evidence |
| Chat | Live Groq reply streaming, saved-request recovery, title/recent-preview search, encoded code blocks and processing status | Real-provider/tunnel/device acceptance and richer formatting |
| Accessibility | Visible focus, inherited control fonts, 44px minimum button height, wrapping toolbars and reduced-motion styles | TalkBack and large-text acceptance on physical devices |
| Migration | Primary/legacy client guidance and data-preservation checklist | Supported Kotlin export/MAUI import flow |
| Tools | Memory cleanup preview, revision-checked execution and native confirmation | Additional automation actions and task scheduling |
| Companion | Procedural blue particle orb, depth-aware orbital nodes, lightweight fallback and playback state | Real-device performance and installed voice-engine acceptance |

- [Permanent signing setup](docs/android-release.md)
- [Workspace backup and recovery](https://github.com/LMS147/Server-management/blob/main/deployment/backup/README.md)
- [Real-device acceptance checklist](docs/device-acceptance.md)
- [MAUI migration status](docs/migration-status.md)

## License

No open-source license has been selected. See LICENSE. The source is not granted an MIT, Apache, or other open-source license by this restructuring.

### File controls and memory maintenance

The Android Files screen uploads/downloads documents through the system picker and opens UTF-8 workspace files for conflict-safe editing. The Memory screen edits/deletes saved facts and previews conservative, backed-up compaction. Host status and service controls are provided by the separate Server-management application. See [API contracts](docs/api.md) and [setup](docs/setup.md) for limits and operation.


## Live chat streaming (0.9.0)

The MAUI app displays live reply text from an updated API while keeping completed replies and duplicate-request protection in SQLite. Interrupted streams use the existing saved-reply status check. Older servers retain ordinary chat through capability negotiation. See [streaming protocol, limits and upgrade steps](docs/chat-streaming.md). Upgrade the backend and reconnect the app to enable streaming; this source update does not deploy the live server automatically.

## Separate applications

Atlas is the AI companion app. Host Dashboard, Services, Connections, Logs and Settings are provided by the independent [Server-management app](https://github.com/LMS147/Server-management). Server monitoring has moved there, including removal of the Atlas `/monitoring` endpoint.
