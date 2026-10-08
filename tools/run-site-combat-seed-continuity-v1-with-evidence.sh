#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  site-combat-seed-continuity-v1 \
  --include artifacts/combat/site-seed-continuity \
  -- \
  bash tools/run-site-combat-seed-continuity-v1.sh
