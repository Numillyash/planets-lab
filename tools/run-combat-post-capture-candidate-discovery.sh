#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/combat-post-capture-candidate-v3}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
COMPILED_DIR="${COMPILED_DIR:-validation/corpus/compiled/v1}"
INDEX="${INDEX:-$COMPILED_DIR/metadata/game_features.parquet}"
PROFILE="${PROFILE:-combat-planar-no-horwasp}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

mkdir -p "$ARTIFACT_DIR"
LOG_PATH="$ARTIFACT_DIR/gate.log"
exec > >(tee "$LOG_PATH") 2>&1

echo "===== POST-CAPTURE CANDIDATE DISCOVERY: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
if [[ ! -f "$INDEX" ]]; then
  echo "ERROR: feature index missing: $INDEX" >&2
  echo "Run the full combat feature-scope gate once before this narrow discovery gate." >&2
  exit 66
fi
if ! compgen -G "$ARCHIVE_DIR/game-*.zip" >/dev/null; then
  echo "ERROR: archive corpus missing under: $ARCHIVE_DIR" >&2
  exit 66
fi
echo "docker:  ready"
echo "index:   $INDEX"
echo "profile: $PROFILE"

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics
  lab
)

echo
echo "===== POST-CAPTURE CANDIDATE DISCOVERY: TARGETED TESTS ====="
"${lab[@]}" python -m pytest -q \
  tests/test_combat_host_capture_continuation_audit.py \
  tests/test_combat_host_post_capture_opponent_audit.py \
  tests/test_combat_host_post_capture_initiator_population_audit.py \
  tests/test_combat_host_post_capture_ship_candidate_audit.py \
  tests/test_combat_host_post_capture_special_movement_audit.py \
  tests/test_combat_host_post_capture_active_membership_audit.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py \
  tests/test_combat_host_queue.py

echo
echo "===== POST-CAPTURE CANDIDATE DISCOVERY: RUNTIME ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_capture_ship_candidate_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-capture-ship-candidates.json"

echo
echo "===== POST-CAPTURE CANDIDATE DISCOVERY: SPECIAL MOVEMENT RESIDUAL ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_capture_special_movement_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-capture-special-movement.json"

echo
echo "===== POST-CAPTURE CANDIDATE DISCOVERY: ACTIVE MEMBERSHIP ====="
"${lab[@]}" python tools/diagnostics/combat_host_post_capture_active_membership_audit.py \
  --archive-dir "$ARCHIVE_DIR" \
  --prepared-dir validation/corpus/compiled/v1/prepared \
  --feature-index "$INDEX" \
  --scope-profile "$PROFILE" \
  --output "$ARTIFACT_DIR/post-capture-active-membership.json"

echo
echo "===== POST-CAPTURE CANDIDATE DISCOVERY: COMPLETE ====="
echo "profile:    $PROFILE"
echo "candidates:       $ARTIFACT_DIR/post-capture-ship-candidates.json"
echo "special_movement: $ARTIFACT_DIR/post-capture-special-movement.json"
echo "active_membership:$ARTIFACT_DIR/post-capture-active-membership.json"
echo "full_log:         $LOG_PATH"
