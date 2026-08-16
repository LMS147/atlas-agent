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

## Deploy to Render (paid worker, $7/mo — the simple path)

`render.yaml` is committed, so: Dashboard → **New** → **Blueprint** → pick the
repo → fill in the three secrets → apply. The disk mounts at `/data`;
`DATA_DIR=/data` is set in the blueprint.

Verify with `/memory`, trigger a manual redeploy, check `/memory` again.
If content survives, the disk is mounted correctly. Expect ~30s of silence
during deploys (disk services are stop-then-start, pinned to one instance —
fine, a second instance would double-reply anyway).

Shell tab: `cat /data/memory.md`, `ls /data/backups/`, or `vi /data/agent.md`
to tune personality live — the system prompt is rebuilt every message.

## Deploy free (webhook + GitHub-backed memory)

Free Render services get no disk and sleep after 15 min idle. Workarounds,
both already wired in:

1. **Storage → GitHub.** Create a private repo, a fine-grained PAT with
   Contents read+write, then set `GH_REPO` and `GH_TOKEN`. `memory.py`
   switches backends automatically; git commits replace local backups.
2. **Transport → webhook.** Deploy as a **Web Service** (free plan). Render
   injects `RENDER_EXTERNAL_URL` and `PORT`; `bot.py` detects them and runs
   webhook mode. Set `WEBHOOK_SECRET` to any long random string. Leave the
   health check path blank.

Cold starts mean the first message after idle takes 30–60s (Telegram
retries, so it arrives). A cron pinger every 10 min keeps it warm within the
750 free instance-hours. Honestly: worth it as an exercise, not worth it if
you just want the thing working — pay the $7.

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
