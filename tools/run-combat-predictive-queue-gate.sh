#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/combat-predictive-queue-v1}"
FEATURE_ARTIFACT_DIR="${FEATURE_ARTIFACT_DIR:-artifacts/combat-feature-scope-v1}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
PROFILE="${PROFILE:-combat-planar-no-horwasp}"

mkdir -p "$ARTIFACT_DIR"
LOG_PATH="$ARTIFACT_DIR/gate.log"
exec > >(tee "$LOG_PATH") 2>&1

echo "===== PREDICTIVE COMBAT QUEUE: FEATURE SCOPE ACCEPTANCE ====="
ARTIFACT_DIR="$FEATURE_ARTIFACT_DIR" \
ARCHIVE_DIR="$ARCHIVE_DIR" \
COMPILED_DIR="$COMPILED_DIR" \
INDEX="$INDEX" \
PROFILE="$PROFILE" \
bash tools/run-combat-feature-scope-gate.sh

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
  lab
)

echo
echo "===== PREDICTIVE COMBAT QUEUE: TARGETED TESTS ====="
"${lab[@]}" python -m pytest -q \
  tests/test_combat_order.py \
  tests/test_combat_eligibility.py \
  tests/test_combat_selection.py \
  tests/test_combat_queue.py \
  tests/test_combat_host_queue.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_effective_state.py \
  tests/test_combat_standard_targetability.py \
  tests/test_combat_sequence.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py

echo
echo "===== PREDICTIVE COMBAT QUEUE: HELD-OUT NEXT VCR ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_mutation_next_pair_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-mutation-next-pair.json"

echo
echo "===== PREDICTIVE COMBAT QUEUE: ACCEPTANCE ====="
"${lab[@]}" python tools/diagnostics/combat_predictive_queue_integration_check.py \
  "$FEATURE_ARTIFACT_DIR/integration.json" \
  "$ARTIFACT_DIR/post-mutation-next-pair.json" \
  --output "$ARTIFACT_DIR/integration.json"

echo
echo "===== PREDICTIVE COMBAT QUEUE: COMPLETE ====="
echo "profile:       $PROFILE"
echo "queue_report:  $ARTIFACT_DIR/post-mutation-next-pair.json"
echo "integration:   $ARTIFACT_DIR/integration.json"
echo "full_log:      $LOG_PATH"
