# Backend layout

| Directory | Responsibility |
|---|---|
| `atlas/app/` | FastAPI routes, Groq agent, conversations, memory, files and monitoring |
| `atlas/telegram/` | Atlas Telegram transport |
| `atlas/seed/` | Initial identity and memory documents |
| `atlas/tests/` | Atlas application regression tests |
| `server/termux/` | Host SSH, Cloudflare retry and boot scripts from the phone-server guide |
| `server/termux_service.py` | Install and control the supervised Atlas API process |
| `server/healthcheck.py` | Authenticated local API health probe |
| `server/tests/` | Service installation, lifecycle and restart tests |

From the repository root:

```sh
python -m backend.atlas.app
python -m backend.atlas.telegram.bot
python -m backend.server.healthcheck
python -m backend.server.termux_service status
```

Shared configuration stays in `backend/.env` and dependencies are installed from
`backend/requirements.txt`. Existing `DATA_DIR`, SQLite data, workspace files and
credentials retain their locations.

Run the component tests separately:

```sh
python -m unittest discover -s backend/atlas/tests -v
python -m unittest discover -s backend/server/tests -v
```

## Update an existing phone installation

The old Python module entry points have been removed. Before pulling this change,
stop the existing API using the currently installed checkout:

```sh
cd ~/server/apps/atlas-agent
source .venv/bin/activate
export ATLAS_PYTHON="$PWD/.venv/bin/python"
bash deployment/termux/service.sh stop
```

After this PR is merged, update and re-register the service so its run script uses
`backend.atlas.app`:

```sh
git pull --ff-only
python -m pip install -r backend/requirements.txt
bash deployment/termux/install-service.sh --enable --boot
bash deployment/termux/service.sh health
```

If the checkout was already updated, stop the old supervised API directly before
re-registering:

```sh
sv -w 30 down "$PREFIX/var/service/atlas-api"
```

Wait for shutdown to finish before running the installer. Update any personal
scripts that launch the previous Python module paths. A manually launched
Telegram process should be stopped before updating, then started with
`python -m backend.atlas.telegram.bot` or the updated Telegram helper.

Tailscale recovery and APK recovery buttons remain follow-up work under
`server/` and `mobile/`.

See [phone host scripts and installation](server/README.md) for the independent SSH/Cloudflare setup.
