#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-rulebook-reconciliation-v2 \
  --include artifacts/combat/mass-rulebook-reconciliation-v2/published \
  -- \
  bash tools/run-combat-mass-rulebook-reconciliation-v2.sh
