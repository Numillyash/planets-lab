#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
export PLANETS_CORPUS_DB_ROOT="$CORPUS_DB_ROOT"

HELDOUT="$MAIN_ROOT/artifacts/public-capture-side/heldout-capture-side.json"
MANIFEST="$MAIN_ROOT/validation/corpus/manifests/public-validation-selected.jsonl"
INDEX="$MAIN_ROOT/validation/corpus/index/public-validation-games.jsonl"
OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/heldout-occurrence-round.json"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== POST-CAPTURE OCCURRENCE-ROUND SECONDARY HELDOUT GATE ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_db:     $CORPUS_DB_ROOT"
echo "heldout:       $HELDOUT"
echo "output:        $OUTPUT"
echo

research_branch="$(git -C "$RESEARCH_ROOT" branch --show-current)"
research_head="$(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
main_branch="$(git -C "$MAIN_ROOT" branch --show-current)"
main_head="$(git -C "$MAIN_ROOT" rev-parse HEAD)"
main_origin="$(git -C "$MAIN_ROOT" rev-parse origin/main)"

if [[ "$research_branch" != "research/external-engine-analysis" ]]; then
  echo "ERROR: research checkout is on $research_branch" >&2
  exit 2
fi
if [[ "$main_branch" != "main" ]]; then
  echo "ERROR: canonical checkout is on $main_branch, expected main" >&2
  exit 2
fi
if [[ "$main_head" != "$main_origin" ]]; then
  echo "ERROR: canonical main checkout is not at origin/main" >&2
  echo "  HEAD:        $main_head" >&2
  echo "  origin/main: $main_origin" >&2
  exit 2
fi
if [[ ! -s "$CORPUS_DB_ROOT/CURRENT" ]]; then
  echo "ERROR: Corpus DB CURRENT missing: $CORPUS_DB_ROOT/CURRENT" >&2
  exit 66
fi
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "corpus CURRENT: $(cat "$CORPUS_DB_ROOT/CURRENT")"
echo

compose=(
  docker compose
  -f "$MAIN_ROOT/compose.yaml"
  -f "$MAIN_ROOT/compose.corpus-db.yaml"
)

echo "===== BUILD/REUSE CANONICAL MAIN LAB IMAGE ====="
(
  cd "$MAIN_ROOT"
  "${compose[@]}" build lab
)
echo

lab=(
  "${compose[@]}" run --rm -T
  -v "$RESEARCH_ROOT:/research"
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics:/research/tools/research
  lab
)

if [[ ! -s "$HELDOUT" ]]; then
  echo "===== REBUILD HELDOUT CAPTURE-SIDE ARTIFACT ====="
  for required in "$MANIFEST" "$INDEX"; do
    if [[ ! -s "$required" ]]; then
      echo "ERROR: heldout artifact missing and prerequisite missing: $required" >&2
      exit 66
    fi
  done
  (
    cd "$MAIN_ROOT"
    "${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py       --manifest validation/corpus/manifests/public-validation-selected.jsonl       --index validation/corpus/index/public-validation-games.jsonl       --partition heldout       --corpus-db-root /corpus-db       --output artifacts/public-capture-side/heldout-capture-side.json
  )
  echo
fi

echo "===== FROZEN CANDIDATE UNIT TESTS ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q     /research/tests/test_postcapture_occurrence_candidates.py
)
echo

echo "===== SECONDARY HELDOUT DIFFERENTIAL ====="
mkdir -p "$(dirname "$OUTPUT")"
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python     /research/tools/research/probe-postcapture-occurrence-round-heldout.py     --main-root /workspace     --corpus-db-root /corpus-db     --heldout /workspace/artifacts/public-capture-side/heldout-capture-side.json     --output /research/artifacts/external-sources/postcapture-occurrence/heldout-occurrence-round.json
)

echo
echo "===== COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "output:        $OUTPUT"
echo
echo "Evidence label: SECONDARY_HELDOUT_DISCRIMINATOR"
echo "This public partition was previously opened for LEFT/RIGHT work."
echo "Candidate definitions were frozen before this queue-specific evaluation."
