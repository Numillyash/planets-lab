#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 combat-c5-phase-aware-firecloud-v12 \
 --include artifacts/combat/c5-phase-aware-firecloud-v12/published \
 -- bash tools/run-combat-c5-phase-aware-firecloud-v12.sh
