# Setup

Run commands from the repository root unless stated otherwise.

## Configure and start the API

```sh
python -m venv .venv
# Activate .venv using the command for your shell, then:
python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

On Windows use `Copy-Item backend/.env.example backend/.env` instead of `cp` if needed. Edit `backend/.env` locally and set:

- `GROQ_API_KEY`: your existing Groq provider key.
- `ATLAS_API_TOKEN`: a separate randomly generated access token, minimum 32 characters.
- `DATA_DIR`: durable storage directory; defaults to `./data` in the repository root.
- `ATLAS_HOST=127.0.0.1` and `ATLAS_PORT=8000` for the local server behind a tunnel.

Generate the Atlas token on your own machine:

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save it only in your local backend/.env and Android's Atlas access-token field. Never commit it or use your Groq key as the Atlas token. Exported environment variables take precedence over backend/.env. Telegram credentials are not required to start the API.

```sh
python -m backend.app
```

The launcher loads configuration and starts one Uvicorn worker. Startup initializes seed memory files and SQLite history. Swagger documentation is at http://127.0.0.1:8000/docs; click **Authorize** and enter your Atlas token. Check local authenticated health with:

```sh
python -m backend.healthcheck
```

An `ok` health result confirms API startup, not a paid Groq inference or provider quota. Chat returns explicit provider failure codes when necessary.

## Connect Android

Open `android/` in Android Studio with JDK 17 and SDK 35. Build/run on Android 8.0+, or use an existing CI debug APK. The current Android binary already matches the API contract; it does not require a networking rewrite.

Use the HTTPS URL of your tunnel as **Server URL** and the same `ATLAS_API_TOKEN` as **Atlas access token**. Android rejects plain HTTP. The server can remain on loopback HTTP behind the HTTPS tunnel. See [Cloudflare instructions](../deployment/cloudflare/README.md). Demo mode remains available without a server.

Verify the complete flow: connect, send a message, create a memory, reopen the app, then restart the API and send another message in the same conversation. SQLite preserves server context; Room preserves the app's local history and delivery state. If a reply is interrupted, use **Check for reply** to recover it with the same request ID. **Send again…** creates a fresh request only after confirmation. The app never replaces a failed live request with a demo response.

Build manually:

```sh
cd android
./gradlew testDebugUnitTest assembleDebug
```

Windows: `.\gradlew.bat testDebugUnitTest assembleDebug`. GitHub Actions publishes the `atlas-debug-apk` artifact after successful builds. Device rendering, on-device Keystore behavior, a real Groq account, and an external tunnel have not been tested by automated API tests.

## Termux API lifecycle

After installing Python/Git in Termux, clone the repository, install backend/requirements.txt, and configure backend/.env. From the root:

```sh
bash deployment/termux/start.sh
bash deployment/termux/healthcheck.sh
bash deployment/termux/stop.sh
```

These now manage the **API**. They verify process identity and make an authenticated HTTP health request. `ATLAS_PYTHON` can point to a virtual environment's Python executable. Logs/PID state are in ignored `.run/api.log` and `.run/api.pid`. A stale lock after abrupt interruption needs manual inspection. Startup/boot integration, wake locks, Android battery exemptions, and tunnel lifecycle automation are not configured by these helpers.

Run one API worker/process per DATA_DIR. Use the launcher above rather than adding `--workers` or `--reload`. Keep the directory on persistent storage; SQLite history is local even when Markdown memory is GitHub-backed.

## Existing Telegram bot

The bot remains independent:

```sh
python -m backend.telegram.bot
```

It still needs TELEGRAM_TOKEN and ALLOWED_USER_IDS in backend/.env, plus GROQ_API_KEY. The former lifecycle helpers are retained as `start-telegram.sh`, `healthcheck-telegram.sh`, and `stop-telegram.sh` under deployment/termux. They use their original `.run/telegram.*` files. Local Markdown memory can be shared with the API; Telegram conversation sessions retain their existing in-memory behavior.

Existing Render/Fly blueprints and deployment/Dockerfile continue to start **Telegram**, preserving that deployment. They do not automatically publish the API. A separately configured API deployment must use the API launcher, its own HTTP port/bind configuration, persistent storage, and the Atlas token.

## Tests

```sh
python -m unittest discover -s backend/tests -v
python -m compileall -q backend
bash -n deployment/termux/*.sh
```

Tests use temporary storage and mocked Groq responses. They cover the Android API contract, bearer auth, model-tool memory writes, provider error mapping, request replay/conflicts, concurrency, restart persistence, and a live local Uvicorn startup. Linux lifecycle tests also exercise the shell helpers when /proc and process PID namespaces match. No real provider calls or credentials are used.
