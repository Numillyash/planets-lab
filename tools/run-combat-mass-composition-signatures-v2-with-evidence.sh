#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-composition-signatures-v2 \
  --include artifacts/combat/mass-composition-signatures-v2 \
  -- \
  bash tools/run-combat-mass-composition-signatures-v2.sh
