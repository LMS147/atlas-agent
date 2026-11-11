#!/usr/bin/env bash
set -euo pipefail
# Render chooses PORT. Keep the one-worker, configuration-aware API launcher.
export ATLAS_HOST=0.0.0.0
export ATLAS_PORT="${PORT:-10000}"
exec python -m backend.atlas.app
