#!/usr/bin/env bash
# Consume the completed passenger-Chunnel resolution gate and inspect the exact
# seven-row remainder for Tow-break / independent-navigation alternatives.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-passenger-chunnel-resolution-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/passenger-chunnel-resolution.log"

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
    echo "Missing completed passenger-Chunnel resolution log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-break-independent-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
    ("post_classic_storm_input", 9),
    ("cases", 9),
    ("refined_observed_chunnel_route_warpwell_exact", 2),
    ("refined_exact_turn_catalog_no_chunnel_lead", 1),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

for game_id in (360690, 620694):
    archive = RAW_DIR / f"game-{game_id}.zip"
    cache = PREPARED_DIR / f"game-{game_id}.pickle"
    assert archive.is_file(), f"missing archive: {archive}"
    assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("resolution_log=", path)
print("runtime_checkpoint=9 post-classic rows / 2 route-equivalent Chunnel exclusions / 7 remaining")
print("remaining_games=2 prepared_caches=2")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_break_independent_movement_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage break-independent-movement \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_break_independent_movement_audit.py \
        --resolution-log "$source_log" \
        --examples 100

run_stage summary "${lab[@]}" python -u - "$gate_dir/break-independent-movement.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing summary counter: {key}"
    return int(match.group(1))

keys = (
    "remaining_input",
    "cases",
    "same_line_rows",
    "off_route_rows",
    "both_independent_exact",
    "target_independent_exact_only",
    "tower_independent_exact_only",
    "neither_independent_exact",
    "tower_ordinary_exact",
    "target_ordinary_exact",
    "tower_strict_damage_exact",
    "target_strict_damage_exact",
    "snapshot_four_fingers_true",
    "snapshot_four_fingers_false",
    "snapshot_four_fingers_unknown",
    "nonfuel_lock_proven",
    "lock_depends_on_target_phase_fuel",
    "nonfuel_lock_unresolved_other",
    "target_exact_with_snapshot_four_fingers",
    "both_exact_with_snapshot_four_fingers",
    "same_line_neither_independent_exact",
    "off_route_neither_independent_exact",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("remaining_input") == 7
assert counter("cases") == 7
assert counter("same_line_rows") == 3
assert counter("off_route_rows") == 4
assert sum(counter(key) for key in (
    "both_independent_exact",
    "target_independent_exact_only",
    "tower_independent_exact_only",
    "neither_independent_exact",
)) == 7
assert sum(counter(key) for key in (
    "snapshot_four_fingers_true",
    "snapshot_four_fingers_false",
    "snapshot_four_fingers_unknown",
)) == 7
assert sum(counter(key) for key in (
    "nonfuel_lock_proven",
    "lock_depends_on_target_phase_fuel",
    "nonfuel_lock_unresolved_other",
)) == 7
print("Independent exactness is an alternative-explanation lead only; it does not prove that Tow broke.")
print("Snapshot fuel remains supporting evidence, not automatic Tow-phase fuel.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
