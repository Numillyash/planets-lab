#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  site-combat-payload-provenance-v1 \
  --include artifacts/combat/site-payload-provenance \
  -- \
  bash tools/run-site-combat-payload-provenance-v1.sh
