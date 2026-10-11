#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-horwasp-postcombat-clan-projection-v1 \
  --include artifacts/combat/horwasp-postcombat-clan-projection-v1/published \
  -- \
  bash tools/run-combat-horwasp-postcombat-clan-projection-v1.sh
