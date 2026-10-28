#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT"
mkdir -p .run
mkdir .run/api.lock 2>/dev/null || { echo "Another API lifecycle operation is running." >&2; exit 1; }
trap 'rmdir "$ROOT/.run/api.lock"' EXIT
if process_matches; then
  kill "$(cat "$API_PID_FILE")"
  for attempt in {1..20}; do
    if ! process_matches; then break; fi
    sleep 0.5
  done
  if process_matches; then
    echo "API is still shutting down; PID retained. Try again after in-flight requests finish." >&2
    exit 1
  fi
fi
rm -f "$API_PID_FILE"
echo "Atlas API is stopped."
