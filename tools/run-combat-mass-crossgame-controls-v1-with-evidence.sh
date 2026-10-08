#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-crossgame-controls-v1 \
  --include artifacts/combat/mass-crossgame-controls-v1 \
  -- \
  bash tools/run-combat-mass-crossgame-controls-v1.sh
