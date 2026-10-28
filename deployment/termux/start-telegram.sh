#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p .run
if ! mkdir .run/telegram.lock 2>/dev/null; then
  echo "Another lifecycle operation is running; inspect .run/telegram.lock if stale." >&2; exit 1
fi
trap 'rmdir "$ROOT/.run/telegram.lock"' EXIT
if bash deployment/termux/healthcheck-telegram.sh >/dev/null 2>&1; then echo "Atlas Telegram is already running."; exit 0; fi
if [[ ! -f backend/.env ]]; then echo "Create backend/.env from backend/.env.example first." >&2; exit 1; fi
PYTHON_BIN="${ATLAS_PYTHON:-python}"
nohup "$PYTHON_BIN" -m backend.telegram.bot >>.run/telegram.log 2>&1 &
echo "$!" > .run/telegram.pid
sleep 1
bash deployment/termux/healthcheck-telegram.sh
