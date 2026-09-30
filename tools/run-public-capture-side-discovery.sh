#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MANIFEST="${MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
INDEX="${INDEX:-validation/corpus/index/public-validation-games.jsonl}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/discovery-capture-side.json}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

for required in "$MANIFEST" "$INDEX"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

echo "===== PUBLIC CAPTURE-SIDE DISCOVERY: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
echo "docker:       ready"

echo "===== PUBLIC CAPTURE-SIDE DISCOVERY: BUILD LAB IMAGE ====="
docker compose build lab

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PUBLIC CAPTURE-SIDE DISCOVERY: HARVEST ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py \
  --manifest "$MANIFEST" \
  --index "$INDEX" \
  --archive-dir "$ARCHIVE_DIR" \
  --partition discovery \
  --output "$OUTPUT"

echo
echo "===== PUBLIC CAPTURE-SIDE DISCOVERY: COMPLETE ====="
echo "manifest:     $MANIFEST"
echo "index:        $INDEX"
echo "archive_dir:  $ARCHIVE_DIR"
echo "output:       $OUTPUT"
