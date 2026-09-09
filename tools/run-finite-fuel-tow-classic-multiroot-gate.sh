#!/usr/bin/env bash
# Consume a completed classic-storm reclassification gate and test the exact
# nine-row finite-fuel Tow remainder against bounded classic multi-root storms.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-classic-reclassification-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
reclassification_log="$source_dir/classic-storm-reclassification.log"

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

if ! test -f "$reclassification_log"; then
    echo "Missing reclassification log: $reclassification_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-classic-multiroot-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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

run_stage inputs "${lab[@]}" python -u - "$reclassification_log" <<'PY'
from pathlib import Path
import re
import sys

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for key, expected in (
    ("clean_residual_input", 53),
    ("classic_storm_attributed", 44),
    ("post_classic_storm_residual", 9),
    ("mode_false_games", 3),
    ("mode_not_false_games", 0),
):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing {key}"
    value = int(match.group(1))
    assert value == expected, f"unexpected {key}: {value} != {expected}"
for game_id in (360690, 511506, 620694):
    archive = RAW_DIR / f"game-{game_id}.zip"
    cache = PREPARED_DIR / f"game-{game_id}.pickle"
    assert archive.is_file(), f"missing archive: {archive}"
    assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"
print("reclassification_log=", path)
print("runtime_checkpoint=53 clean / 44 classic-storm / 9 remaining")
print("target_games=3 prepared_caches=3")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_classic_multiroot_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage classic-multiroot \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_classic_multiroot_audit.py \
        --reclassification-log "$reclassification_log" \
        --examples 100

run_stage summary "${lab[@]}" python -u - "$gate_dir/classic-multiroot.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing summary counter: {key}"
    return int(match.group(1))

keys = (
    "post_classic_storm_input",
    "cases",
    "rows_with_any_multi_root_exact_lead",
    "no_multi_root_exact_lead",
    "before_static_subset_exact_rows",
    "after_static_subset_exact_rows",
    "before_sorted_sequential_exact_rows",
    "after_sorted_sequential_exact_rows",
    "before_any_permutation_subset_exact_rows",
    "after_any_permutation_subset_exact_rows",
    "before_storm_conflict",
    "before_storm_invalid",
    "after_storm_conflict",
    "after_storm_invalid",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("post_classic_storm_input") == 9
assert counter("cases") == 9
assert counter("rows_with_any_multi_root_exact_lead") + counter("no_multi_root_exact_lead") == 9
assert counter("before_storm_conflict") == 0
assert counter("before_storm_invalid") == 0
assert counter("after_storm_conflict") == 0
assert counter("after_storm_invalid") == 0
print("Multi-root exactness is a bounded storm-order lead only; no automatic reclassification.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
