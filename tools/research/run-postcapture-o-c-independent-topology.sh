#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"

BASELINE_MANIFEST="$MAIN_ROOT/validation/corpus/manifests/public-validation-selected.jsonl"
SHORT_MANIFEST="$MAIN_ROOT/validation/corpus/manifests/public-short-expansion-selected.jsonl"
INPUT="$MAIN_ROOT/artifacts/public-capture-side/independent-short32-postheldout-validation.json"
OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/postcapture-occurrence/independent-short32-o-c-topology-gate.json"

FROZEN_CANDIDATE_COMMIT="7e590cd73690ebf544ff8b7d671747cb6e0ca047"
FROZEN_GATE_PROTOCOL_COMMIT="a5002f7df49c7db76b0d38cd86fb916ae29f3dcc"

echo "===== INDEPENDENT SHORT32 O/C TOPOLOGY GATE ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "input:         $INPUT"
echo "output:        $OUTPUT"
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

if ! git -C "$RESEARCH_ROOT" merge-base --is-ancestor   "$FROZEN_CANDIDATE_COMMIT" "$research_head"; then
  echo "ERROR: research HEAD does not contain frozen O/C candidate." >&2
  exit 3
fi
if ! git -C "$RESEARCH_ROOT" merge-base --is-ancestor   "$FROZEN_GATE_PROTOCOL_COMMIT" "$research_head"; then
  echo "ERROR: research HEAD does not contain frozen independent gate protocol." >&2
  exit 3
fi

for required in "$BASELINE_MANIFEST" "$SHORT_MANIFEST" "$INPUT"; do
  if [[ ! -s "$required" ]]; then
    echo "ERROR: required file missing or empty: $required" >&2
    exit 66
  fi
done

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "candidate:     $FROZEN_CANDIDATE_COMMIT"
echo "gate protocol: $FROZEN_GATE_PROTOCOL_COMMIT"
echo

echo "===== INDEPENDENT POPULATION BOUNDARY ====="
python3 - "$BASELINE_MANIFEST" "$SHORT_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

baseline = Path(sys.argv[1])
short = Path(sys.argv[2])

def ids(path: Path) -> set[int]:
    out = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        out.add(int(row["game_id"]))
    return out

baseline_ids = ids(baseline)
short_ids = ids(short)
overlap = baseline_ids & short_ids

print(f"public36 games: {len(baseline_ids)}")
print(f"short32 games:  {len(short_ids)}")
print(f"overlap:        {len(overlap)}")

if len(short_ids) != 32:
    raise SystemExit(f"expected short32=32 games, got {len(short_ids)}")
if overlap:
    raise SystemExit(f"independent short32 overlaps public36: {sorted(overlap)}")
PY
echo

cd "$RESEARCH_ROOT"

echo "===== O/C TOPOLOGY UNIT TESTS ====="
python3 -m pytest -q   tests/test_postcapture_o_c_topology.py   tests/test_postcapture_o_c_independent.py
echo

echo "===== INDEPENDENT TOPOLOGY EVALUATION ====="
python3 tools/research/analyze-postcapture-o-c-independent.py   --input "$INPUT"   --output "$OUTPUT"

echo
echo "===== COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "output:        $OUTPUT"
echo
echo "Evidence label: INDEPENDENT_O_C_TOPOLOGY_VALIDATION"
echo "No O/C class or selector was fitted from short32."
