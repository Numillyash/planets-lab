#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-horwasp-fighter-feedback-gate-v1 \
  --include artifacts/combat/horwasp-fighter-feedback-gate-v1/published \
  -- \
  bash tools/run-combat-horwasp-fighter-feedback-gate-v1.sh
