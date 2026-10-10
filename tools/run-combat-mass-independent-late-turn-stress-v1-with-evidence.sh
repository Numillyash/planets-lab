#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-independent-late-turn-stress-v1 \
  --include artifacts/combat/mass-independent-late-turn-stress-v1/published \
  -- \
  bash tools/run-combat-mass-independent-late-turn-stress-v1.sh
