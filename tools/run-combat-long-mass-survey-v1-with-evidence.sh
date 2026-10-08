#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-long-mass-survey-v1 \
  --include artifacts/combat/long-mass-survey-v1/published \
  -- \
  bash tools/run-combat-long-mass-survey-v1.sh
