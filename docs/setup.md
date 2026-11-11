# Atlas setup

Run application commands from the Atlas repository root.

## Configure the AI backend

```sh
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -r backend/requirements.txt
```

Copy `backend/.env.example` to `backend/.env` only for a new installation. Keep an
existing configuration and DATA_DIR when updating. Configure GROQ_API_KEY,
ATLAS_API_TOKEN (a separate random token of at least 32 characters), DATA_DIR,
ATLAS_HOST and ATLAS_PORT. Exported environment variables override the file.

Generate an Atlas access token locally:

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep it private. Run the application and check it in another terminal:

```sh
python -m backend.atlas.app
python -m backend.atlas.healthcheck
```

The API defaults to `127.0.0.1:8000` and uses one worker. `/docs` exposes the API
contract. An authenticated health result confirms startup; a chat also tests the
configured Groq provider. Credentials remain in configuration rather than Git.

## Connect the Atlas mobile app

Build the MAUI app from `mobile/Atlas.sln`, or install its signed release APK. See
[mobile build instructions](../mobile/README.md) and [release signing](android-release.md).
Enter the server's HTTPS base URL and its ATLAS_API_TOKEN on the setup screen.
The Groq provider key stays on the backend.

Configure HTTPS forwarding, phone supervision, SSH and Tailscale through the
separate [Server-management repository](https://github.com/LMS147/Server-management).
Its [migration guide](https://github.com/LMS147/Server-management/blob/main/docs/migration.md)
explains how to move existing management commands while keeping this Atlas checkout
and DATA_DIR in place. The API can remain on loopback HTTP behind the HTTPS tunnel.

Verify chat, memory, file operations, history restoration, and interrupted-reply
recovery with your actual device and provider. Never repeat an uncertain AI request
without checking for its saved result first.

## Existing Telegram transport

```sh
python -m backend.atlas.telegram.bot
```

Configure TELEGRAM_TOKEN and ALLOWED_USER_IDS in addition to GROQ_API_KEY. Telegram
and the API can share Markdown memory. Their conversation sessions remain separate.
Host lifecycle helpers are maintained in Server-management.

## Cloud application deployment

The application-specific Render API configuration and Docker/Fly/Render Telegram
configurations remain here. The [Render API guide](../deployment/render/README.md)
uses `render.api.yaml`; the older Telegram blueprints start the bot. Configure
persistent storage for durable history, memory and uploads.

## Tests

```sh
python -m unittest discover -s backend/atlas/tests -v
python -m compileall -q backend
bash -n deployment/render/*.sh
```

Application tests use temporary data and mocked AI responses. Phone service,
backup, host-script and cross-repository lifecycle tests live in Server-management.
Run the [physical-device acceptance checklist](device-acceptance.md) for release
validation.
