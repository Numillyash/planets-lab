#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
  combat-c5-public100-site-coverage-v1 \
  --include artifacts/combat/c5-public100-site-coverage-v1/published \
  -- \
  bash tools/run-combat-c5-public100-site-coverage-v1.sh
