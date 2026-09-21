#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

branch="$(git symbolic-ref --quiet --short HEAD)"
if [[ "$branch" != "main" ]]; then
  echo "ERROR: combat feature-scope gate must run from main; current branch=$branch" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: checkout is not clean" >&2
  git status --short >&2
  exit 2
fi

git fetch origin main
remote_main="$(git rev-parse FETCH_HEAD)"
gate_head="$(git rev-parse HEAD)"
if [[ "$gate_head" != "$remote_main" ]]; then
  echo "ERROR: checkout is not actual fetched origin/main" >&2
  printf 'HEAD=%s\nFETCHED_MAIN=%s\n' "$gate_head" "$remote_main" >&2
  exit 2
fi

ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
DATABASE="${DATABASE:-$COMPILED_DIR/corpus.duckdb}"
BUILD_META="${BUILD_META:-$COMPILED_DIR/metadata/game_feature_build.json}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/combat-feature-scope-v1}"
PROFILE="${PROFILE:-combat-planar-no-horwasp}"

mkdir -p "$ARTIFACT_DIR"

echo "===== COMBAT FEATURE SCOPE: BUILD LAB IMAGE ====="
docker compose build lab

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
  lab
)

echo "===== COMBAT FEATURE SCOPE: HEAD ====="
echo "$gate_head"

echo
echo "===== COMBAT FEATURE SCOPE: TARGETED TESTS ====="
"${lab[@]}" python -m pytest -q \
  tests/test_feature_index.py \
  tests/test_combat_planet_chain_audit.py \
  tests/test_combat_ship_chain_audit.py \
  tests/test_combat_ship_chain_phase_audit.py \
  tests/test_combat_ship_chain_cluster_audit.py

echo
echo "===== COMBAT FEATURE SCOPE: REBUILD FEATURE INDEX ====="
"${lab[@]}" python -m planets_lab.corpus.feature_index_cli build \
  --archive-dir "$ARCHIVE_DIR" \
  --compiled-dir "$COMPILED_DIR" \
  --output "$INDEX" \
  --database "$DATABASE" \
  --build-meta "$BUILD_META" \
  --require-archives

echo
echo "===== COMBAT FEATURE SCOPE: SELECTOR ====="
"${lab[@]}" python -m planets_lab.corpus.feature_index_cli select \
  --index "$INDEX" \
  --profile "$PROFILE" \
  --output "$ARTIFACT_DIR/selection.json"

echo
echo "===== COMBAT FEATURE SCOPE: PLANET CHAIN ====="
"${lab[@]}" python tools/diagnostics/combat_planet_chain_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/planet-chain.json"

echo
echo "===== COMBAT FEATURE SCOPE: SHIP PHASE ====="
"${lab[@]}" python tools/diagnostics/combat_ship_chain_phase_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/ship-phase.json"

echo
echo "===== COMBAT FEATURE SCOPE: SHIP CLUSTER ====="
"${lab[@]}" python tools/diagnostics/combat_ship_chain_cluster_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/ship-cluster.json"

echo
echo "===== COMBAT FEATURE SCOPE: CHECKPOINT CONTINUITY ====="
"${lab[@]}" python tools/diagnostics/combat_feature_scope_integration_check.py \
  "$ARTIFACT_DIR/planet-chain.json" \
  "$ARTIFACT_DIR/ship-phase.json" \
  "$ARTIFACT_DIR/ship-cluster.json" \
  --output "$ARTIFACT_DIR/integration.json"

test "$(git rev-parse HEAD)" = "$gate_head"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: gate changed tracked working-tree state" >&2
  git status --short >&2
  exit 1
fi

echo
echo "===== COMBAT FEATURE SCOPE: COMPLETE ====="
echo "profile:      $PROFILE"
echo "selection:    $ARTIFACT_DIR/selection.json"
echo "planet:       $ARTIFACT_DIR/planet-chain.json"
echo "ship_phase:   $ARTIFACT_DIR/ship-phase.json"
echo "ship_cluster: $ARTIFACT_DIR/ship-cluster.json"
echo "integration:  $ARTIFACT_DIR/integration.json"
