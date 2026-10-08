#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  multigame-conditional-combat-coverage-v2 \
  --include artifacts/combat/multigame-conditional-coverage-v2 \
  -- \
  bash tools/run-multigame-conditional-combat-coverage-v2.sh
