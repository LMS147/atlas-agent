# Setup

## Android

Open `android/` in Android Studio with JDK 17 and Android SDK 35, sync, then run on Android 8.0+ and choose **Explore demo**. The app can be explored without a server. From the repo root:

```sh
cd android
./gradlew testDebugUnitTest assembleDebug
```

Windows: `cd android` then `.\gradlew.bat testDebugUnitTest assembleDebug`.
CI runs the build and publishes an `atlas-debug-apk` artifact when successful. The Android debug build and unit tests passed in [GitHub Actions](https://github.com/LMS147/atlas-agent/actions/runs/40656515106). Download the `atlas-debug-apk` artifact from that run. Device rendering and live API integration remain unverified.

## Existing Telegram agent

Run all Python commands from the repository root:

```sh
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env locally: Telegram token, Groq key, allowed Telegram IDs.
python -m backend.telegram.bot
```

Windows: copy `backend\.env.example` to `backend\.env` using File Explorer or PowerShell. Never commit `.env` or keys. The Telegram module loads `backend/.env` explicitly; existing exported environment variables take precedence. The default local data path remains `./data` in the root, preserving data from an earlier root-level deployment. If you used another working directory, set `DATA_DIR` to its existing absolute path before starting.

The old `python bot.py` command is replaced by `python -m backend.telegram.bot`. Existing Render blueprints and Fly process commands are updated. Fly's Dockerfile is at `deployment/Dockerfile`. The legacy Telegram deployment guide is retained as `docs/telegram-legacy.md` for configuration context; its old source layout is historical.

## FastAPI scaffold

```sh
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

This starts an empty FastAPI app with no data routes, docs endpoint, or health endpoint. It is not yet compatible with Android live mode. Implement docs/api.md plus authentication before enabling remote access. Do not enter a Groq key in Android's Atlas access-token field.

## Termux

Install Python and Git with Termux's package manager, clone this repo, install `backend/requirements.txt`, and configure `backend/.env`. Then run from the root:

```sh
bash deployment/termux/start.sh
bash deployment/termux/healthcheck.sh
bash deployment/termux/stop.sh
```

Logs and PID state live in ignored `.run/`. The scripts are manual Telegram-process helpers; they do not configure Android battery exemptions, boot startup, a tunnel, or a FastAPI service. A stale lock after abrupt interruption needs manual inspection before removal.

## Checks

```sh
python -m unittest discover -s backend/tests -v
python -m compileall -q backend
bash -n deployment/termux/start.sh deployment/termux/stop.sh deployment/termux/healthcheck.sh
```
