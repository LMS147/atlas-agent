# Atlas — a Telegram agent with file-based memory

`agent.md` is the identity (human-edited, agent never touches it).
`memory.md` is what it learns (agent-appended via the `save_memory` tool).

```text
my-agent/
├── bot.py            # Telegram layer (polling, or webhook on Render free tier)
├── agent.py          # Groq LLM loop + save_memory tool
├── memory.py         # file read/write, locking, backups, GitHub backend switch
├── storage.py        # GitHub-repo storage (free-tier mode only)
├── seed/
│   ├── agent.md      # shipped in git, copied to the volume on first boot
│   └── memory.md
├── requirements.txt
├── render.yaml       # Render Background Worker + Disk
├── fly.toml          # Fly.io alternative
└── .env.example
```

The `seed/` folder matters: the persistent volume starts empty, so
`ensure_files()` copies these in on first run. After that the live files on
the volume win — edit them via the bot or by SSH/shell.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env       # fill in TELEGRAM_TOKEN + GROQ_API_KEY
python bot.py
```

1. Message `@BotFather` → `/newbot` → grab the token.
2. Message your bot `/whoami`, put that number in `ALLOWED_USER_IDS`, restart.
   Until you do, the guard blocks everyone (except `/whoami` itself).

## Bot commands

| Command | Effect |
|---|---|
| `/memory` | dump memory.md |
| `/agent` | dump agent.md |
| `/remember <fact>` | manually save a fact |
| `/compact` | LLM-rewrite memory.md (dedupe, prune); backs up first |
| `/reset` | clear conversation session — memory untouched |
| `/whoami` | your Telegram user id (unguarded on purpose) |

`/reset` clears the current conversation: cheap, non-destructive.
`memory.md` survives resets, restarts, and redeploys. That's the whole point.

## Deploy to Render — free tier (the committed `render.yaml`)

Free web service + webhook + GitHub-backed memory. See the step-by-step
below. `render.yaml` is the free blueprint; the paid worker variant is kept
in `render.worker.yaml`.

Setup order:
1. Create a **private** GitHub repo for memory (e.g. `agent-memory`). Leave it empty.
2. Create a **fine-grained PAT**: github.com → Settings → Developer settings →
   Fine-grained tokens → only that repo → Repository permissions →
   **Contents: Read and write**. Copy the `github_pat_...` token.
3. Push this project to GitHub.
4. Render → **New** → **Blueprint** → pick this repo → fill in the six
   secrets (`TELEGRAM_TOKEN`, `GROQ_API_KEY`, `ALLOWED_USER_IDS`,
   `GH_REPO`, `GH_TOKEN`, `WEBHOOK_SECRET`) → Apply.
   `WEBHOOK_SECRET` = any long random string using only letters, digits,
   `_` or `-` (Telegram rejects other characters).
5. First boot seeds `agent.md` + `memory.md` into the memory repo as
   commits. Message the bot `/whoami` if you still need your user id.

Verify: send `/remember tests the deploy`, then check the memory repo on
GitHub — you should see a commit `remember: tests the deploy`. Every memory
write is a commit, so version history is free.

Cold starts: the service sleeps after 15 min idle; the first message after
that takes 30–60s (Telegram retries, so it arrives). Keep it warm with
cron-job.org hitting `https://<your-app>.onrender.com/` every 10 minutes —
the 404 response is fine, any request wakes it. That stays within the 750
free instance-hours/month.

Note: conversation sessions live in RAM, so every spin-down clears them
(memory.md is unaffected). On free tier that's just life.

## Deploy to Render — paid worker ($7/mo, `render.worker.yaml`)

Simpler: polling + a real disk, no GitHub repo or webhook needed. Replace
`render.yaml` with `render.worker.yaml`, then: Dashboard → **New** →
**Blueprint** → fill in the three secrets → apply. The disk mounts at
`/data`; `DATA_DIR=/data` is set in the blueprint.

Verify with `/memory`, trigger a manual redeploy, check `/memory` again.
If content survives, the disk is mounted correctly. Expect ~30s of silence
during deploys (disk services are stop-then-start, pinned to one instance —
fine, a second instance would double-reply anyway).

Shell tab: `cat /data/memory.md`, `ls /data/backups/`, or `vi /data/agent.md`
to tune personality live — the system prompt is rebuilt every message.

## How the free-tier mode works under the hood

Two automatic switches, no code edits:

1. **Storage → GitHub** when `GH_REPO` is set: `memory.py` reads/writes the
   memory repo via the Contents API instead of local files. Git commits
   replace the local backup rotation.
2. **Transport → webhook** when `RENDER_EXTERNAL_URL` exists (Render injects
   it, plus `PORT`): `bot.py` runs `run_webhook` instead of polling, so
   Telegram pushes updates to the service — which is what lets Render wake
   it from sleep.

## Fly.io alternative

```bash
fly launch --no-deploy
fly volumes create agent_data --size 1
fly secrets set TELEGRAM_TOKEN=... GROQ_API_KEY=... ALLOWED_USER_IDS=...
fly deploy
```

## Groq gotchas

- **Model IDs churn.** `llama-3.3-70b-versatile` is the current safe default
  for tool calling. Check console.groq.com/docs/models before deploying;
  `MODEL` is an env var so a rename is a dashboard edit, not a commit.
- **TPM is the real limit.** All of memory.md ships every message, so
  `MAX_MEMORY_CHARS` (12k) and `/compact` are load-bearing.
- **No prompt caching** on Groq — another reason to keep memory tight.
- **Weaker tool discipline** than frontier models. The guards in
  `append_memory` (dedupe, length cap, section whitelist) hold regardless of
  what the model decides to do; tighten seed/agent.md if it saves junk.

## Roadmap once it's running

1. Persist `sessions` to disk (`sessions.json` on the volume) so redeploys
   keep conversation context.
2. Cost logging — token usage per turn into a file.
3. A second tool — add an entry to `TOOLS` and a branch in the result loop.
