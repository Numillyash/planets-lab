#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/combat-capture-reintegration-v1}"
PREDICTIVE_ARTIFACT_DIR="${PREDICTIVE_ARTIFACT_DIR:-artifacts/combat-predictive-queue-v1}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
PROFILE="${PROFILE:-combat-planar-no-horwasp}"

mkdir -p "$ARTIFACT_DIR"
LOG_PATH="$ARTIFACT_DIR/gate.log"
exec > >(tee "$LOG_PATH") 2>&1

DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"
echo "===== CAPTURE REINTEGRATION: DOCKER PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  echo "Restart Docker Desktop/backend, verify 'docker info', then rerun this gate." >&2
  exit 69
fi
echo "docker: ready"

echo
echo "===== CAPTURE REINTEGRATION: PREDICTIVE QUEUE CHECKPOINT ====="
ARTIFACT_DIR="$PREDICTIVE_ARTIFACT_DIR" \
ARCHIVE_DIR="$ARCHIVE_DIR" \
COMPILED_DIR="$COMPILED_DIR" \
INDEX="$INDEX" \
PROFILE="$PROFILE" \
bash tools/run-combat-predictive-queue-gate.sh

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
  lab
)

echo
echo "===== CAPTURE REINTEGRATION: TARGETED TESTS ====="
"${lab[@]}" python -m pytest -q \
  tests/test_combat_sequence.py \
  tests/test_combat_mutable_queue.py \
  tests/test_combat_host_capture_continuation_audit.py \
  tests/test_combat_host_post_capture_opponent_audit.py \
  tests/test_combat_host_post_capture_initiator_population_audit.py \
  tests/test_combat_host_post_capture_ship_candidate_audit.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py

echo
echo "===== CAPTURE REINTEGRATION: CAPTURE STATE DIFFERENTIAL ====="
"${lab[@]}" python tools/diagnostics/combat_host_capture_continuation_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/capture-continuation.json"

echo
echo "===== CAPTURE REINTEGRATION: OPPONENT INITIATOR DIFFERENTIAL ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_capture_initiator_population_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-capture-initiator.json"


echo
echo "===== CAPTURE REINTEGRATION: POST-CAPTURE SHIP CANDIDATE DISCOVERY ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_capture_ship_candidate_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-capture-ship-candidates.json"

echo "===== CAPTURE REINTEGRATION: ACCEPTANCE ====="
"${lab[@]}" python tools/diagnostics/combat_capture_reintegration_check.py \
  "$PREDICTIVE_ARTIFACT_DIR/integration.json" \
  "$ARTIFACT_DIR/capture-continuation.json" \
  "$ARTIFACT_DIR/post-capture-initiator.json" \
  --output "$ARTIFACT_DIR/integration.json"

echo
echo "===== CAPTURE REINTEGRATION: COMPLETE ====="
echo "profile:      $PROFILE"
echo "capture:      $ARTIFACT_DIR/capture-continuation.json"
echo "initiator:    $ARTIFACT_DIR/post-capture-initiator.json"
echo "candidates:   $ARTIFACT_DIR/post-capture-ship-candidates.json"
echo "integration:  $ARTIFACT_DIR/integration.json"
echo "full_log:     $LOG_PATH"
