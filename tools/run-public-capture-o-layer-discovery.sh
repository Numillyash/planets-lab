#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DISCOVERY="${DISCOVERY:-artifacts/public-capture-side/discovery-capture-side.json}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/discovery-o-layer-probe.json}"
PARTS_DIR="${PARTS_DIR:-artifacts/public-capture-side/o-layer-parts}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"
PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
export PLANETS_CORPUS_DB_ROOT

if [[ ! -s "$DISCOVERY" ]]; then
  echo "ERROR: discovery artifact missing or empty: $DISCOVERY" >&2
  echo "Run tools/run-public-capture-side-discovery-with-evidence.sh first." >&2
  exit 66
fi

if [[ ! -s "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
  echo "ERROR: Corpus DB CURRENT missing: $PLANETS_CORPUS_DB_ROOT/CURRENT" >&2
  exit 66
fi

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
echo "docker:       ready"
echo "corpus_db:    $(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"

compose=(
  docker compose
  -f compose.yaml
  -f compose.corpus-db.yaml
)

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: BUILD LAB IMAGE ====="
"${compose[@]}" build lab

lab=(
  "${compose[@]}" run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: PROBE ====="
rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

mapfile -t GAME_IDS < <(
  "${lab[@]}" python - "$DISCOVERY" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ids = sorted({
    int(row["game_id"])
    for row in payload.get("observations", [])
    if isinstance(row, dict) and isinstance(row.get("game_id"), int)
})
for game_id in ids:
    print(game_id)
PY
)

if [[ "${#GAME_IDS[@]}" -eq 0 ]]; then
  echo "ERROR: no discovery ship-capture game ids found." >&2
  exit 65
fi

echo "game_passes:  ${#GAME_IDS[@]}"
position=0
for game_id in "${GAME_IDS[@]}"; do
  position=$((position + 1))
  part="$PARTS_DIR/game-${game_id}.json"
  echo
  echo "===== O-LAYER GAME ${position}/${#GAME_IDS[@]}: ${game_id} ====="
  "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py \
    --discovery "$DISCOVERY" \
    --corpus-db-root /corpus-db \
    --game-id "$game_id" \
    --output "$part"
done

echo
echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: MERGE ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_merge.py \
  --parts-dir "$PARTS_DIR" \
  --output "$OUTPUT"

echo
echo "===== PUBLIC CAPTURE O-LAYER DISCOVERY: COMPLETE ====="
echo "discovery:    $DISCOVERY"
echo "corpus_db:    $(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
echo "parts_dir:    $PARTS_DIR"
echo "output:       $OUTPUT"
