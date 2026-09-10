#!/usr/bin/env bash
# Consume a completed classic multi-root gate, recover its exact nine-row source
# population, and inspect passenger Chunnel / special relocation context.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-classic-multiroot-gate-dir>" >&2
    exit 2
fi

multiroot_dir=${1%/}
multiroot_log="$multiroot_dir/classic-multiroot.log"
revisions="$multiroot_dir/revisions.txt"

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

if ! test -f "$multiroot_log" || ! test -f "$revisions"; then
    echo "Missing completed classic-multiroot gate files under: $multiroot_dir" >&2
    exit 2
fi

source_gate=$(sed -n 's/^source_gate=//p' "$revisions" | tail -n 1)
if test -z "$source_gate"; then
    echo "source_gate missing from $revisions" >&2
    exit 2
fi
reclassification_log="${source_gate%/}/classic-storm-reclassification.log"
if ! test -f "$reclassification_log"; then
    echo "Missing source reclassification log: $reclassification_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-passenger-chunnel-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir"
printf 'candidate=%s\nmultiroot_gate=%s\nreclassification_gate=%s\n' \
    "$gate_head" "$multiroot_dir" "$source_gate" | tee "$gate_dir/revisions.txt"
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

run_stage inputs "${lab[@]}" python -u - "$multiroot_log" "$reclassification_log" <<'PY'
from pathlib import Path
import re
import sys

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR

multiroot = Path(sys.argv[1])
reclassification = Path(sys.argv[2])
multiroot_text = multiroot.read_text(encoding="utf-8")
reclass_text = reclassification.read_text(encoding="utf-8")

for key, expected in (
    ("post_classic_storm_input", 9),
    ("cases", 9),
    ("rows_with_any_multi_root_exact_lead", 0),
    ("no_multi_root_exact_lead", 9),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", multiroot_text, re.M)
    assert matches, f"missing multi-root counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected multi-root {key}: {value} != {expected}"

for key, expected in (
    ("classic_storm_attributed", 44),
    ("post_classic_storm_residual", 9),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", reclass_text, re.M)
    assert matches, f"missing reclassification counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected reclassification {key}: {value} != {expected}"

for game_id in (360690, 511506, 620694):
    archive = RAW_DIR / f"game-{game_id}.zip"
    cache = PREPARED_DIR / f"game-{game_id}.pickle"
    assert archive.is_file(), f"missing archive: {archive}"
    assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("multiroot_log=", multiroot)
print("reclassification_log=", reclassification)
print("runtime_checkpoint=9 post-classic rows / 0 bounded multi-root exact leads")
print("target_games=3 prepared_caches=3")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_passenger_chunnel_context_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage passenger-chunnel-context \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_passenger_chunnel_context_audit.py \
        --reclassification-log "$reclassification_log" \
        --examples 100

run_stage summary "${lab[@]}" python -u - "$gate_dir/passenger-chunnel-context.log" <<'PY'
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
    "ability_catalog_changed_games",
    "rows_under_changed_ability_catalog",
    "rows_with_observed_chunnel_destination",
    "rows_with_observed_chunnel_origin_route",
    "rows_with_observed_chunnel_geometry_route",
    "rows_where_tow_pair_has_direct_chunnel_role",
    "rows_with_structural_origin_chunnel",
    "rows_with_numeric_fc_structural_origin_chunnel",
    "rows_with_same_origin_comovers",
    "observed_chunnel_route_exact_lead",
    "numeric_fc_structural_origin_chunnel_lead",
    "structural_origin_chunnel_lead",
    "same_origin_comovement_only_lead",
    "same_destination_observed_chunnel_only_lead",
    "ability_catalog_changed_unresolved_lead",
    "no_chunnel_lead",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("post_classic_storm_input") == 9
assert counter("cases") == 9
lead_total = sum(
    counter(key)
    for key in (
        "observed_chunnel_route_exact_lead",
        "numeric_fc_structural_origin_chunnel_lead",
        "structural_origin_chunnel_lead",
        "same_origin_comovement_only_lead",
        "same_destination_observed_chunnel_only_lead",
        "ability_catalog_changed_unresolved_lead",
        "no_chunnel_lead",
    )
)
assert lead_total == 9, f"lead accounting mismatch: {lead_total} != 9"
print("Changed ability catalogs are fail-closed: stable-intersection positives are retained, otherwise the row stays unresolved.")
print("Passenger Chunnel categories are evidence-scoped context leads; no hidden event is inferred from distance alone.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
