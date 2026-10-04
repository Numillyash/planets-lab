#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"

DISCOVERY="$MAIN_ROOT/artifacts/public-capture-side/discovery-o-layer-probe.json"
HELDOUT="$MAIN_ROOT/artifacts/public-capture-side/heldout-o-layer-validation.json"
OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/public-o-c-topology-census.json"

echo "===== POST-CAPTURE O/C TOPOLOGY CENSUS ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "discovery:     $DISCOVERY"
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

for required in "$DISCOVERY" "$HELDOUT"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required O-layer artifact missing or empty: $required" >&2
    echo "This census intentionally does not rebuild or reopen a partition." >&2
    exit 66
  fi
done

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo

cd "$RESEARCH_ROOT"

echo "===== TOPOLOGY ANALYZER UNIT TESTS ====="
python3 -m pytest -q tests/test_postcapture_o_c_topology.py
echo

python3 tools/research/analyze-postcapture-o-c-topology.py \
  --discovery "$DISCOVERY" \
  --heldout "$HELDOUT" \
  --output "$OUTPUT"

echo
echo "===== COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "output:        $OUTPUT"
echo
echo "Position-only census; no pair selector was fitted."
