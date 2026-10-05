#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOW_NON_MAIN="${CORPUS_DB_PUBLIC100_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"

if [[ "$ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: public100 compact runtime must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  exit 64
fi

exec bash tools/run-with-runtime-evidence.sh   corpus-db-public100-compact   --   bash tools/run-corpus-db-public100-compact.sh
