#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT"
if [[ -n "${PREFIX:-}" && -f "$PREFIX/var/service/atlas-api/atlas-managed.json" ]]; then
  exec "$ATLAS_PYTHON" -m backend.termux_service health
fi
process_matches || { echo "No verified Atlas API process is running." >&2; exit 1; }
exec "$ATLAS_PYTHON" -m backend.healthcheck
