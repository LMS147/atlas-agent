# Atlas backend

This backend contains the Atlas AI application under `atlas/`.

| Directory | Responsibility |
|---|---|
| `atlas/app/` | FastAPI routes, Groq agent, conversations, memory, files and in-app monitoring |
| `atlas/telegram/` | Atlas Telegram transport |
| `atlas/seed/` | Initial agent identity and memory |
| `atlas/tests/` | Application, API and startup regression tests |

From the repository root:

```sh
python -m pip install -r backend/requirements.txt
python -m backend.atlas.app
python -m backend.atlas.healthcheck
python -m backend.atlas.telegram.bot
python -m unittest discover -s backend/atlas/tests -v
```

Configure `backend/.env` and retain the existing DATA_DIR when updating. The Atlas
health probe is application-specific and uses the same configuration as the API.

Phone startup, SSH, Cloudflare, service control, workspace backup tools and their
tests live in [Server-management](https://github.com/LMS147/Server-management).
Install/configure that repository before pulling an update that removes the old
management paths. Follow its [migration guide](https://github.com/LMS147/Server-management/blob/main/docs/migration.md).
Existing installed supervisor scripts continue launching this checkout's
`backend.atlas.app` with its existing Python interpreter. Personal commands that
reference this checkout's removed management scripts need the new repository path.
