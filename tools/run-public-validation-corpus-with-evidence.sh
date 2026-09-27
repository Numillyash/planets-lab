#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh \
  public-validation-corpus \
  --include artifacts/public-validation-corpus \
  --include validation/corpus/manifests/public-validation-selected.jsonl \
  --include validation/corpus/manifests/public-validation-combined.jsonl \
  --include validation/corpus/index/public-validation-games.jsonl \
  --include validation/corpus/index/public-validation-stats.json \
  -- \
  bash tools/run-public-validation-corpus-acquisition.sh
