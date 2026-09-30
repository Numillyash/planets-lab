#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DISCOVERY="${DISCOVERY:-artifacts/public-capture-side/discovery-capture-side.json}"
ARCHIVE_DIR="${ARCHIVE_DIR:-validation/corpus/cache/loadall}"
APPEARANCE_CACHE_DIR="${APPEARANCE_CACHE_DIR:-validation/corpus/cache/public-capture-side-v1}"
PREPARED_DIR="${PREPARED_DIR:-validation/corpus/cache/prepared-v1}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/discovery-o-layer-probe.json}"
PARTS_DIR="${PARTS_DIR:-artifacts/public-capture-side/o-layer-parts}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

if [[ ! -s "$DISCOVERY" ]]; then
  echo "ERROR: discovery artifact missing or empty: $DISCOVERY" >&2
  echo "Run tools/run-public-capture-side-discovery-with-evidence.sh first." >&2
  exit 66
fi

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
echo "docker:       ready"

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: BUILD LAB IMAGE ====="
docker compose build lab

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: PROBE ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py   --discovery "$DISCOVERY"   --archive-dir "$ARCHIVE_DIR"   --appearance-cache-dir "$APPEARANCE_CACHE_DIR"   --prepared-dir "$PREPARED_DIR"   --output "$OUTPUT"

echo
echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: COMPLETE ====="
echo "discovery:    $DISCOVERY"
echo "archive_dir:  $ARCHIVE_DIR"
echo "cache_dir:    $APPEARANCE_CACHE_DIR"
echo "prepared_dir: $PREPARED_DIR"
echo "output:       $OUTPUT"
