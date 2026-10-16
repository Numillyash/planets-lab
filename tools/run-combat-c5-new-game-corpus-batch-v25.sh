#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
DB_ROOT="$PLANETS_CORPUS_DB_ROOT"
BASELINE="validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl"
SELECTED="validation/corpus/manifests/public-c5-v25-selected.jsonl"
OUT="artifacts/combat/c5-new-game-corpus-batch-v25"
BUILD_ID="corpus-v2compact-c5-v25-public8-20261016"
DATABASE="$DB_ROOT/generations/$BUILD_ID.duckdb"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"

[[ -f "$BASELINE" && -x "$PYTHON" && -d "$DB_ROOT" ]] || {
 echo "ERROR: public100 baseline, site-state Python or shared corpus DB root absent" >&2
 exit 66
}
CURRENT_BEFORE=""
if [[ -f "$DB_ROOT/CURRENT" ]]; then CURRENT_BEFORE="$(cat "$DB_ROOT/CURRENT")"; fi
verify_current() {
 local after=""
 if [[ -f "$DB_ROOT/CURRENT" ]]; then after="$(cat "$DB_ROOT/CURRENT")"; fi
 if [[ "$after" != "$CURRENT_BEFORE" ]]; then
   echo "ERROR: corpus CURRENT changed during V25; investigate immediately" >&2
   return 1
 fi
}
trap verify_current EXIT
echo "===== C5 V25 NEW GAME CORPUS / 3 STUDIES / ONE RUN ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "baseline: $BASELINE (100 prior public games)"
echo "new generation: $DATABASE (never activates CURRENT)"

# Initial preflight before downloading any archives. Adjustable floor for
# machines with different free-space profiles; no automatic deletions.
MIN_FREE_GIB="${C5_V25_MIN_FREE_GIB:-12}"
[[ "$MIN_FREE_GIB" =~ ^[1-9][0-9]*$ ]] || { echo "invalid C5_V25_MIN_FREE_GIB" >&2; exit 64; }
FREE_BYTES="$(df -PB1 "$DB_ROOT" | awk 'NR==2 {print $4}')"
if (( FREE_BYTES < MIN_FREE_GIB * 1024 * 1024 * 1024 )); then
 echo "ERROR: insufficient free space for NEW 8-game acquisition+DuckDB; required >=${MIN_FREE_GIB}GiB" >&2
 exit 75
fi

# Separate namespace and full baseline exclusion: neither original manifests
# nor cached/immutable public100 database are modified.
export BASELINE_MANIFEST="$BASELINE"
export CANDIDATES_MANIFEST="validation/corpus/manifests/public-c5-v25-candidates.jsonl"
export SELECTED_MANIFEST="$SELECTED"
export COMBINED_MANIFEST="validation/corpus/manifests/public-c5-v25-with-public100.jsonl"
export REPORT="$OUT/selection-report.json"
export INDEX_OUTPUT="validation/corpus/index/public-c5-v25-games.jsonl"
export STATS_OUTPUT="validation/corpus/index/public-c5-v25-stats.json"
export REJECTED_FILE="validation/corpus/manifests/public-c5-v25-rejected.json"
export BACKFILL_REPORT="$OUT/backfill-report.json"
export EVIDENCE_DIR="$OUT/acquisition-evidence"
export MIN_TURN=55 MAX_TURN=140 MIN_SLOTS=8 MAX_SLOTS=16
export SELECT_COUNT=8 PROBE_LIMIT="${C5_V25_PROBE_LIMIT:-320}"
export REUSE_DISCOVERY=1 AUTO_BACKFILL=1 MAX_BACKFILL_ROUNDS=24

echo "===== C5 V25 ACQUIRE 8 DISJOINT FINISHED PUBLIC GAMES ====="
bash tools/run-public-validation-corpus-acquisition.sh

echo "===== C5 V25 VERIFY FULL PUBLIC100 EXCLUSION ====="
"$PYTHON" - "$BASELINE" "$SELECTED" <<'PY'
import json,sys
def ids(path):
    rows=[json.loads(x) for x in open(path,encoding="utf8") if x.strip()]
    keys=[x["game_id"] for x in rows]
    if len(set(keys))!=len(keys) or any(type(x) is not int or x<=0 for x in keys):
        raise SystemExit("invalid game manifest IDs")
    return set(keys)
baseline,selected=ids(sys.argv[1]),ids(sys.argv[2])
print(f"old={len(baseline)} fresh={len(selected)} overlap={len(baseline&selected)}")
if len(baseline)!=100 or len(selected)!=8 or baseline&selected:
    raise SystemExit("invalid new-game population; no import permitted")
PY

if [[ -f "$DATABASE" ]]; then
 echo "===== C5 V25 REUSE ALREADY PUBLISHED EXPLICIT GENERATION ====="
else
 echo "===== C5 V25 BUILD AND EXACT-PARITY VALIDATE NEW COMPACT GENERATION ====="
 docker compose -f compose.yaml -f compose.corpus-db.yaml \
  --profile corpus-db-writer run --rm -T corpus-db-importer \
  python -m planets_lab.corpus.corpus_db_compact_multi_cli build \
    --manifest "/workspace/$SELECTED" \
    --cache-dir /workspace/validation/corpus/cache/loadall \
    --expected-count 8 --state-name compact-c5-v25-public8-resume \
    --build-id "$BUILD_ID"
fi
[[ -f "$DATABASE" ]] || { echo "ERROR: V25 new generation publication missing" >&2; exit 2; }
verify_current

echo "===== C5 V25 THREE NEW-CORPUS FROZEN T-1/T ANALYSES ====="
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_new_game_corpus_batch_v25.py \
 --corpus-db "$DATABASE" \
 --selected-manifest "$SELECTED" --baseline-manifest "$BASELINE" \
 --output-dir "$OUT/published"
verify_current
echo "===== C5 V25 ALL THREE NEW-CORPUS REPORTS / MANIFEST COMPLETE ====="
