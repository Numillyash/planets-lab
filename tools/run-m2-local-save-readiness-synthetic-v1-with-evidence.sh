#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# IMPORTANT: ONLY --synthetic runs under public runtime-evidence.
# Real/private client reports must NEVER use this wrapper or GitHub.
exec bash tools/run-with-runtime-evidence.sh \
  m2-local-save-readiness-synthetic-v1 \
  -- python3 tools/diagnostics/m2_local_save_readiness_v1.py --synthetic
