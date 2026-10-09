#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# V1 must genuinely succeed with published runtime evidence before V2 proceeds.
bash tools/run-combat-mass-temporal-reconciliation-v1-with-evidence.sh
bash tools/run-combat-mass-time-indexed-static-v1-with-evidence.sh
