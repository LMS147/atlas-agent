#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT"
process_matches || { echo "No verified Atlas API process is running." >&2; exit 1; }
exec "$ATLAS_PYTHON" -m backend.healthcheck
