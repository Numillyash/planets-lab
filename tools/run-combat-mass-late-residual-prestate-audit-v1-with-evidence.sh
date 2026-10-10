#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-late-residual-prestate-audit-v1 \
  --include artifacts/combat/mass-late-residual-prestate-audit-v1/published \
  -- \
  bash tools/run-combat-mass-late-residual-prestate-audit-v1.sh
