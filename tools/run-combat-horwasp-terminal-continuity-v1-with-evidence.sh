#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-horwasp-terminal-continuity-v1 \
  --include artifacts/combat/horwasp-terminal-continuity-v1/published \
  -- \
  bash tools/run-combat-horwasp-terminal-continuity-v1.sh
