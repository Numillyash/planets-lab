#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  public-capture-side-discovery \
  --include artifacts/public-capture-side \
  -- \
  bash tools/run-public-capture-side-discovery.sh
