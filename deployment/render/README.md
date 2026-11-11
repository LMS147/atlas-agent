# Test the Atlas Android API on Render

This is a **separate API Web Service** for the Android app. The existing `render.yaml`, `render.worker.yaml` and Telegram Dockerfile still run the Telegram transport. Choose `render.api.yaml` for this test.

## Deploy the free test

1. In the Render dashboard select **New → Blueprint** and connect `LMS147/atlas-agent`. Authorize Render's GitHub integration to access this private repository if requested.
2. Select branch `main`, then set **Blueprint Path** to `render.api.yaml` (not the default `render.yaml`). Review the service name `atlas-api-test` and **Free** instance type.
3. Enter `GROQ_API_KEY` in Render's secret/environment field. The Blueprint generates a separate `ATLAS_API_TOKEN`. Retrieve it from the service's Environment page after creation. Do not use the Groq key in Android.
4. Deploy and wait for **Live**. The start command binds to Render's assigned `PORT` on `0.0.0.0`; `/healthz` returns an empty 204 after initialization. `/api/v1/*` remains bearer-authenticated.
5. Copy the service's actual HTTPS URL from Render. It will look like `https://<assigned-name>.onrender.com`; use the assigned URL rather than guessing the name.
6. Open that URL followed by `/docs` to wake a sleeping free service. Once loaded, choose **Authorize**, enter `ATLAS_API_TOKEN`, and try `GET /api/v1/health`.
7. In Android → **Server setup**, enter the HTTPS base URL (without `/docs` or `/api/v1`) and that same Atlas token, then connect. The current v0.5 APK works without rebuilding.

No Telegram token, GitHub memory token, Cloudflare tunnel or Termux process is required for this API test. Do not set `GH_REPO` or `GH_TOKEN` for this temporary local-storage configuration. If you create a Web Service manually, leave **Root Directory** empty, choose Python, and use these settings instead:

| Setting | Value |
| --- | --- |
| Branch | `main` |
| Instance type | Free |
| Build command | `pip install -r backend/requirements.txt` |
| Start command | `bash deployment/render/start.sh` |
| Health check path | `/healthz` |
| `DATA_DIR` | `/tmp/atlas-data` |
| `GROQ_API_KEY` | Your provider key, stored only on Render |
| `ATLAS_API_TOKEN` | A separately generated token of at least 32 printable characters without spaces |
| `MODEL` | `llama-3.3-70b-versatile` (or a supported model available to your Groq account) |

The root `.python-version` selects the latest Python 3.12 patch, matching the backend CI series. Leave `PYTHON_VERSION` unset unless you provide a fully qualified supported version; an inherited `PYTHON_VERSION=3.12` overrides the file and is invalid on Render. Generate a manual Atlas token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, and put it directly into Render's environment field.

Automatic deploys are disabled in this test Blueprint to avoid resetting test data on every commit. Deploy new commits manually in Render when you want to test them. Blueprint sync/configuration changes can also redeploy/reset the service.

## What to test

- Connect and receive a real Groq chat reply; create, rename and switch conversations.
- Add/edit/delete a memory; preview and apply conservative compaction.
- Upload a small UTF-8 file, open/edit it, then download and inspect it. Test a binary download separately.
- Open Server status. These metrics describe the Render runtime, not the phone. Device-wide `/proc` values, when readable, may reflect the shared host rather than your container's allocation; some values may be unavailable.
- Temporarily disconnect Android's network, then reconnect and use **Check for reply** for an interrupted chat.

## Free-plan limits

Free Render services spin down after 15 minutes without inbound traffic. Waking usually takes about a minute, so the app may show a connection or startup error on the first attempt. Wake `/docs`, wait for it to load, then connect again. Do not repeatedly send new AI requests while a previous request is unresolved.

**Everything in `DATA_DIR` is temporary on the free plan**: SQLite conversations, local Markdown memory, uploads and backups can disappear on sleep, restart or redeploy. Android's cached chats are not a replacement for server data. If the server no longer knows a cached chat after a reset, create a new conversation rather than expecting the old one to resume. GitHub-backed memory alone would not preserve SQLite conversations or workspace files.

For durable testing, deliberately upgrade to a paid Web Service and attach a persistent disk mounted at `/var/data`; set `DATA_DIR=/var/data/atlas`. Back up any wanted test data before changing storage, because this changes the data location. Keep one instance and one Uvicorn worker for SQLite and process ownership. Do not claim durability until the disk is attached and the app is using its mount path. Paid service/disk charges are separate; the provided Blueprint only requests a free service.

## Troubleshooting

- **404 at `/`** is normal; use `/docs` for the API explorer or `/healthz` for the minimal public readiness probe.
- **401** from `/api/v1/health`: API is running; supply the Atlas bearer token. Do not use this protected endpoint as Render's unauthenticated health check.
- **Port/startup failure**: verify Root Directory is empty and the start command uses `deployment/render/start.sh`. Do not start `backend.atlas.telegram.bot` for Android.
- **Chat 429/502/504**: check Groq quota, model availability and provider credentials in Render. A healthy API does not prove provider access.
- **Missing data after redeploy**: expected on Free. Use a paid persistent disk or Termux's durable storage for long-lived data.

References: [Render Web Services](https://render.com/docs/web-services), [free limits](https://render.com/docs/free), [Python versions](https://render.com/docs/python-version), [health checks](https://render.com/docs/health-checks), [Blueprint reference](https://render.com/docs/blueprint-spec).
