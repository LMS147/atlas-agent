# Backend layout

Application code and phone service management have separate packages.

| Directory | Responsibility |
|---|---|
| `atlas/app/` | FastAPI routes, Groq agent, conversations, memory, files and monitoring |
| `atlas/telegram/` | Atlas Telegram transport |
| `atlas/seed/` | Initial identity and memory documents |
| `atlas/tests/` | Atlas application regression tests |
| `server/termux_service.py` | Install and control the supervised Atlas API process |
| `server/healthcheck.py` | Authenticated local API health probe |
| `server/tests/` | Service installation, lifecycle and restart tests |

From the repository root, the canonical commands are:

```sh
python -m backend.atlas.app
python -m backend.atlas.telegram.bot
python -m backend.server.healthcheck
python -m backend.server.termux_service status
```

Existing commands (`backend.app`, `backend.telegram.bot`, `backend.healthcheck`
and `backend.termux_service`) remain supported by small compatibility adapters.
Legacy module imports resolve to the same implementation modules, preserving
shared memory locks and module state. Existing installed supervisors keep their
`python -m backend.app` process command so shell lifecycle checks keep working.

Configuration stays in `backend/.env`. `backend/requirements.txt` remains the
installation entry point. `DATA_DIR`, existing SQLite data, workspace files and
credentials keep their existing locations. This refactor does not migrate or
reset runtime data.

Run all backend tests with the existing discovery command:

```sh
python -m unittest discover -s backend/tests -v
```

The files in `backend/tests` are discovery adapters for the tests in the two
component directories. Each component suite can also run separately:

```sh
python -m unittest discover -s backend/atlas/tests -v
python -m unittest discover -s backend/server/tests -v
```

This change separates existing functionality. Tailscale recovery commands and
the APK recovery buttons are follow-up work under `server/` and `mobile/`.
