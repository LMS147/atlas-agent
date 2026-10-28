#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p .run
mkdir .run/telegram.lock 2>/dev/null || { echo "Another lifecycle operation is running." >&2; exit 1; }
trap 'rmdir "$ROOT/.run/telegram.lock"' EXIT
if bash deployment/termux/healthcheck.sh >/dev/null 2>&1; then
  PID="$(cat .run/telegram.pid)"
  kill "$PID"
  echo "Requested graceful shutdown of Atlas Telegram."
else
  echo "No verified Atlas Telegram process is running."
fi
rm -f .run/telegram.pid
