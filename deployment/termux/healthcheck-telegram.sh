#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="$ROOT/.run/telegram.pid"
[[ -f "$PID_FILE" ]] || { echo "Atlas Telegram is stopped."; exit 1; }
PID="$(cat "$PID_FILE")"
[[ "$PID" =~ ^[0-9]+$ ]] && kill -0 "$PID" 2>/dev/null || { echo "Atlas Telegram is stopped."; exit 1; }
[[ -r "/proc/$PID/cmdline" ]] && tr '\0' ' ' <"/proc/$PID/cmdline" | grep -Fq -- 'backend.atlas.telegram.bot' || { echo "PID does not identify the Atlas Telegram process."; exit 1; }
echo "Atlas Telegram process is running (PID $PID); this is not an API or Groq health check."
