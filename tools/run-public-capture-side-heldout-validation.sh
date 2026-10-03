#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MANIFEST="${MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
INDEX="${INDEX:-validation/corpus/index/public-validation-games.jsonl}"
CAPTURE_REPORT="${CAPTURE_REPORT:-artifacts/public-capture-side/heldout-capture-side.json}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/heldout-o-layer-validation.json}"
PARTS_DIR="${PARTS_DIR:-artifacts/public-capture-side/o-layer-heldout-parts}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"
PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
export PLANETS_CORPUS_DB_ROOT

for required in "$MANIFEST" "$INDEX" "$PLANETS_CORPUS_DB_ROOT/CURRENT"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

echo "===== PUBLIC CAPTURE-SIDE HELDOUT: PREFLIGHT ====="
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

echo "===== PUBLIC CAPTURE-SIDE HELDOUT: BUILD LAB IMAGE ====="
"${compose[@]}" build lab

lab=(
  "${compose[@]}" run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PUBLIC CAPTURE-SIDE HELDOUT: DB HARVEST ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py \
  --manifest "$MANIFEST" \
  --index "$INDEX" \
  --partition heldout \
  --corpus-db-root /corpus-db \
  --output "$CAPTURE_REPORT"

rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

mapfile -t GAME_IDS < <(
  "${lab[@]}" python - "$CAPTURE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("partition") != "heldout":
    raise SystemExit("capture report is not heldout")
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
  echo "ERROR: heldout partition contains no ship capture observations." >&2
  exit 65
fi

echo
echo "===== PUBLIC CAPTURE O-LAYER HELDOUT: PROBE ====="
echo "game_passes:  ${#GAME_IDS[@]}"
position=0
for game_id in "${GAME_IDS[@]}"; do
  position=$((position + 1))
  part="$PARTS_DIR/game-${game_id}.json"
  echo
  echo "===== HELDOUT O-LAYER GAME ${position}/${#GAME_IDS[@]}: ${game_id} ====="
  "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py \
    --capture-side-report "$CAPTURE_REPORT" \
    --partition heldout \
    --corpus-db-root /corpus-db \
    --game-id "$game_id" \
    --output "$part"
done

echo
echo "===== PUBLIC CAPTURE O-LAYER HELDOUT: MERGE ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_merge.py \
  --parts-dir "$PARTS_DIR" \
  --output "$OUTPUT"

echo
echo "===== PUBLIC CAPTURE O-LAYER HELDOUT: FROZEN GATE ====="
"${lab[@]}" python - "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("partition") != "heldout":
    raise SystemExit("merged report is not heldout")
counts = payload["summary"]["counts"]
adjacent = int(counts.get("adjacent_rows", 0))
exact = int(counts.get("identity_anchored_split_exact", 0))
mismatch = int(counts.get("identity_anchored_split_mismatch", 0))
unresolved = int(counts.get("identity_anchored_split_unresolved", 0))

print(f"heldout_adjacent:              {adjacent}")
print(f"heldout_frozen_exact:          {exact}")
print(f"heldout_frozen_mismatch:       {mismatch}")
print(f"heldout_frozen_unresolved:     {unresolved}")

passed = (
    adjacent > 0
    and exact == adjacent
    and mismatch == 0
    and unresolved == 0
)
print(f"heldout_frozen_gate_passed:    {str(passed).lower()}")
if not passed:
    raise SystemExit(3)
PY

echo
echo "===== PUBLIC CAPTURE-SIDE HELDOUT: COMPLETE ====="
echo "capture_report: $CAPTURE_REPORT"
echo "parts_dir:      $PARTS_DIR"
echo "output:         $OUTPUT"
echo "corpus_db:      $(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
