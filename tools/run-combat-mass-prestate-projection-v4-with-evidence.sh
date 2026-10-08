#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 combat-mass-prestate-projection-v4 \
 --include artifacts/combat/mass-prestate-projection-v4 \
 -- \
 bash tools/run-combat-mass-prestate-projection-v4.sh
