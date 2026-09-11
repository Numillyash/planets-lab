#!/usr/bin/env bash
# Reconcile the cleaned T41 finite-fuel Tow row against documented Nu movement
# mass, Alchemy ordering and insufficient-fuel proration semantics.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-same-line-context-resolution-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/same-line-context-resolution.log"

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
    echo "Missing completed context-resolution log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-documented-reconcile-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for key, expected in (
    ("cases", 3),
    ("bounded_web_damage_context_rows", 2),
    ("alchemy_rows", 1),
    ("alchemy_exact_cargo_signature_rows", 1),
    ("alchemy_adjusted_envelope_possible_rows", 1),
    ("alchemy_adjusted_snapshot_exact_rows", 1),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

print("context_resolution_log=", path)
print("runtime_checkpoint=3 rows / 2 web confounders / exact T41 Alchemy-adjusted snapshot")
print("documented_sources=https://help.planets.nu/fuel-details ; https://help.planets.nu/host-order")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_documented_reconciliation_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage documented-reconciliation \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_documented_reconciliation_audit.py \
        --context-resolution-log "$source_log"

run_stage summary "${lab[@]}" python -u - "$gate_dir/documented-reconciliation.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing result counter {key}"
    return int(matches[-1])

expected = {
    "cases": 1,
    "pre_alchemy_combined_exact": 0,
    "post_alchemy_combined_exact": 1,
    "post_alchemy_tower_only_exact": 0,
    "alchemy_mass_basis_discriminator": 1,
    "combined_mass_discriminator": 1,
}
for key, wanted in expected.items():
    value = counter(key)
    print(f"{key}= {value}")
    assert value == wanted, f"unexpected {key}: {value} != {wanted}"

print("T41 is a historical discriminator for documented post-Alchemy combined-mass proportional Tow fuel movement.")
print("Web-hit rows remain excluded from this fuel discriminator; unrelated Tow interactions remain separately scoped.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
