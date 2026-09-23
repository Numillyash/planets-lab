#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  combat-capture-reintegration \
  --include artifacts/combat-feature-scope-v1 \
  --include artifacts/combat-predictive-queue-v1 \
  --include artifacts/combat-capture-reintegration-v1 \
  -- \
  bash tools/run-combat-capture-reintegration-gate.sh
