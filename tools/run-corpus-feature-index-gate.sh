#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

branch="$(git symbolic-ref --quiet --short HEAD)"
if [[ "$branch" != "main" ]]; then
  echo "ERROR: corpus feature-index gate must run from main; current branch=$branch" >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: checkout is not clean; preserve or commit local changes first" >&2
  git status --short >&2
  exit 2
fi

git fetch origin main
remote_main="$(git rev-parse FETCH_HEAD)"
gate_head="$(git rev-parse HEAD)"
if [[ "$gate_head" != "$remote_main" ]]; then
  echo "ERROR: checkout is not actual fetched origin/main; update with --ff-only first" >&2
  printf 'HEAD=%s\nFETCHED_MAIN=%s\n' "$gate_head" "$remote_main" >&2
  exit 2
fi

MANIFEST="${MANIFEST:-validation/corpus/manifests/accounts-recent-finished.jsonl}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
DATABASE="${DATABASE:-$COMPILED_DIR/corpus.duckdb}"
BUILD_META="${BUILD_META:-$COMPILED_DIR/metadata/game_feature_build.json}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/corpus-feature-index-v1}"
REBUILD_DIR="$ARTIFACT_DIR/rebuild"

mkdir -p "$ARTIFACT_DIR" "$REBUILD_DIR"

echo "===== FEATURE INDEX: BUILD LAB IMAGE ====="
docker compose build lab

# The repository is a src-layout Python package and requires Python >=3.11.
# Run the gate in the project's Docker service rather than depending on a host
# editable install or the host Python version. The bind mount keeps all compiled
# outputs in the checkout paths above.
lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
  lab
)

echo "===== FEATURE INDEX: HEAD ====="
echo "$gate_head"

echo
echo "===== FEATURE INDEX: PYTHON ENV ====="
"${lab[@]}" python - <<'PY'
import sys
import planets_lab
print("python=", sys.version.replace("\n", " "))
print("planets_lab=", planets_lab.__file__)
assert sys.version_info >= (3, 11)
assert planets_lab.__file__.startswith("/workspace/src/")
PY

echo
echo "===== FEATURE INDEX: TARGETED TESTS ====="
"${lab[@]}" python -m pytest -q \
  tests/test_feature_index.py \
  tests/test_combat_corpus_parity_audit.py

echo
echo "===== FEATURE INDEX: BUILD CURRENT CORPUS ====="
"${lab[@]}" python -m planets_lab.corpus.feature_index_cli build \
  --manifest "$MANIFEST" \
  --archive-dir "$ARCHIVE_DIR" \
  --compiled-dir "$COMPILED_DIR" \
  --output "$INDEX" \
  --database "$DATABASE" \
  --build-meta "$BUILD_META" \
  --require-archives

echo
echo "===== FEATURE INDEX: DETERMINISTIC REBUILD ====="
"${lab[@]}" python -m planets_lab.corpus.feature_index_cli build \
  --manifest "$MANIFEST" \
  --archive-dir "$ARCHIVE_DIR" \
  --compiled-dir "$COMPILED_DIR" \
  --output "$REBUILD_DIR/game_features.parquet" \
  --database "$REBUILD_DIR/corpus.duckdb" \
  --build-meta "$REBUILD_DIR/build.json" \
  --require-archives

INDEX_SHA="$(sha256sum "$INDEX" | awk '{print $1}')"
REBUILD_SHA="$(sha256sum "$REBUILD_DIR/game_features.parquet" | awk '{print $1}')"
echo "primary_sha256: $INDEX_SHA"
echo "rebuild_sha256: $REBUILD_SHA"
if [[ "$INDEX_SHA" != "$REBUILD_SHA" ]]; then
  echo "ERROR: deterministic feature-index rebuild differs" >&2
  exit 1
fi

echo
echo "===== FEATURE INDEX: ORDINARY CLASSIC SELECTOR ====="
"${lab[@]}" python -m planets_lab.corpus.feature_index_cli select \
  --index "$INDEX" \
  --profile ordinary-classic \
  --output "$ARTIFACT_DIR/ordinary-classic.json"

echo
echo "===== FEATURE INDEX: COMBAT PARITY BASELINE ====="
"${lab[@]}" python tools/diagnostics/combat_classic_corpus_parity_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --output "$ARTIFACT_DIR/combat-baseline.json"

echo
echo "===== FEATURE INDEX: COMBAT PARITY ALL-INDEXED ====="
"${lab[@]}" python tools/diagnostics/combat_classic_corpus_parity_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --feature-profile all-indexed \
  --output "$ARTIFACT_DIR/combat-all-indexed.json"

echo
echo "===== FEATURE INDEX: INTEGRATION PROOF ====="
"${lab[@]}" python tools/diagnostics/corpus_feature_index_integration_check.py \
  "$ARTIFACT_DIR/combat-baseline.json" \
  "$ARTIFACT_DIR/combat-all-indexed.json" \
  --output "$ARTIFACT_DIR/combat-integration.json"

test "$(git rev-parse HEAD)" = "$gate_head"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: gate changed tracked working-tree state" >&2
  git status --short >&2
  exit 1
fi

echo
echo "===== FEATURE INDEX: COMPLETE ====="
echo "index:              $INDEX"
echo "database:           $DATABASE"
echo "build_meta:         $BUILD_META"
echo "ordinary_selector:  $ARTIFACT_DIR/ordinary-classic.json"
echo "integration_proof:  $ARTIFACT_DIR/combat-integration.json"
echo "sha256:             $INDEX_SHA"
