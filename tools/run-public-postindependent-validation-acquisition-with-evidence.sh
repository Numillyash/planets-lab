#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOW_NON_MAIN="${PUBLIC_POSTINDEPENDENT_VALIDATION_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
FROZEN_CANDIDATE_COMMIT="46bcb08c2f0d3f0449b97921edb03ab6647f7d3b"
FROZEN_CANDIDATE_PATH="tools/diagnostics/combat_public_capture_side_postindependent_candidate.py"

if [[ "$ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: prospective post-independent acquisition must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  exit 64
fi

if ! git merge-base --is-ancestor "$FROZEN_CANDIDATE_COMMIT" HEAD; then
  echo "ERROR: HEAD does not contain the frozen post-independent candidate commit." >&2
  echo "required: $FROZEN_CANDIDATE_COMMIT" >&2
  exit 65
fi

if ! git diff --quiet "$FROZEN_CANDIDATE_COMMIT" -- "$FROZEN_CANDIDATE_PATH"; then
  echo "ERROR: post-independent candidate changed after validation freeze." >&2
  echo "candidate: $FROZEN_CANDIDATE_PATH" >&2
  echo "frozen:    $FROZEN_CANDIDATE_COMMIT" >&2
  exit 66
fi

exec bash tools/run-with-runtime-evidence.sh   public-postindependent-validation-acquisition   --include artifacts/public-postindependent-validation   --   bash tools/run-public-postindependent-validation-acquisition.sh
