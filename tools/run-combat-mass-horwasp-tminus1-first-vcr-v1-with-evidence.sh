#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-mass-horwasp-tminus1-first-vcr-v1 \
  --include artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published \
  -- \
  bash tools/run-combat-mass-horwasp-tminus1-first-vcr-v1.sh
