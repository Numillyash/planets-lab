#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CANONICAL_CORPUS_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
EXPECTED_CURRENT="${EXPECTED_CURRENT:-generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb}"
PUBLIC100_REL="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
PUBLIC100_SHA="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"
FROZEN_SELECTOR_IMPL_COMMIT="d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad"
FROZEN_PROTOCOL_COMMIT="16b5a10e6bda7ebd8e98e1cee3a8ca16508727de"

BASELINE_MANIFEST="$MAIN_ROOT/validation/corpus/manifests/public-short-expansion-with-public36.jsonl"
FRESH_MANIFEST="$MAIN_ROOT/validation/corpus/manifests/public-postindependent-validation-selected.jsonl"
FRESH_INDEX="$MAIN_ROOT/validation/corpus/index/public-postindependent-validation-games.jsonl"

OUT_DIR="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/fresh32-independent"
CAPTURE_REPORT="$OUT_DIR/fresh32-capture-side.json"
O_LAYER_REPORT="$OUT_DIR/fresh32-o-layer.json"
PARTS_DIR="$OUT_DIR/o-layer-parts"
VALIDATION_REPORT="$OUT_DIR/fresh32-o-c-forward-independent.json"

DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== FRESH32 PROSPECTIVE O/C-FORWARD VALIDATION ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_root:   $CANONICAL_CORPUS_ROOT"
echo

research_branch="$(git -C "$RESEARCH_ROOT" branch --show-current)"
research_head="$(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
main_branch="$(git -C "$MAIN_ROOT" branch --show-current)"
main_head="$(git -C "$MAIN_ROOT" rev-parse HEAD)"
main_origin="$(git -C "$MAIN_ROOT" rev-parse origin/main)"

if [[ "$research_branch" != "research/external-engine-analysis" ]]; then
  echo "ERROR: research checkout is on $research_branch" >&2
  exit 2
fi
if [[ "$main_branch" != "main" ]]; then
  echo "ERROR: canonical checkout is on $main_branch, expected main" >&2
  exit 2
fi
if [[ "$main_head" != "$main_origin" ]]; then
  echo "ERROR: canonical main checkout is not at origin/main" >&2
  echo "  HEAD:        $main_head" >&2
  echo "  origin/main: $main_origin" >&2
  exit 2
fi

for frozen in "$FROZEN_SELECTOR_IMPL_COMMIT" "$FROZEN_PROTOCOL_COMMIT"; do
  if ! git -C "$RESEARCH_ROOT" merge-base --is-ancestor "$frozen" "$research_head"; then
    echo "ERROR: research HEAD does not contain frozen commit: $frozen" >&2
    exit 3
  fi
done

for frozen_path in \
  tools/research/postcapture_o_c_forward_selector.py \
  tools/research/postcapture_pair_bounds.py \
  tools/research/probe-postcapture-o-c-forward-open.py; do
  if ! git -C "$RESEARCH_ROOT" diff --quiet \
    "$FROZEN_SELECTOR_IMPL_COMMIT" -- "$frozen_path"; then
    echo "ERROR: frozen selector implementation changed after freeze." >&2
    echo "path:   $frozen_path" >&2
    echo "frozen: $FROZEN_SELECTOR_IMPL_COMMIT" >&2
    exit 4
  fi
done

for required in "$BASELINE_MANIFEST" "$FRESH_MANIFEST" "$FRESH_INDEX" "$CANONICAL_CORPUS_ROOT/CURRENT"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

actual_current="$(tr -d '\r\n' < "$CANONICAL_CORPUS_ROOT/CURRENT")"
if [[ "$actual_current" != "$EXPECTED_CURRENT" ]]; then
  echo "ERROR: prospective validation requires canonical CURRENT to remain public68." >&2
  echo "expected: $EXPECTED_CURRENT" >&2
  echo "actual:   $actual_current" >&2
  exit 67
fi

if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi

echo "===== FRESH32 POPULATION BOUNDARY ====="
python3 - "$BASELINE_MANIFEST" "$FRESH_MANIFEST" "$FRESH_INDEX" <<'PY'
import json
import sys
from pathlib import Path

baseline_path, fresh_path, index_path = map(Path, sys.argv[1:])

def ids(path: Path) -> set[int]:
    result: set[int] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        game_id = row.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
            raise SystemExit(f"{path}:{line_no}: invalid game_id")
        if game_id in result:
            raise SystemExit(f"{path}:{line_no}: duplicate game_id={game_id}")
        result.add(game_id)
    return result

baseline = ids(baseline_path)
fresh = ids(fresh_path)
index = ids(index_path)
overlap = baseline & fresh

print(f"public68 games: {len(baseline)}")
print(f"fresh32 games:  {len(fresh)}")
print(f"index games:    {len(index)}")
print(f"overlap:        {len(overlap)}")

if len(baseline) != 68:
    raise SystemExit(f"expected public68=68, got {len(baseline)}")
if len(fresh) != 32:
    raise SystemExit(f"expected fresh32=32, got {len(fresh)}")
if index != fresh:
    raise SystemExit("fresh32 manifest/index game-id mismatch")
if overlap:
    raise SystemExit(f"fresh32 overlaps public68: {sorted(overlap)}")
PY
echo

public100_db="$CANONICAL_CORPUS_ROOT/$PUBLIC100_REL"
if [[ ! -f "$public100_db" ]]; then
  echo "ERROR: pinned public100 generation does not exist: $public100_db" >&2
  exit 68
fi
actual_public100_sha="$(sha256sum "$public100_db" | awk '{print $1}')"
if [[ "$actual_public100_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: pinned public100 SHA256 mismatch." >&2
  echo "expected: $PUBLIC100_SHA" >&2
  echo "actual:   $actual_public100_sha" >&2
  exit 68
fi

public100_name="$(basename "$public100_db")"
public100_rel="generations/$public100_name"
view_root="$CANONICAL_CORPUS_ROOT/validation-views/oc-forward-fresh32-$$"

cleanup() {
  rm -rf "$view_root"
}
trap cleanup EXIT

mkdir -p "$view_root/generations"
ln "$public100_db" "$view_root/generations/$public100_name"
printf '%s\n' "$public100_rel" > "$view_root/CURRENT"

export PLANETS_CORPUS_DB_ROOT="$view_root"

echo "research HEAD:  $research_head"
echo "main HEAD:      $main_head"
echo "canonical CURRENT: $actual_current"
echo "public100 DB:   $public100_db"
echo "public100 SHA:  $actual_public100_sha"
echo "validation view:$view_root"
echo

compose=(
  docker compose
  -f "$MAIN_ROOT/compose.yaml"
  -f "$MAIN_ROOT/compose.corpus-db.yaml"
)

echo "===== BUILD/REUSE CANONICAL MAIN LAB IMAGE ====="
(
  cd "$MAIN_ROOT"
  "${compose[@]}" build lab
)
echo

lab=(
  "${compose[@]}" run --rm -T
  -v "$RESEARCH_ROOT:/research"
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics:/research/tools/research
  lab
)

echo "===== VALIDATION DB BOUNDARY ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python - "$FRESH_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path
from planets_lab.corpus.corpus_db_runtime import connect_current_compact_read_only

manifest = Path(sys.argv[1])
fresh_ids = {
    int(json.loads(raw)["game_id"])
    for raw in manifest.read_text(encoding="utf-8").splitlines()
    if raw.strip()
}
connection, path = connect_current_compact_read_only(Path("/corpus-db"))
try:
    archive_count = int(connection.execute("SELECT count(*) FROM source_archives").fetchone()[0])
    db_ids = {
        int(row[0])
        for row in connection.execute("SELECT game_id FROM source_archives").fetchall()
    }
finally:
    connection.close()

print(f"database={path}")
print(f"source_archives={archive_count}")
print(f"fresh32_present={len(fresh_ids & db_ids)}")
if archive_count != 100:
    raise SystemExit(f"expected public100 source_archives=100, got {archive_count}")
if not fresh_ids <= db_ids:
    raise SystemExit(f"public100 missing fresh games: {sorted(fresh_ids - db_ids)}")
PY
)
echo

echo "===== FROZEN VALIDATOR UNIT TESTS ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q \
    /research/tests/test_postcapture_o_c_forward_selector.py \
    /research/tests/test_postcapture_o_c_forward_independent.py
)
echo

mkdir -p "$OUT_DIR"
rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

echo "===== FRESH32 CAPTURE HARVEST ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py \
    --manifest validation/corpus/manifests/public-postindependent-validation-selected.jsonl \
    --index validation/corpus/index/public-postindependent-validation-games.jsonl \
    --partition all \
    --corpus-db-root /corpus-db \
    --example-limit 10000 \
    --output /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-capture-side.json
)
echo

mapfile -t GAME_IDS < <(
  python3 - "$CAPTURE_REPORT" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("partition") != "all":
    raise SystemExit("fresh32 capture report must have partition=all")
indexed = set(map(int, payload.get("indexed_game_ids", [])))
scanned = set(map(int, payload.get("scanned_game_ids", [])))
if indexed != scanned:
    raise SystemExit("fresh32 capture harvest did not scan all indexed games")
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
  echo "===== FRESH32 INDEPENDENT O/C-FORWARD VALIDATION ====="
  echo "status: INSUFFICIENT_NO_COMPARABLE_ROWS"
  echo "No ship-capture observations were harvested from fresh32."
  exit 4
fi

echo "===== FRESH32 O-LAYER PROBE ====="
position=0
for game_id in "${GAME_IDS[@]}"; do
  position=$((position + 1))
  part="$PARTS_DIR/game-${game_id}.json"
  echo "===== O-LAYER GAME ${position}/${#GAME_IDS[@]}: ${game_id} ====="
  (
    cd "$MAIN_ROOT"
    "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py \
      --capture-side-report /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-capture-side.json \
      --partition independent \
      --corpus-db-root /corpus-db \
      --game-id "$game_id" \
      --example-limit 10000 \
      --output "/research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/o-layer-parts/game-${game_id}.json"
  )
done
echo

echo "===== FRESH32 O-LAYER MERGE ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_merge.py \
    --parts-dir /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/o-layer-parts \
    --output /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-o-layer.json
)
echo

echo "===== FRESH32 PROSPECTIVE SELECTOR GATE ====="
set +e
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python /research/tools/research/probe-postcapture-o-c-forward-independent.py \
    --main-root /workspace \
    --corpus-db-root /corpus-db \
    --capture-report /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-capture-side.json \
    --o-layer-report /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-o-layer.json \
    --output /research/artifacts/external-sources/postcapture-occurrence/fresh32-independent/fresh32-o-c-forward-independent.json
)
gate_rc=$?
set -e

after_current="$(tr -d '\r\n' < "$CANONICAL_CORPUS_ROOT/CURRENT")"
if [[ "$after_current" != "$actual_current" ]]; then
  echo "ERROR: validation changed canonical CURRENT." >&2
  echo "before: $actual_current" >&2
  echo "after:  $after_current" >&2
  exit 5
fi

echo
echo "===== COMPLETE ====="
echo "research HEAD:   $research_head"
echo "main HEAD:       $main_head"
echo "canonical CURRENT preserved: $after_current"
echo "capture report:  $CAPTURE_REPORT"
echo "O-layer report:  $O_LAYER_REPORT"
echo "validation:      $VALIDATION_REPORT"
echo
echo "Evidence: INDEPENDENT_VALIDATION"
echo "Frozen selector implementation was not modified."

exit "$gate_rc"
