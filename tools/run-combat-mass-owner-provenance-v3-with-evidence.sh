#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 combat-mass-owner-provenance-v3 \
 --include artifacts/combat/mass-owner-provenance-v3 \
 -- \
 bash tools/run-combat-mass-owner-provenance-v3.sh
