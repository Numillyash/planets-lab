#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PUBLIC_VALIDATION_ALLOW_NON_MAIN="${PUBLIC_VALIDATION_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"

if [[ "$PUBLIC_VALIDATION_ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: public validation corpus acquisition must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  echo "Switch to main and fast-forward from origin/main before retrying." >&2
  echo "For an intentional non-main diagnostic only, set PUBLIC_VALIDATION_ALLOW_NON_MAIN=1." >&2
  exit 64
fi

exec bash tools/run-with-runtime-evidence.sh \
  public-validation-corpus \
  --include artifacts/public-validation-corpus \
  -- \
  bash tools/run-public-validation-corpus-acquisition.sh
