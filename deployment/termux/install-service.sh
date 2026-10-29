#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$ROOT"
exec "$ATLAS_PYTHON" -m backend.termux_service install "$@"
