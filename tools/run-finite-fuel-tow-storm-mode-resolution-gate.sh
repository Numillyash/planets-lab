#!/usr/bin/env bash
# Resolve nuionstorms for the finite-fuel Tow residual games via proxy-only public loadinfo.
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
gate_dir="logs/finite-fuel-tow-storm-mode-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
print("external_log=", external)
print("runtime_checkpoint=56 classified / 53 clean residuals")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_storm_mode_resolution_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage storm-mode-resolution \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_storm_mode_resolution_audit.py \
        --external-log "$external_log"

run_stage summary "${lab[@]}" python -u - "$gate_dir/storm-mode-resolution.log" <<'PY'
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
    "unique_games",
    "loadinfo_attempts",
    "loadinfo_success",
    "loadinfo_error",
    "mode_true_games",
    "mode_false_games",
    "mode_unknown_games",
    "mode_missing_games",
    "mode_unparsed_games",
    "mode_conflict_games",
    "proxy_client_error",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("clean_residual_input") == 53
assert counter("unique_games") == 3
assert counter("loadinfo_attempts") == 3
assert counter("loadinfo_success") == 3, "public loadinfo did not resolve for all Tow residual games"
assert counter("loadinfo_error") == 0
assert counter("proxy_client_error") == 0
assert counter("mode_true_games") + counter("mode_false_games") + counter("mode_unknown_games") == 3
print("Mode resolution only. No Host-rule promotion.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
