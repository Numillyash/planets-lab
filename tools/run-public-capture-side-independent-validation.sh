#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SHORT_MANIFEST="${SHORT_MANIFEST:-validation/corpus/manifests/public-short-expansion-selected.jsonl}"
SHORT_INDEX="${SHORT_INDEX:-validation/corpus/index/public-short-expansion-games.jsonl}"
BASELINE_MANIFEST="${BASELINE_MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
CAPTURE_REPORT="${CAPTURE_REPORT:-artifacts/public-capture-side/independent-short32-capture-side.json}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/independent-short32-postheldout-validation.json}"
GATE_REPORT="${GATE_REPORT:-artifacts/public-capture-side/independent-short32-postheldout-gate.json}"
PARTS_DIR="${PARTS_DIR:-artifacts/public-capture-side/o-layer-independent-short32-parts}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"
PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
EXPECTED_CURRENT="${EXPECTED_CURRENT:-generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb}"
FROZEN_CANDIDATE_COMMIT="${FROZEN_CANDIDATE_COMMIT:-592607b07efa0f857521da05fe0651127ed8be2d}"
export PLANETS_CORPUS_DB_ROOT

for required in   "$SHORT_MANIFEST"   "$SHORT_INDEX"   "$BASELINE_MANIFEST"   "$PLANETS_CORPUS_DB_ROOT/CURRENT"
do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

actual_current="$(tr -d '\r\n' < "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
if [[ "$actual_current" != "$EXPECTED_CURRENT" ]]; then
  echo "ERROR: independent validation requires the frozen public68 CURRENT." >&2
  echo "expected: $EXPECTED_CURRENT" >&2
  echo "actual:   $actual_current" >&2
  exit 67
fi

echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
echo "docker:       ready"
echo "corpus_db:    $actual_current"
echo "candidate:    $FROZEN_CANDIDATE_COMMIT"

compose=(
  docker compose
  -f compose.yaml
  -f compose.corpus-db.yaml
)

echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: BUILD LAB IMAGE ====="
"${compose[@]}" build lab

lab=(
  "${compose[@]}" run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: POPULATION BOUNDARY ====="
"${lab[@]}" python - "$SHORT_MANIFEST" "$SHORT_INDEX" "$BASELINE_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

short_manifest = Path(sys.argv[1])
short_index = Path(sys.argv[2])
baseline_manifest = Path(sys.argv[3])

def ids(path: Path) -> set[int]:
    result = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        result.add(int(row["game_id"]))
    return result

short_ids = ids(short_manifest)
index_ids = ids(short_index)
baseline_ids = ids(baseline_manifest)
overlap = short_ids & baseline_ids

print(f"short_manifest_games: {len(short_ids)}")
print(f"short_index_games:    {len(index_ids)}")
print(f"baseline_games:       {len(baseline_ids)}")
print(f"baseline_overlap:     {len(overlap)}")

if len(short_ids) != 32:
    raise SystemExit(f"expected 32 independent games, got {len(short_ids)}")
if index_ids != short_ids:
    missing = sorted(short_ids - index_ids)
    extra = sorted(index_ids - short_ids)
    raise SystemExit(
        f"short index mismatch: missing={missing} extra={extra}"
    )
if overlap:
    raise SystemExit(f"independent corpus overlaps public36: {sorted(overlap)}")
PY

echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: DB HARVEST ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py   --manifest "$SHORT_MANIFEST"   --index "$SHORT_INDEX"   --partition all   --corpus-db-root /corpus-db   --output "$CAPTURE_REPORT"

rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

mapfile -t GAME_IDS < <(
  "${lab[@]}" python - "$CAPTURE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("partition") != "all":
    raise SystemExit("independent capture report must have partition=all")
indexed = payload.get("indexed_game_ids", [])
scanned = payload.get("scanned_game_ids", [])
if indexed != scanned:
    raise SystemExit("independent harvest did not scan every indexed short32 game")
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
  echo "ERROR: independent short32 contains no ship-capture observations." >&2
  exit 65
fi

echo
echo "===== PUBLIC CAPTURE O-LAYER INDEPENDENT SHORT32: PROBE ====="
echo "game_passes:  ${#GAME_IDS[@]}"
position=0
for game_id in "${GAME_IDS[@]}"; do
  position=$((position + 1))
  part="$PARTS_DIR/game-${game_id}.json"
  echo
  echo "===== INDEPENDENT O-LAYER GAME ${position}/${#GAME_IDS[@]}: ${game_id} ====="
  "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py     --capture-side-report "$CAPTURE_REPORT"     --partition independent     --corpus-db-root /corpus-db     --game-id "$game_id"     --example-limit 10000     --output "$part"
done

echo
echo "===== PUBLIC CAPTURE O-LAYER INDEPENDENT SHORT32: MERGE ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_merge.py   --parts-dir "$PARTS_DIR"   --output "$OUTPUT"

echo
echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: POSTHELDOUT GATE ====="
"${lab[@]}" python - "$OUTPUT" "$GATE_REPORT" "$FROZEN_CANDIDATE_COMMIT" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
gate_path = Path(sys.argv[2])
candidate_commit = sys.argv[3]
payload = json.loads(output.read_text(encoding="utf-8"))
if payload.get("partition") != "independent":
    raise SystemExit("merged report is not independent validation")
counts = payload["summary"]["counts"]

adjacent = int(counts.get("adjacent_rows", 0))
rows = int(counts.get("postheldout_candidate_rows", 0))
exact = int(counts.get("postheldout_candidate_exact", 0))
mismatch = int(counts.get("postheldout_candidate_mismatch", 0))
unresolved = int(counts.get("postheldout_candidate_unresolved", 0))

branches = {
    "reachable_sticky": int(
        counts.get("postheldout_branch:reachable_sticky", 0)
    ),
    "nonreachable_neutral_fresh_fc": int(
        counts.get("postheldout_branch:nonreachable_neutral_fresh_fc", 0)
    ),
    "second_occurrence_reversal": int(
        counts.get("postheldout_branch:second_occurrence_reversal", 0)
    ),
    "reachable_numeric_opponent_override": int(
        counts.get(
            "postheldout_branch:reachable_numeric_opponent_override",
            0,
        )
    ),
}
branch_coverage_complete = all(value > 0 for value in branches.values())
candidate_gate_passed = (
    adjacent > 0
    and rows == adjacent
    and exact == rows
    and mismatch == 0
    and unresolved == 0
)
promotion_ready = candidate_gate_passed and branch_coverage_complete

if mismatch > 0:
    status = "FAILED_MISMATCH"
elif rows != adjacent or unresolved > 0:
    status = "INCOMPLETE_UNRESOLVED"
elif candidate_gate_passed and branch_coverage_complete:
    status = "PASS_FULL_BRANCH_COVERAGE"
elif candidate_gate_passed:
    status = "PASS_PARTIAL_BRANCH_COVERAGE"
else:
    status = "INSUFFICIENT_EVIDENCE"

report = {
    "schema": "planets-lab.combat-public-capture-side-independent-gate.v1",
    "evidence_status": "INDEPENDENT_VALIDATION",
    "frozen_candidate_commit": candidate_commit,
    "source_report": str(output),
    "adjacent_rows": adjacent,
    "candidate_rows": rows,
    "exact": exact,
    "mismatch": mismatch,
    "unresolved": unresolved,
    "branch_counts": branches,
    "branch_coverage_complete": branch_coverage_complete,
    "candidate_gate_passed": candidate_gate_passed,
    "promotion_ready": promotion_ready,
    "status": status,
}
gate_path.parent.mkdir(parents=True, exist_ok=True)
gate_path.write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

print(f"independent_adjacent:          {adjacent}")
print(f"candidate_rows:                {rows}")
print(f"candidate_exact:               {exact}")
print(f"candidate_mismatch:            {mismatch}")
print(f"candidate_unresolved:          {unresolved}")
for name, value in branches.items():
    print(f"branch_{name}: {value}")
print(f"branch_coverage_complete:      {str(branch_coverage_complete).lower()}")
print(f"candidate_gate_passed:         {str(candidate_gate_passed).lower()}")
print(f"promotion_ready:               {str(promotion_ready).lower()}")
print(f"independent_validation_status: {status}")
print(f"gate_report:                   {gate_path}")

if mismatch > 0:
    raise SystemExit(3)
if rows != adjacent or unresolved > 0:
    raise SystemExit(4)
PY

echo
echo "===== PUBLIC CAPTURE-SIDE INDEPENDENT SHORT32: COMPLETE ====="
echo "capture_report: $CAPTURE_REPORT"
echo "parts_dir:      $PARTS_DIR"
echo "output:         $OUTPUT"
echo "gate_report:    $GATE_REPORT"
echo "corpus_db:      $actual_current"
