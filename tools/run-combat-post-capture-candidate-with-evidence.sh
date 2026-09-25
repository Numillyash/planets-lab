#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  combat-post-capture-candidate \
  --include artifacts/combat-post-capture-candidate-v3 \
  -- \
  bash tools/run-combat-post-capture-candidate-discovery.sh
