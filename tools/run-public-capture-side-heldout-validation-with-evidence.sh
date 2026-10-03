#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOW_NON_MAIN="${PUBLIC_CAPTURE_SIDE_HELDOUT_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
FROZEN_CANDIDATE_COMMIT="cd87f9505472e5e396db28a7d6f7c67c561f9c64"

if [[ "$ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: heldout validation must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  exit 64
fi

if ! git merge-base --is-ancestor "$FROZEN_CANDIDATE_COMMIT" HEAD; then
  echo "ERROR: HEAD does not contain the frozen pre-heldout candidate commit." >&2
  echo "required: $FROZEN_CANDIDATE_COMMIT" >&2
  exit 65
fi

exec bash tools/run-with-runtime-evidence.sh \
  public-capture-side-heldout-validation \
  --include artifacts/public-capture-side \
  -- \
  bash tools/run-public-capture-side-heldout-validation.sh
