#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
PUBLIC100_REL="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
PUBLIC100_SHA="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"
SELECTOR_REPORT="${SELECTOR_REPORT:-$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-o-c-forward-independent.json}"
OUT_DIR="${OUT_DIR:-$RESEARCH_ROOT/artifacts/external-sources/postcapture-site-transition}"
OUTPUT="$OUT_DIR/game400330-t141-v592-595.json"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== MUTABLE SITE TRANSITION INTEGRATION ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_root:   $CORPUS_ROOT"
echo "selector:      $SELECTOR_REPORT"
echo

research_branch="$(git -C "$RESEARCH_ROOT" branch --show-current)"
research_head="$(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
main_branch="$(git -C "$MAIN_ROOT" branch --show-current)"
main_head="$(git -C "$MAIN_ROOT" rev-parse HEAD)"
main_origin="$(git -C "$MAIN_ROOT" rev-parse origin/main)"

if [[ "$research_branch" != "research/external-engine-analysis" ]]; then
  echo "ERROR: research checkout is on $research_branch; expected research/external-engine-analysis" >&2
  exit 64
fi
if [[ "$main_branch" != "main" || "$main_head" != "$main_origin" ]]; then
  echo "ERROR: canonical main checkout must be cleanly positioned at origin/main" >&2
  echo "branch:      $main_branch" >&2
  echo "HEAD:        $main_head" >&2
  echo "origin/main: $main_origin" >&2
  exit 64
fi
if [[ ! -s "$SELECTOR_REPORT" ]]; then
  echo "ERROR: independent selector report is missing: $SELECTOR_REPORT" >&2
  echo "Run tools/research/run-postcapture-o-c-forward-independent-with-evidence.sh first." >&2
  exit 66
fi

public100="$CORPUS_ROOT/$PUBLIC100_REL"
if [[ ! -f "$public100" ]]; then
  echo "ERROR: public100 generation missing: $public100" >&2
  exit 67
fi
actual_sha="$(sha256sum "$public100" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA mismatch" >&2
  echo "expected: $PUBLIC100_SHA" >&2
  echo "actual:   $actual_sha" >&2
  exit 67
fi

if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi

compose=(
  docker compose
  -f "$MAIN_ROOT/compose.yaml"
  -f "$MAIN_ROOT/compose.corpus-db.yaml"
)

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "public100:     $PUBLIC100_REL"
echo "public100 SHA: $actual_sha"
echo

echo "===== BUILD/REUSE MAIN LAB IMAGE ====="
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

echo "===== TARGETED TESTS ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q     /research/tests/test_postcapture_o_c_forward_selector.py     /research/tests/test_postcapture_site_transition_executor.py
)
echo

mkdir -p "$OUT_DIR"

echo "===== GAME 400330 T141 V592->595 ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python /research/tools/research/probe-postcapture-site-transition-chain.py     --corpus-db-root /corpus-db     --corpus-db-generation "$PUBLIC100_REL"     --selector-report /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-o-c-forward-independent.json     --game-id 400330     --battle-turn 141     --x 1674     --y 2363     --start-vcr 592     --end-vcr 595     --output /research/artifacts/external-sources/postcapture-site-transition/game400330-t141-v592-595.json
)
echo

echo "===== COMPLETE ====="
echo "output: $OUTPUT"
