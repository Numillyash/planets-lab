#!/usr/bin/env bash
# Reconcile the finite-fuel Tow clean residual after nuionstorms mode resolution.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 3 )); then
    echo "Usage: $0 <completed-external-gate-dir> <completed-classic-storm-gate-dir> <completed-storm-mode-gate-dir>" >&2
    exit 2
fi

external_dir=${1%/}
classic_dir=${2%/}
mode_dir=${3%/}
external_log="$external_dir/external-context.log"
classic_log="$classic_dir/classic-storm-membership.log"
mode_log="$mode_dir/storm-mode-resolution.log"

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

for path in "$external_log" "$classic_log" "$mode_log"; do
    if ! test -f "$path"; then
        echo "Missing required log: $path" >&2
        exit 2
    fi
done

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-classic-reclass-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir"
printf 'candidate=%s\nexternal_gate=%s\nclassic_gate=%s\nstorm_mode_gate=%s\n' \
    "$gate_head" "$external_dir" "$classic_dir" "$mode_dir" | tee "$gate_dir/revisions.txt"
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

run_stage inputs "${lab[@]}" python -u - "$external_log" "$classic_log" "$mode_log" <<'PY'
from pathlib import Path
import re
import sys

external, classic, mode = map(Path, sys.argv[1:])
checks = (
    (external, "without_known_context_or_transfer_confounder", 53),
    (classic, "tow_after_root_vector_rows", 44),
    (classic, "tow_no_after_root_vector_match", 9),
    (classic, "tow_any_classic_origin_qualifies", 44),
    (mode, "mode_false_games", 3),
    (mode, "mode_true_games", 0),
    (mode, "mode_unknown_games", 0),
    (mode, "proxy_client_error", 0),
)
for path, key, expected in checks:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing {key} in {path}"
    value = int(matches[-1])
    assert value == expected, f"unexpected {key} in {path}: {value} != {expected}"
print("external_log=", external)
print("classic_log=", classic)
print("mode_log=", mode)
print("runtime_checkpoint=53 clean / 44 exact-root+classic-origin / 3 classic-mode games")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_classic_storm_reclassification_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage classic-storm-reclassification \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_classic_storm_reclassification_audit.py \
        --external-log "$external_log" \
        --classic-log "$classic_log" \
        --mode-log "$mode_log" \
        --examples 100

run_stage summary "${lab[@]}" python -u - "$gate_dir/classic-storm-reclassification.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing summary counter: {key}"
    return int(match.group(1))

keys = (
    "clean_residual_input",
    "cases",
    "mode_false_games",
    "mode_not_false_games",
    "exact_root_vector_rows",
    "classic_origin_rows",
    "classic_storm_attributed",
    "post_classic_storm_residual",
    "remaining_due_mode",
    "remaining_no_exact_root_vector",
    "remaining_no_classic_origin_membership",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("clean_residual_input") == 53
assert counter("cases") == 53
assert counter("mode_false_games") == 3
assert counter("mode_not_false_games") == 0
assert counter("exact_root_vector_rows") == 44
assert counter("classic_origin_rows") == 44
assert counter("classic_storm_attributed") == 44
assert counter("post_classic_storm_residual") == 9
assert counter("remaining_due_mode") == 0
assert counter("remaining_no_exact_root_vector") == 9
assert counter("remaining_no_classic_origin_membership") == 0
print("44 rows are reclassified as attributable classic ion-storm confounders within the bounded evidence gate.")
print("The exact nine-row remainder is the next non-fuel context population.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
