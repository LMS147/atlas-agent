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

## Test on Render first

Follow the [Render API test guide](../deployment/render/README.md). Select the separate `render.api.yaml` Blueprint for a free HTTPS API test; the older `render.yaml` still starts Telegram. Free Render storage is temporary, including conversations, memory and uploads. Use a paid disk or the phone for durable data.

## Termux API service

For a supervised API with crash restart, rotated logs, and an optional Termux:Boot hook, follow [the Termux service guide](../deployment/termux/README.md). After configuring the backend and stopping the older manual API, install termux-services, restart the shell, and run from the checkout:

```sh
bash deployment/termux/install-service.sh --enable --boot
bash deployment/termux/service.sh status
```

Activate the intended virtual environment first or set ATLAS_PYTHON to its interpreter. Credentials remain in backend/.env. This registers the service on the phone where you run it; it does not remotely configure a phone from GitHub. Existing SSH/tunnel boot scripts are preserved.

The original start/stop/health scripts delegate to the installed service. Without registration they still support manual development. Single-process ownership of DATA_DIR is enforced at API startup. Existing conversation data is retained. Samsung battery restrictions and Termux:Boot activation need manual phone setup and a real reboot check.

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

## Conversation history

Update/restart the backend and install Android v0.3.0 using the same signing key as your previous in-place build. Both database migrations run automatically. Keep the existing DATA_DIR so server history remains available.

Open **History** in Chat or **Conversations** in the navigation menu. Use **New chat**, **Rename**, and the confirmed **Delete** action. Selecting a chat loads its messages from the server and keeps its context separate from other chats. **Load earlier messages** retrieves older pages; changing the AI's context window does not delete saved messages. The last-selected conversation is remembered on this device.

Reinstalling the app or connecting from another device can restore completed history from the same server with a valid Atlas token. Saved credentials can also reopen the existing Room cache during an internet/tunnel outage. A failed health check with no cached workspace still requires a working server; rejected credentials do not silently switch to demo mode.

If a server no longer contains a cached chat and does not report it as deleted (for example, DATA_DIR was replaced), Android retains the local copy as read-only instead of recreating it or deleting the only remaining messages. A confirmed server deletion removes the local copy on the next list synchronization. Demo conversations remain local.

Deleting a conversation removes that chat's server messages and model context, while shared memory facts remain available to Atlas. Clearing the current local cache in Settings does not delete server history; refresh history to download it again. Data is not encrypted by SQLite itself. Live Groq, external tunnel, and physical-device verification still require your configured environment.

## Chat reliability v0.4

Update/restart the backend before installing Android v0.4. **Check for reply** now checks a read-only request-status endpoint and can restore a saved result without posting another AI request. Pending results stay recoverable. A missing record offers **Retry delivery…**, which keeps the original UUID after confirmation. Failed/interrupted attempts require confirmation for a fresh request; check saved memories first because a tool may have run before failure.

The app displays Retry-After guidance for rate limits. Automatic new inference retries remain disabled. New requests require a known conversation on the server, so replacing DATA_DIR cannot silently reset an existing conversation. SQLite/Room histories and existing delivery IDs are preserved; this release adds a delivery-state value without changing the Room schema.

### Files, memory and metrics (v0.5)

Update the checkout and restart the API (`bash deployment/termux/service.sh restart`); install the matching Android APK. No new Python/native dependencies or database migration is required.

In **Files**, choose **Upload**, select a document with Android's file picker, and choose an unused name (ASCII letters/numbers, spaces, dots, dashes or underscores, starting with a letter or number; 120 characters maximum). Files go into `DATA_DIR/workspace`; uploads/downloads are capped at 5 MiB. **Open text** reads UTF-8 files up to 256 KiB and permits editing workspace files. A conflicting edit requires reopening the latest version. **Download** uses Android's save picker, including for binary files; no broad storage permission is needed. Profile, canonical memory and backups stay read-only in Files. Downloads and local copies remain on your device after server-side changes.

In **Memory**, edit facts, confirm deletion, or preview conservative compaction. Compaction only removes duplicate facts and excess blank lines; it will not make unique facts shorter. Local backups are retained (last 30) before changes. Use shorter facts or remove obsolete ones if unique memory still fills its limit.

**Server status** shows real CPU, RAM, filesystem storage, device/API uptime and HTTP/service metrics, with ten-second foreground refreshes. Restricted Android metrics display Unavailable. Validate available metrics on the actual phone; Samsung firmware may restrict `/proc` differently from Linux CI.
