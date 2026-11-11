#!/usr/bin/env bash
# Shared by the API lifecycle helpers; tokens are read only by Python configuration.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ATLAS_PYTHON="${ATLAS_PYTHON:-python}"
API_PID_FILE="$ROOT/.run/api.pid"
process_matches() {
  [[ -f "$API_PID_FILE" ]] || return 1
  local api_pid
  api_pid="$(cat "$API_PID_FILE")"
  [[ "$api_pid" =~ ^[0-9]+$ ]] && kill -0 "$api_pid" 2>/dev/null || return 1
  [[ -r "/proc/$api_pid/cmdline" ]] || return 1
  tr '\0' '\n' <"/proc/$api_pid/cmdline" | grep -Fxq -- 'backend.atlas.app'
}
