#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MANIFEST="${MANIFEST:-validation/corpus/manifests/accounts-recent-finished.jsonl}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
DATABASE="${DATABASE:-$COMPILED_DIR/corpus.duckdb}"
BUILD_META="${BUILD_META:-$COMPILED_DIR/metadata/game_feature_build.json}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/corpus-feature-index-v1}"
REBUILD_DIR="$ARTIFACT_DIR/rebuild"

mkdir -p "$ARTIFACT_DIR" "$REBUILD_DIR"

echo "===== FEATURE INDEX: HEAD ====="
git rev-parse HEAD

echo
echo "===== FEATURE INDEX: TARGETED TESTS ====="
pytest -q   tests/test_feature_index.py   tests/test_combat_corpus_parity_audit.py

echo
echo "===== FEATURE INDEX: BUILD CURRENT CORPUS ====="
python -m planets_lab.corpus.feature_index_cli build   --manifest "$MANIFEST"   --archive-dir "$ARCHIVE_DIR"   --compiled-dir "$COMPILED_DIR"   --output "$INDEX"   --database "$DATABASE"   --build-meta "$BUILD_META"   --require-archives

echo
echo "===== FEATURE INDEX: DETERMINISTIC REBUILD ====="
python -m planets_lab.corpus.feature_index_cli build   --manifest "$MANIFEST"   --archive-dir "$ARCHIVE_DIR"   --compiled-dir "$COMPILED_DIR"   --output "$REBUILD_DIR/game_features.parquet"   --database "$REBUILD_DIR/corpus.duckdb"   --build-meta "$REBUILD_DIR/build.json"   --require-archives

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
python -m planets_lab.corpus.feature_index_cli select   --index "$INDEX"   --profile ordinary-classic   --output "$ARTIFACT_DIR/ordinary-classic.json"

echo
echo "===== FEATURE INDEX: COMBAT PARITY BASELINE ====="
python tools/diagnostics/combat_classic_corpus_parity_audit.py   --archive-dir "$ARCHIVE_DIR"   --output "$ARTIFACT_DIR/combat-baseline.json"

echo
echo "===== FEATURE INDEX: COMBAT PARITY ALL-INDEXED ====="
python tools/diagnostics/combat_classic_corpus_parity_audit.py   --archive-dir "$ARCHIVE_DIR"   --feature-index "$INDEX"   --feature-profile all-indexed   --output "$ARTIFACT_DIR/combat-all-indexed.json"

echo
echo "===== FEATURE INDEX: INTEGRATION PROOF ====="
python tools/diagnostics/corpus_feature_index_integration_check.py   "$ARTIFACT_DIR/combat-baseline.json"   "$ARTIFACT_DIR/combat-all-indexed.json"   --output "$ARTIFACT_DIR/combat-integration.json"

echo
echo "===== FEATURE INDEX: COMPLETE ====="
echo "index:              $INDEX"
echo "database:           $DATABASE"
echo "build_meta:         $BUILD_META"
echo "ordinary_selector:  $ARTIFACT_DIR/ordinary-classic.json"
echo "integration_proof:  $ARTIFACT_DIR/combat-integration.json"
echo "sha256:             $INDEX_SHA"
