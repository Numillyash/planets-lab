#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
export PLANETS_CORPUS_DB_ROOT="$CORPUS_DB_ROOT"

DISCOVERY="$MAIN_ROOT/artifacts/public-capture-side/discovery-capture-side.json"
OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/discovery-occurrence-round.json"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== POST-CAPTURE OCCURRENCE-ROUND DISCOVERY GATE ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_db:     $CORPUS_DB_ROOT"
echo "discovery:     $DISCOVERY"
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
if [[ ! -s "$DISCOVERY" ]]; then
  echo "ERROR: discovery capture-side artifact missing: $DISCOVERY" >&2
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

echo "===== OCCURRENCE CANDIDATE UNIT TESTS ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q     /research/tests/test_postcapture_occurrence_candidates.py
)
echo

echo "===== DISCOVERY DIFFERENTIAL ====="
mkdir -p "$(dirname "$OUTPUT")"
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python     /research/tools/research/probe-postcapture-occurrence-round-discovery.py     --main-root /workspace     --corpus-db-root /corpus-db     --discovery /workspace/artifacts/public-capture-side/discovery-capture-side.json     --output /research/artifacts/external-sources/postcapture-occurrence/discovery-occurrence-round.json
)

echo
echo "===== COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "output:        $OUTPUT"
echo "Held-out was not read."
