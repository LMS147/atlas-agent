#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT"
if [[ -n "${PREFIX:-}" && -f "$PREFIX/var/service/atlas-api/atlas-managed.json" ]]; then
  exec "$ATLAS_PYTHON" -m backend.termux_service start
fi
mkdir -p .run
mkdir .run/api.lock 2>/dev/null || { echo "Another API lifecycle operation is running; inspect .run/api.lock if stale." >&2; exit 1; }
trap 'rmdir "$ROOT/.run/api.lock"' EXIT
if process_matches; then
  echo "Atlas API process already exists."
  "$ATLAS_PYTHON" -m backend.healthcheck
  exit $?
fi
# Validate before spawning, without printing credentials.
"$ATLAS_PYTHON" -c 'from backend.app.config import load_settings; load_settings()'
nohup "$ATLAS_PYTHON" -m backend.app >>.run/api.log 2>&1 &
echo "$!" > "$API_PID_FILE"
for attempt in {1..30}; do
  if ! kill -0 "$(cat "$API_PID_FILE")" 2>/dev/null; then
    echo "API exited during startup; inspect .run/api.log." >&2
    rm -f "$API_PID_FILE"
    exit 1
  fi
  if process_matches && "$ATLAS_PYTHON" -m backend.healthcheck >/dev/null 2>&1; then
    echo "Atlas API is running and authenticated health check passed."
    exit 0
  fi
  sleep 0.5
done
echo "API is still starting or unhealthy; inspect .run/api.log. PID retained for stop.sh." >&2
exit 1
