#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
EXPECTED_CURRENT="${EXPECTED_CURRENT:-generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb}"
FROZEN_SELECTOR_IMPL_COMMIT="d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad"
export PLANETS_CORPUS_DB_ROOT="$CORPUS_DB_ROOT"

DISCOVERY_CAPTURE="$MAIN_ROOT/artifacts/public-capture-side/discovery-capture-side.json"
DISCOVERY_O="$MAIN_ROOT/artifacts/public-capture-side/discovery-o-layer-probe.json"
HELDOUT_CAPTURE="$MAIN_ROOT/artifacts/public-capture-side/heldout-capture-side.json"
HELDOUT_O="$MAIN_ROOT/artifacts/public-capture-side/heldout-o-layer-validation.json"
INDEPENDENT_CAPTURE="$MAIN_ROOT/artifacts/public-capture-side/independent-short32-capture-side.json"
INDEPENDENT_O="$MAIN_ROOT/artifacts/public-capture-side/independent-short32-postheldout-validation.json"

OUT_DIR="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence"
DISCOVERY_OUT="$OUT_DIR/discovery-o-c-forward-open.json"
HELDOUT_OUT="$OUT_DIR/heldout-o-c-forward-open.json"
INDEPENDENT_OUT="$OUT_DIR/independent-short32-o-c-forward-open.json"

DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== POST-CAPTURE O -> C-FORWARD OPEN-POPULATION DIFFERENTIAL ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_db:     $CORPUS_DB_ROOT"
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

if ! git -C "$RESEARCH_ROOT" merge-base --is-ancestor \
  "$FROZEN_SELECTOR_IMPL_COMMIT" "$research_head"; then
  echo "ERROR: research HEAD does not contain frozen selector implementation." >&2
  exit 3
fi

for frozen_path in \
  tools/research/postcapture_o_c_forward_selector.py \
  tools/research/postcapture_pair_bounds.py \
  tools/research/probe-postcapture-o-c-forward-open.py; do
  if ! git -C "$RESEARCH_ROOT" diff --quiet \
    "$FROZEN_SELECTOR_IMPL_COMMIT" -- "$frozen_path"; then
    echo "ERROR: frozen selector implementation changed after freeze." >&2
    echo "path:   $frozen_path" >&2
    echo "frozen: $FROZEN_SELECTOR_IMPL_COMMIT" >&2
    exit 4
  fi
done

if [[ ! -s "$CORPUS_DB_ROOT/CURRENT" ]]; then
  echo "ERROR: Corpus DB CURRENT missing: $CORPUS_DB_ROOT/CURRENT" >&2
  exit 66
fi
actual_current="$(tr -d '
' < "$CORPUS_DB_ROOT/CURRENT")"
if [[ "$actual_current" != "$EXPECTED_CURRENT" ]]; then
  echo "ERROR: O/C forward differential requires canonical public68 CURRENT." >&2
  echo "expected: $EXPECTED_CURRENT" >&2
  echo "actual:   $actual_current" >&2
  exit 67
fi

for required in   "$DISCOVERY_CAPTURE" "$DISCOVERY_O"   "$HELDOUT_CAPTURE" "$HELDOUT_O"   "$INDEPENDENT_CAPTURE" "$INDEPENDENT_O"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required artifact missing or empty: $required" >&2
    exit 66
  fi
done

if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi

echo "research HEAD:  $research_head"
echo "main HEAD:      $main_head"
echo "corpus CURRENT: $actual_current"
echo "selector impl:  $FROZEN_SELECTOR_IMPL_COMMIT"
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

echo "===== FROZEN SELECTOR UNIT TESTS ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q     /research/tests/test_postcapture_o_c_forward_selector.py     /research/tests/test_postcapture_o_c_topology.py     /research/tests/test_postcapture_o_c_independent.py
)
echo

mkdir -p "$OUT_DIR"

run_probe() {
  local label="$1"
  local capture="$2"
  local capture_partition="$3"
  local olayer="$4"
  local olayer_partition="$5"
  local output="$6"

  echo "===== O/C FORWARD: $label ====="
  (
    cd "$MAIN_ROOT"
    "${lab[@]}" python       /research/tools/research/probe-postcapture-o-c-forward-open.py       --main-root /workspace       --corpus-db-root /corpus-db       --capture-report "$capture"       --capture-partition "$capture_partition"       --o-layer-report "$olayer"       --o-layer-partition "$olayer_partition"       --label "$label"       --output "$output"
  )
  echo
}

# Paths passed inside the lab container use /workspace and /research.
run_probe   discovery   /workspace/artifacts/public-capture-side/discovery-capture-side.json   discovery   /workspace/artifacts/public-capture-side/discovery-o-layer-probe.json   discovery   /research/artifacts/external-sources/postcapture-occurrence/discovery-o-c-forward-open.json

run_probe   heldout   /workspace/artifacts/public-capture-side/heldout-capture-side.json   heldout   /workspace/artifacts/public-capture-side/heldout-o-layer-validation.json   heldout   /research/artifacts/external-sources/postcapture-occurrence/heldout-o-c-forward-open.json

run_probe   independent-short32   /workspace/artifacts/public-capture-side/independent-short32-capture-side.json   all   /workspace/artifacts/public-capture-side/independent-short32-postheldout-validation.json   independent   /research/artifacts/external-sources/postcapture-occurrence/independent-short32-o-c-forward-open.json

echo "===== COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "discovery:     $DISCOVERY_OUT"
echo "heldout:       $HELDOUT_OUT"
echo "independent:   $INDEPENDENT_OUT"
echo
echo "Evidence: OPEN_POPULATION_FITTING_DIFFERENTIAL"
echo "No selector component was modified from runtime outcomes."
