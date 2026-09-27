#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  public-validation-corpus \
  --include artifacts/public-validation-corpus \
  -- \
  bash tools/run-public-validation-corpus-acquisition.sh
