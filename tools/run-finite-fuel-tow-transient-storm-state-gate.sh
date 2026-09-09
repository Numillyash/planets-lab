#!/usr/bin/env bash
# Reuse a completed finite-fuel Tow external-context gate and test bounded
# transient ion-storm membership hypotheses plus ordinary movement controls.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-external-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
external_log="$source_dir/external-context.log"

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

if ! test -f "$external_log"; then
    echo "Missing external-context log: $external_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-transient-storm-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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

run_stage inputs "${lab[@]}" python -u - "$external_log" <<'PY'
from pathlib import Path
import re
import sys

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR

external = Path(sys.argv[1])
text = external.read_text(encoding="utf-8")
for key, expected in (
    ("residual_input", 56),
    ("classified_cases", 56),
    ("without_known_context_or_transfer_confounder", 53),
):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing {key}"
    value = int(match.group(1))
    assert value == expected, f"unexpected {key}: {value} != {expected}"

archives = sorted(RAW_DIR.glob("game-*.zip"))
assert archives, f"no archives under {RAW_DIR}"
for archive in archives:
    game_id = int(archive.stem.split("-")[-1])
    cache = PREPARED_DIR / f"game-{game_id}.pickle"
    assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"
print("external_log=", external)
print("runtime_checkpoint=56 classified / 53 clean residuals")
print("archives=", len(archives), "prepared_caches=", len(archives))
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_transient_storm_state_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage transient-storm-state \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_transient_storm_state_audit.py \
        --external-log "$external_log" \
        --examples 100 \
        --control-examples 40

run_stage summary "${lab[@]}" python -u - "$gate_dir/transient-storm-state.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing summary counter: {key}"
    return int(match.group(1))

for key in (
    "clean_residual_input",
    "tow_clean_cases",
    "tow_after_root_vector_rows",
    "tow_no_after_root_vector_match",
    "tow_rows_with_stable_root_pair",
    "tow_rows_with_stable_cluster_id_set",
    "tow_any_transient_origin_qualifies",
    "tow_any_transient_geometry_qualifies",
    "tow_any_transient_causal_point_qualifies",
    "ordinary_direct_classifier_rows",
    "ordinary_single_root_direct_controls",
    "control_after_raw_origin_qualifies",
    "control_any_transient_origin_qualifies",
    "control_any_transient_geometry_qualifies",
    "control_any_transient_causal_point_qualifies",
):
    print(f"{key}= {counter(key)}")

assert counter("clean_residual_input") == 53
assert counter("tow_clean_cases") == 53
assert counter("tow_after_root_vector_rows") == 44
assert counter("tow_no_after_root_vector_match") == 9
assert counter("control_after_raw_origin_qualifies") == counter("ordinary_single_root_direct_controls"), (
    "ordinary control harness did not reproduce the current classifier baseline"
)
print("Evidence mining only. transient candidates are not Host rules.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
