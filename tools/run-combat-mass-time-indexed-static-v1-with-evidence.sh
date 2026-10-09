#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-time-indexed-static-v1 \
  --include artifacts/combat/mass-time-indexed-static-v1/published \
  -- \
  bash tools/run-combat-mass-time-indexed-static-v1.sh
