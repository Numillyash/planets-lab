#!/usr/bin/env bash
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"

mkdir -p artifacts
LOG_PATH="artifacts/combat-c5-mixed-queue-batch.log"
exec > >(tee "$LOG_PATH") 2>&1

declare -a STAGE_NAMES=()
declare -a STAGE_RCS=()
OVERALL_RC=0

run_stage() {
  local name="$1"
  shift
  echo
  echo "===== C5 MIXED QUEUE BATCH: ${name} ====="
  "$@"
  local rc=$?
  STAGE_NAMES+=("$name")
  STAGE_RCS+=("$rc")
  if [[ "$rc" -ne 0 ]]; then
    OVERALL_RC=1
  fi
  echo "===== STAGE RESULT: ${name} rc=${rc} ====="
  return 0
}

echo "===== C5 MIXED QUEUE BATCH: HEAD ====="
git rev-parse HEAD
git status --short

run_stage "REGRESSION TESTS" \
  docker compose run --rm lab pytest -q \
    tests/test_combat_host_mixed_ship_planet_queue_batch_audit.py \
    tests/test_combat_host_queue_shape_audit.py \
    tests/test_combat_planet.py \
    tests/test_combat_planet_chain_audit.py \
    tests/test_combat_host_post_mutation_next_pair_audit.py \
    tests/test_combat_host_post_capture_initiator_population_audit.py \
    tests/test_combat_host_queue.py \
    tests/test_combat_mutable_queue.py

run_stage "FACTUAL QUEUE SHAPE" \
  docker compose run --rm lab python \
    tools/diagnostics/combat_host_queue_shape_audit.py \
    --output /workspace/artifacts/combat-host-queue-shape-batch.json

run_stage "PLANET CARRY" \
  docker compose run --rm lab python \
    tools/diagnostics/combat_planet_chain_audit.py \
    --output /workspace/artifacts/combat-planet-chain-batch.json

run_stage "SHIP NEXT-PAIR REGRESSION" \
  docker compose run --rm lab python \
    tools/diagnostics/combat_host_post_mutation_next_pair_audit.py \
    --example-limit 20 \
    --output /workspace/artifacts/combat-host-post-mutation-next-pair-batch.json

run_stage "POST-CAPTURE INITIATOR REGRESSION" \
  docker compose run --rm lab python \
    tools/diagnostics/combat_host_post_capture_initiator_population_audit.py \
    --example-limit 20 \
    --output /workspace/artifacts/combat-host-post-capture-initiator-batch.json

run_stage "MIXED SHIP/PLANET DISCOVERY" \
  docker compose run --rm lab python \
    tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py \
    --example-limit 20 \
    --output /workspace/artifacts/combat-host-mixed-ship-planet-queue-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: STAGE SUMMARY ====="
for i in "${!STAGE_NAMES[@]}"; do
  printf '%-40s rc=%s\n' "${STAGE_NAMES[$i]}" "${STAGE_RCS[$i]}"
done

echo
echo "===== C5 MIXED QUEUE BATCH: STATUS ====="
git status --short

echo
echo "full_log: $LOG_PATH"

exit "$OVERALL_RC"
