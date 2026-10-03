#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOW_NON_MAIN="${PUBLIC_SHORT_EXPANSION_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"

if [[ "$ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: public short expansion must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  exit 64
fi

exec bash tools/run-with-runtime-evidence.sh \
  public-short-expansion \
  --include artifacts/public-short-expansion \
  -- \
  bash tools/run-public-short-expansion-acquisition.sh
