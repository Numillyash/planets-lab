#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-c5-current-n-roster-bridge-v2 \
  --include artifacts/combat/c5-current-n-roster-bridge-v2/published \
  -- \
  bash tools/run-combat-c5-current-n-roster-bridge-v2.sh
