#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  site-combat-mass-candidates-v1 \
  --include artifacts/combat/site-mass-candidates \
  -- \
  bash tools/run-site-combat-mass-candidates-v1.sh
