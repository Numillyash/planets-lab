#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOW_NON_MAIN="${PUBLIC_CAPTURE_SIDE_INDEPENDENT_ALLOW_NON_MAIN:-0}"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
FROZEN_CANDIDATE_COMMIT="592607b07efa0f857521da05fe0651127ed8be2d"

if [[ "$ALLOW_NON_MAIN" != "1" && "$SOURCE_BRANCH" != "main" ]]; then
  echo "ERROR: independent validation must run from main." >&2
  echo "current branch: ${SOURCE_BRANCH:-DETACHED}" >&2
  exit 64
fi

if ! git merge-base --is-ancestor "$FROZEN_CANDIDATE_COMMIT" HEAD; then
  echo "ERROR: HEAD does not contain the frozen post-heldout candidate commit." >&2
  echo "required: $FROZEN_CANDIDATE_COMMIT" >&2
  exit 65
fi

FROZEN_CANDIDATE_PATH="tools/diagnostics/combat_public_capture_side_postheldout_candidate.py"
if ! git diff --quiet "$FROZEN_CANDIDATE_COMMIT" -- "$FROZEN_CANDIDATE_PATH"; then
  echo "ERROR: frozen post-heldout candidate changed after freeze." >&2
  echo "candidate: $FROZEN_CANDIDATE_PATH" >&2
  echo "frozen:    $FROZEN_CANDIDATE_COMMIT" >&2
  exit 66
fi

exec bash tools/run-with-runtime-evidence.sh   public-capture-side-independent-validation   --include artifacts/public-capture-side   --   bash tools/run-public-capture-side-independent-validation.sh
