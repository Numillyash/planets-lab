#!/usr/bin/env bash
# Reuse a completed finite-fuel Tow external-context gate and cluster only the clean residuals.
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
gate_dir="logs/finite-fuel-tow-residual-shape-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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

lab=(docker compose run --rm -T -e PYTHONPATH=/workspace/src lab)

run_stage inputs "${lab[@]}" python -u - "$external_log" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
assert path.is_file(), path
text = path.read_text(encoding="utf-8")
for key, expected in (
    ("residual_input", 56),
    ("classified_cases", 56),
    ("without_known_context_or_transfer_confounder", 53),
):
    match = re.search(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert match is not None, f"missing {key}"
    value = int(match.group(1))
    assert value == expected, f"unexpected {key}: {value} != {expected}"
print("external_log=", path)
print("runtime_checkpoint=56 classified / 53 clean residuals")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_residual_shape_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage residual-shape \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_residual_shape_audit.py \
        --external-log "$external_log" \
        --examples 100

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
