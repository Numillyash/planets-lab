#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 combat-c5-short-edge-mechanisms-batch-v24 \
 --include artifacts/combat/c5-short-edge-mechanisms-batch-v24/published \
 -- bash tools/run-combat-c5-short-edge-mechanisms-batch-v24.sh
