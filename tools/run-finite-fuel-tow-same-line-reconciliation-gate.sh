#!/usr/bin/env bash
# Consume the completed Tow break/independent-movement gate and reconcile the
# exact three same-line rows against physical finite-fuel Tow phase envelopes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-break-independent-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/break-independent-movement.log"

test "$(git symbolic-ref --quiet --short HEAD)" = main
test -z "$(git status --porcelain)"

git fetch origin main
fetched_head=$(git rev-parse FETCH_HEAD)
checkout_head=$(git rev-parse HEAD)
if test "$checkout_head" != "$fetched_head"; then
    printf 'Checkout is not freshly fetched main.\nHEAD=%s\nFETCH_HEAD=%s\nUpdate with --ff-only first.\n' \
        "$checkout_head" "$fetched_head" >&2
    exit 2
fi

if ! test -f "$source_log"; then
    echo "Missing completed break-independent log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-same-line-reconcile-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir"
printf 'candidate=%s\nsource_gate=%s\n' "$gate_head" "$source_dir" | tee "$gate_dir/revisions.txt"
printf 'stage\tcommand_rc\ttee_rc\n' > "$gate_dir/status.tsv"
printf 'Logs: %s\n' "$gate_dir"

run_stage() {
    local stage=$1
    shift
    local -a stage_status
    printf '\nSTAGE %s\n' "$stage"
    set +e
    "$@" 2>&1 | tee "$gate_dir/$stage.log"
    stage_status=("${PIPESTATUS[@]}")
    set -e
    printf '%s\t%s\t%s\n' "$stage" "${stage_status[0]}" "${stage_status[1]}" >> "$gate_dir/status.tsv"
    if (( stage_status[0] != 0 || stage_status[1] != 0 )); then
        echo "Stopped at $stage; preserve $gate_dir" >&2
        exit 1
    fi
}

lab=(docker compose run --rm -T -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics lab)

run_stage inputs "${lab[@]}" python -u - "$source_log" <<'PY'
from pathlib import Path
import re
import sys

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for key, expected in (
    ("remaining_input", 7),
    ("cases", 7),
    ("same_line_rows", 3),
    ("off_route_rows", 4),
    ("neither_independent_exact", 7),
    ("nonfuel_lock_proven", 7),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

archive = RAW_DIR / "game-360690.zip"
cache = PREPARED_DIR / "game-360690.pickle"
assert archive.is_file(), f"missing archive: {archive}"
assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("break_log=", path)
print("runtime_checkpoint=7 rows / 3 same-line / 4 off-route / 7 neither-independent / 7 nonfuel-lock")
print("target_game=360690 prepared_cache=1")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_same_line_reconciliation_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage same-line-reconciliation \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_same_line_reconciliation_audit.py \
        --break-log "$source_log"

run_stage summary "${lab[@]}" python -u - "$gate_dir/same-line-reconciliation.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing summary counter: {key}"
    return int(matches[-1])

keys = (
    "same_line_input",
    "cases",
    "combined_only",
    "both_models",
    "tower_only_only",
    "neither_model",
    "snapshot_combined_exact",
    "snapshot_tower_only_exact",
    "tower_after_fuel_zero",
    "tower_after_reset_supporting_only",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("same_line_input") == 3
assert counter("cases") == 3
assert sum(counter(key) for key in (
    "combined_only", "both_models", "tower_only_only", "neither_model"
)) == 3
print("Reachable routes make projected-vs-nominal partial cost basis non-discriminating here.")
print("Snapshot/post fuel remains supporting evidence only; phase fuel is not assumed from snapshots.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
