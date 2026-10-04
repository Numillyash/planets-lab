#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
export PLANETS_CORPUS_DB_ROOT="$CORPUS_DB_ROOT"

HELDOUT_CAPTURE="$MAIN_ROOT/artifacts/public-capture-side/heldout-capture-side.json"
DISCOVERY_CAPTURE="$MAIN_ROOT/artifacts/public-capture-side/discovery-capture-side.json"
HELDOUT_PAIR="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/heldout-competitor-pair-recomposition.json"
DISCOVERY_RANK2="$RESEARCH_ROOT/artifacts/external-sources/afsim-r1/discovery-rank2-targeted.json"

HELDOUT_OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/heldout-genuine-queue-cursor-diagnostic.json"
DISCOVERY_OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/discovery-rank2-cursor-diagnostic.json"

DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== POST-CAPTURE RESIDUAL CURSOR UNIFICATION GATE ====="
echo "research_root:   $RESEARCH_ROOT"
echo "main_root:       $MAIN_ROOT"
echo "corpus_db:       $CORPUS_DB_ROOT"
echo "heldout_capture: $HELDOUT_CAPTURE"
echo "discovery_capture:$DISCOVERY_CAPTURE"
echo "heldout_pair:    $HELDOUT_PAIR"
echo "discovery_rank2: $DISCOVERY_RANK2"
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

for required in   "$CORPUS_DB_ROOT/CURRENT"   "$HELDOUT_CAPTURE"   "$DISCOVERY_CAPTURE"   "$HELDOUT_PAIR"   "$DISCOVERY_RANK2"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi

echo "research HEAD:  $research_head"
echo "main HEAD:      $main_head"
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

echo "===== HELDOUT GENUINE RESIDUAL CURSOR ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python     /research/tools/research/probe-postcapture-heldout-cursor-residuals.py     --main-root /workspace     --corpus-db-root /corpus-db     --capture-side /workspace/artifacts/public-capture-side/heldout-capture-side.json     --pair-residuals /research/artifacts/external-sources/postcapture-occurrence/heldout-competitor-pair-recomposition.json     --output /research/artifacts/external-sources/postcapture-occurrence/heldout-genuine-queue-cursor-diagnostic.json
)
echo

echo "===== DISCOVERY RANK>1 RESIDUAL CURSOR ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python     /research/tools/research/probe-postcapture-discovery-rank2-cursor.py     --main-root /workspace     --corpus-db-root /corpus-db     --capture-side /workspace/artifacts/public-capture-side/discovery-capture-side.json     --rank2 /research/artifacts/external-sources/afsim-r1/discovery-rank2-targeted.json     --output /research/artifacts/external-sources/postcapture-occurrence/discovery-rank2-cursor-diagnostic.json
)

echo
echo "===== COMPLETE ====="
echo "research HEAD:   $research_head"
echo "main HEAD:       $main_head"
echo "heldout output:  $HELDOUT_OUTPUT"
echo "discovery output:$DISCOVERY_OUTPUT"
echo
echo "No new queue rule was fitted."
echo "c2ng remains an EXTERNAL_IMPLEMENTATION comparator only."
