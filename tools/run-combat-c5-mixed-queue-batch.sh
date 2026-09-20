#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "===== C5 MIXED QUEUE BATCH: HEAD ====="
git rev-parse HEAD
git status --short

echo
echo "===== C5 MIXED QUEUE BATCH: REGRESSION TESTS ====="
docker compose run --rm lab pytest -q \
  tests/test_combat_host_mixed_ship_planet_queue_batch_audit.py \
  tests/test_combat_host_queue_shape_audit.py \
  tests/test_combat_planet.py \
  tests/test_combat_planet_chain_audit.py \
  tests/test_combat_host_post_mutation_next_pair_audit.py \
  tests/test_combat_host_post_capture_initiator_population_audit.py \
  tests/test_combat_host_queue.py \
  tests/test_combat_mutable_queue.py

echo
echo "===== C5 MIXED QUEUE BATCH: FACTUAL QUEUE SHAPE ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_queue_shape_audit.py \
  --output /workspace/artifacts/combat-host-queue-shape-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: PLANET CARRY ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_planet_chain_audit.py \
  --output /workspace/artifacts/combat-planet-chain-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: SHIP NEXT-PAIR REGRESSION ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_mutation_next_pair_audit.py \
  --output /workspace/artifacts/combat-host-post-mutation-next-pair-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: POST-CAPTURE INITIATOR REGRESSION ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_post_capture_initiator_population_audit.py \
  --output /workspace/artifacts/combat-host-post-capture-initiator-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: MIXED SHIP/PLANET DISCOVERY ====="
docker compose run --rm lab python \
  tools/diagnostics/combat_host_mixed_ship_planet_queue_batch_audit.py \
  --output /workspace/artifacts/combat-host-mixed-ship-planet-queue-batch.json

echo
echo "===== C5 MIXED QUEUE BATCH: STATUS ====="
git status --short
