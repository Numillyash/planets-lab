#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-residual-triage-v1 \
  --include artifacts/combat/mass-residual-triage-v1 \
  -- \
  bash tools/run-combat-mass-residual-triage-v1.sh
