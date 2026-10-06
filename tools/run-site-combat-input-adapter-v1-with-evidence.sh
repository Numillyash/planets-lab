#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  site-combat-input-adapter-v1 \
  --include artifacts/combat/site-input-adapter \
  -- \
  bash tools/run-site-combat-input-adapter-v1.sh
