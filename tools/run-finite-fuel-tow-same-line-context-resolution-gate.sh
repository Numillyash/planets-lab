#!/usr/bin/env bash
# Consume the completed same-line stop-context gate. Keep the two exact one-web-
# quantum rows as bounded external-context confounders and test the clean T41 row
# for a target Alchemy mass mutation before Tow.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-same-line-stop-context-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/same-line-stop-context.log"

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
    echo "Missing completed stop-context log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-same-line-context-resolution-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
    ("cases", 3),
    ("strong_mine_classifier_rows", 0),
    ("tower_web_damage_candidate_rows", 2),
    ("visible_web_crossing_rows", 2),
    ("observed_inside_visible_web_rows", 2),
    ("lead:damage_backed_visible_mine_context", 2),
    ("lead:no_visible_mine_or_damage_lead", 1),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

archive = RAW_DIR / "game-360690.zip"
cache = PREPARED_DIR / "game-360690.pickle"
assert archive.is_file(), f"missing archive: {archive}"
assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("stop_context_log=", path)
print("runtime_checkpoint=3 rows / 2 exact web-damage context / 1 clean T41")
print("target_game=360690 prepared_cache=1")
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_same_line_context_resolution_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage same-line-context-resolution \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_same_line_context_resolution_audit.py \
        --stop-context-log "$source_log"

run_stage summary "${lab[@]}" python -u - "$gate_dir/same-line-context-resolution.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    return int(matches[-1]) if matches else 0

keys = (
    "cases",
    "bounded_web_damage_context_rows",
    "unresolved_damage_context_rows",
    "alchemy_rows",
    "alchemy_exact_cargo_signature_rows",
    "alchemy_full_conversion_hypothesis_rows",
    "alchemy_adjusted_envelope_possible_rows",
    "alchemy_adjusted_snapshot_exact_rows",
)
for key in keys:
    print(f"{key}= {counter(key)}")

assert counter("cases") == 3
assert counter("bounded_web_damage_context_rows") == 2
assert counter("unresolved_damage_context_rows") == 0
assert counter("alchemy_rows") == 1
print("Two rows are bounded web-hit confounders; deterministic web-hit RNG/location is not reconstructed.")
print("T41 Alchemy mass adjustment remains a phase-order hypothesis until independently verified.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
