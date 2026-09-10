#!/usr/bin/env bash
# Resolve the three non-negative passenger-Chunnel leads in the exact nine-row
# post-classic finite-fuel Tow residual without rebuilding corpus preparation.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-passenger-chunnel-context-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/passenger-chunnel-context.log"

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
    echo "Missing completed passenger-Chunnel context log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-passenger-chunnel-resolution-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
    ("structural_origin_chunnel_lead", 1),
    ("same_destination_observed_chunnel_only_lead", 1),
    ("ability_catalog_changed_unresolved_lead", 1),
    ("no_chunnel_lead", 6),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

for game_id in (360690, 511506, 620694):
    archive = RAW_DIR / f"game-{game_id}.zip"
    cache = PREPARED_DIR / f"game-{game_id}.pickle"
    assert archive.is_file(), f"missing archive: {archive}"
    assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("passenger_log=", path)
print("runtime_checkpoint=9 rows / 6 no-Chunnel / 3 bounded Chunnel-resolution targets")
print("target_games=3 prepared_caches=3")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_passenger_chunnel_resolution_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage passenger-chunnel-resolution \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_passenger_chunnel_resolution_audit.py \
        --passenger-log "$source_log" \
        --examples 100

run_stage summary "${lab[@]}" python -u - "$gate_dir/passenger-chunnel-resolution.log" <<'PY'
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
    "resolution_target_rows",
    "background_no_chunnel_rows",
    "geometry_warpwell_rows",
    "geometry_warpwell_ambiguous_rows",
    "stable_observed_chunnel_warpwell_route_rows",
    "changed_catalog_rows",
    "exact_turn_catalog_resolved_rows",
    "exact_turn_catalog_missing_rows",
    "exact_turn_catalog_conflict_rows",
    "exact_turn_observed_chunnel_warpwell_route_rows",
    "rows_with_tow_pair_structural_role",
    "rows_with_tow_pair_numeric_fc_structural_role",
    "refined_observed_chunnel_route_warpwell_exact",
    "refined_tow_pair_numeric_fc_structural_chunnel",
    "refined_tow_pair_structural_chunnel",
    "refined_exact_turn_catalog_no_chunnel_lead",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("post_classic_storm_input") == 9
assert counter("cases") == 9
assert counter("resolution_target_rows") == 3
assert counter("background_no_chunnel_rows") == 6
assert (
    counter("exact_turn_catalog_resolved_rows")
    + counter("exact_turn_catalog_missing_rows")
    + counter("exact_turn_catalog_conflict_rows")
) == counter("changed_catalog_rows")
print("This is a bounded context-resolution gate; proximity alone never proves Chunnel.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
