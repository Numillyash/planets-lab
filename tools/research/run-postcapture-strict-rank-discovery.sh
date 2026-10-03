#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
O_LAYER="$MAIN_ROOT/artifacts/public-capture-side/discovery-o-layer-probe.json"
AFSIM="$RESEARCH_ROOT/artifacts/external-sources/afsim-r1/discovery-afsim-r1-analysis.json"
OUTPUT="$RESEARCH_ROOT/artifacts/external-sources/afsim-r1/discovery-strict-rank-analysis.json"

echo "===== POST-CAPTURE STRICT-RANK DISCOVERY GATE ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "o_layer:       $O_LAYER"
echo "afsim:         $AFSIM"
echo "output:        $OUTPUT"
echo

research_branch="$(git -C "$RESEARCH_ROOT" branch --show-current)"
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
if [[ ! -s "$AFSIM" ]]; then
  echo "ERROR: AFSim discovery analysis missing: $AFSIM" >&2
  exit 66
fi

echo "main HEAD:     $main_head"
echo "research HEAD: $(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
echo

needs_refresh=1
if [[ -s "$O_LAYER" ]]; then
  if python3 - "$O_LAYER" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
rows = payload.get("observations")
if not isinstance(rows, list):
    raise SystemExit(1)

adjacent = []
for row in rows:
    if not isinstance(row, dict):
        continue
    a = row.get("capture_vcr_id")
    b = row.get("next_vcr_id")
    if (
        isinstance(a, int) and not isinstance(a, bool)
        and isinstance(b, int) and not isinstance(b, bool)
        and b == a + 1
    ):
        adjacent.append(row)

if not adjacent:
    raise SystemExit(1)

# Current strict-rank analysis needs the enriched active_dependency object.
if not all(isinstance(row.get("active_dependency"), dict) for row in adjacent):
    raise SystemExit(1)

# Also require rank keys to exist, even when their value is null.
required = {
    "factual_opponent_requester_rank",
    "factual_opponent_strict_rank",
}
if not all(required.issubset(row["active_dependency"]) for row in adjacent):
    raise SystemExit(1)

print(f"artifact current enough: adjacent={len(adjacent)}")
PY
  then
    needs_refresh=0
  fi
fi

if [[ "$needs_refresh" -eq 1 ]]; then
  echo "===== REFRESH CURRENT MAIN DISCOVERY O-LAYER ====="
  echo "Existing artifact is legacy/stale for rank analysis."
  echo "Rebuilding discovery-only O-layer with current canonical main."
  echo

  export PLANETS_CORPUS_DB_ROOT="$CORPUS_DB_ROOT"
  (
    cd "$MAIN_ROOT"
    bash tools/run-public-capture-o-layer-discovery.sh
  )
  echo
fi

echo "===== STRICT-RANK POST-ANALYSIS ====="
cd "$RESEARCH_ROOT"
python3 tools/research/analyze-postcapture-strict-rank-discovery.py   --o-layer "$O_LAYER"   --afsim-analysis "$AFSIM"   --output "$OUTPUT"

echo
echo "===== COMPLETE ====="
echo "main HEAD:     $main_head"
echo "research HEAD: $(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
echo "output:        $OUTPUT"
echo
echo "Held-out was not read."
