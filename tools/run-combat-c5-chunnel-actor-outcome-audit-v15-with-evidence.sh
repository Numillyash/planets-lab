#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 combat-c5-chunnel-actor-outcome-audit-v15 \
 --include artifacts/combat/c5-chunnel-actor-outcome-audit-v15/published \
 -- bash tools/run-combat-c5-chunnel-actor-outcome-audit-v15.sh
