#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  multigame-conditional-combat-pilot-v1 \
  --include artifacts/combat/multigame-conditional-ensemble \
  -- \
  bash tools/run-multigame-conditional-combat-pilot-v1.sh
