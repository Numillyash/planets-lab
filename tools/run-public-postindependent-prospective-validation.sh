#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SHORT_MANIFEST="${SHORT_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-selected.jsonl}"
SHORT_INDEX="${SHORT_INDEX:-validation/corpus/index/public-postindependent-validation-games.jsonl}"
BASELINE_MANIFEST="${BASELINE_MANIFEST:-validation/corpus/manifests/public-short-expansion-with-public36.jsonl}"
CAPTURE_REPORT="${CAPTURE_REPORT:-artifacts/public-capture-side/prospective-public100-capture-side.json}"
OUTPUT="${OUTPUT:-artifacts/public-capture-side/prospective-public100-postindependent-validation.json}"
GATE_REPORT="${GATE_REPORT:-artifacts/public-capture-side/prospective-public100-postindependent-gate.json}"
PARTS_DIR="${PARTS_DIR:-artifacts/public-capture-side/o-layer-prospective-public100-parts}"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"
PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
PUBLIC100_REL="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
PUBLIC100_SHA="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"
EXPECTED_CURRENT="${EXPECTED_CURRENT:-generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb}"
export PLANETS_CORPUS_DB_ROOT

for required in "$SHORT_MANIFEST" "$SHORT_INDEX" "$BASELINE_MANIFEST"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

public100_host="$PLANETS_CORPUS_DB_ROOT/$PUBLIC100_REL"
if [[ ! -f "$public100_host" ]]; then
  echo "ERROR: public100 generation not found: $public100_host" >&2
  exit 67
fi
actual_sha="$(sha256sum "$public100_host" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA256 mismatch." >&2
  echo "expected: $PUBLIC100_SHA" >&2
  echo "actual:   $actual_sha" >&2
  exit 67
fi

actual_current="$(tr -d '\r\n' < "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
if [[ "$actual_current" != "$EXPECTED_CURRENT" ]]; then
  echo "ERROR: prospective validation expects canonical CURRENT to remain public68." >&2
  echo "expected: $EXPECTED_CURRENT" >&2
  echo "actual:   $actual_current" >&2
  exit 67
fi

echo "===== POST-INDEPENDENT PROSPECTIVE VALIDATION: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding." >&2
  exit 69
fi
echo "docker:       ready"
echo "CURRENT:      $actual_current"
echo "public100:    $PUBLIC100_REL"
echo "public100_sha:$actual_sha"

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

echo "===== BUILD LAB IMAGE ====="
"${compose[@]}" build lab

lab=(
  "${compose[@]}" run --rm -T
  -e PYTHONPATH=/workspace/src
  lab
)

echo "===== PROSPECTIVE POPULATION BOUNDARY ====="
"${lab[@]}" python - "$SHORT_MANIFEST" "$SHORT_INDEX" "$BASELINE_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

def ids(path: Path) -> set[int]:
    result = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            result.add(int(json.loads(raw)["game_id"]))
    return result

short_manifest = ids(Path(sys.argv[1]))
short_index = ids(Path(sys.argv[2]))
baseline = ids(Path(sys.argv[3]))
overlap = short_manifest & baseline

print(f"fresh_manifest_games: {len(short_manifest)}")
print(f"fresh_index_games:    {len(short_index)}")
print(f"public68_games:       {len(baseline)}")
print(f"public68_overlap:     {len(overlap)}")

if len(short_manifest) != 32:
    raise SystemExit(f"expected 32 fresh games, got {len(short_manifest)}")
if short_index != short_manifest:
    raise SystemExit(
        f"fresh index mismatch: missing={sorted(short_manifest-short_index)} "
        f"extra={sorted(short_index-short_manifest)}"
    )
if len(baseline) != 68:
    raise SystemExit(f"expected public68 baseline of 68 games, got {len(baseline)}")
if overlap:
    raise SystemExit(f"fresh population overlaps public68: {sorted(overlap)}")
PY

echo "===== FRESH32 CAPTURE HARVEST FROM EXPLICIT PUBLIC100 ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_side_harvest.py   --manifest "$SHORT_MANIFEST"   --index "$SHORT_INDEX"   --partition all   --corpus-db-root /corpus-db   --corpus-db-generation "$PUBLIC100_REL"   --output "$CAPTURE_REPORT"

rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

mapfile -t GAME_IDS < <(
  "${lab[@]}" python - "$CAPTURE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("partition") != "all":
    raise SystemExit("prospective capture report must have partition=all")
indexed = payload.get("indexed_game_ids", [])
scanned = payload.get("scanned_game_ids", [])
if indexed != scanned:
    raise SystemExit("prospective harvest did not scan every indexed fresh game")
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
  echo "ERROR: fresh32 contains no ship-capture observations." >&2
  exit 65
fi

echo
echo "===== PROSPECTIVE O-LAYER PROBE ====="
echo "game_passes: ${#GAME_IDS[@]}"
position=0
for game_id in "${GAME_IDS[@]}"; do
  position=$((position + 1))
  part="$PARTS_DIR/game-${game_id}.json"
  echo
  echo "===== PROSPECTIVE GAME ${position}/${#GAME_IDS[@]}: ${game_id} ====="
  "${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_probe.py     --capture-side-report "$CAPTURE_REPORT"     --partition prospective     --corpus-db-root /corpus-db     --corpus-db-generation "$PUBLIC100_REL"     --game-id "$game_id"     --example-limit 10000     --output "$part"
done

echo
echo "===== PROSPECTIVE O-LAYER MERGE ====="
"${lab[@]}" python tools/diagnostics/combat_public_capture_o_layer_merge.py   --parts-dir "$PARTS_DIR"   --output "$OUTPUT"

echo
echo "===== POST-INDEPENDENT PROSPECTIVE GATE ====="
set +e
"${lab[@]}" python - "$OUTPUT" "$GATE_REPORT" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
gate_path = Path(sys.argv[2])
payload = json.loads(output.read_text(encoding="utf-8"))
if payload.get("partition") != "prospective":
    raise SystemExit("merged report is not prospective validation")
counts = payload["summary"]["counts"]

adjacent = int(counts.get("adjacent_rows", 0))
rows = int(counts.get("postindependent_candidate_rows", 0))
exact = int(counts.get("postindependent_candidate_exact", 0))
mismatch = int(counts.get("postindependent_candidate_mismatch", 0))
unresolved = int(counts.get("postindependent_candidate_unresolved", 0))
kill_left = int(counts.get(
    "postindependent_branch:reachable_numeric_kill_left", 0
))
nonkill_left = int(counts.get(
    "postindependent_branch:reachable_numeric_nonkill_left", 0
))

candidate_exact_gate = (
    adjacent > 0
    and rows == adjacent
    and exact == rows
    and mismatch == 0
    and unresolved == 0
)
discriminator_coverage = kill_left > 0 and nonkill_left > 0
promotion_ready = candidate_exact_gate and discriminator_coverage

if mismatch > 0:
    status = "FAILED_MISMATCH"
    exit_code = 3
elif rows != adjacent or unresolved > 0:
    status = "INCOMPLETE_UNRESOLVED"
    exit_code = 4
elif not discriminator_coverage:
    status = "INSUFFICIENT_DISCRIMINATOR_COVERAGE"
    exit_code = 5
elif candidate_exact_gate:
    status = "PASS_PROSPECTIVE_VALIDATION"
    exit_code = 0
else:
    status = "INSUFFICIENT_EVIDENCE"
    exit_code = 6

report = {
    "schema": "planets-lab.combat-public-capture-side-prospective-gate.v1",
    "evidence_status": "PROSPECTIVE_VALIDATION",
    "frozen_candidate_commit": "46bcb08c2f0d3f0449b97921edb03ab6647f7d3b",
    "source_report": str(output),
    "adjacent_rows": adjacent,
    "candidate_rows": rows,
    "exact": exact,
    "mismatch": mismatch,
    "unresolved": unresolved,
    "fresh_numeric_kill_left": kill_left,
    "fresh_numeric_nonkill_left": nonkill_left,
    "candidate_exact_gate": candidate_exact_gate,
    "discriminator_coverage": discriminator_coverage,
    "promotion_ready": promotion_ready,
    "status": status,
}
gate_path.parent.mkdir(parents=True, exist_ok=True)
gate_path.write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

print(f"prospective_adjacent:          {adjacent}")
print(f"candidate_rows:                {rows}")
print(f"candidate_exact:               {exact}")
print(f"candidate_mismatch:            {mismatch}")
print(f"candidate_unresolved:          {unresolved}")
print(f"fresh_numeric_kill_left:       {kill_left}")
print(f"fresh_numeric_nonkill_left:    {nonkill_left}")
print(f"candidate_exact_gate:          {str(candidate_exact_gate).lower()}")
print(f"discriminator_coverage:        {str(discriminator_coverage).lower()}")
print(f"promotion_ready:               {str(promotion_ready).lower()}")
print(f"prospective_validation_status: {status}")
print(f"gate_report:                   {gate_path}")
raise SystemExit(exit_code)
PY
GATE_RC=$?
set -e

echo
echo "===== PROSPECTIVE VALIDATION COMPLETE ====="
echo "capture_report: $CAPTURE_REPORT"
echo "parts_dir:      $PARTS_DIR"
echo "output:         $OUTPUT"
echo "gate_report:    $GATE_REPORT"
echo "public100:      $PUBLIC100_REL"
echo "CURRENT:        $actual_current"
exit "$GATE_RC"
