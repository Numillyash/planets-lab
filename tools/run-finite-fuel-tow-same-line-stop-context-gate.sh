#!/usr/bin/env bash
# Consume the completed same-line Tow fuel reconciliation gate and inspect the
# three negative rows for visible mine/web, damage/supply and hull-special context.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# != 1 )); then
    echo "Usage: $0 <completed-same-line-reconciliation-gate-dir>" >&2
    exit 2
fi

source_dir=${1%/}
source_log="$source_dir/same-line-reconciliation.log"

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
    echo "Missing completed same-line reconciliation log: $source_log" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-same-line-stop-context-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
normalized_log="$gate_dir/same-line-reconciliation-normalized.log"

run_stage inputs "${lab[@]}" python -u - "$source_log" <<'PY'
from pathlib import Path
import re
import sys

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for key, expected in (
    ("same_line_input", 3),
    ("cases", 3),
    ("combined_only", 0),
    ("both_models", 0),
    ("tower_only_only", 0),
    ("neither_model", 3),
):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    assert matches, f"missing source counter {key}"
    value = int(matches[-1])
    assert value == expected, f"unexpected source {key}: {value} != {expected}"

archive = RAW_DIR / "game-360690.zip"
cache = PREPARED_DIR / "game-360690.pickle"
assert archive.is_file(), f"missing archive: {archive}"
assert cache.is_file(), f"missing prepared cache: {cache}; no rebuild attempted"

print("same_line_log=", path)
print("runtime_checkpoint=3 same-line rows / 3 neither proportional fuel model")
print("target_game=360690 prepared_cache=1")
PY

# The producer historically emitted the three case dictionaries inline before
# SUMMARY rather than under a CASES marker. Normalize that log contract locally
# without modifying or replacing the immutable source gate.
run_stage normalize-input "${lab[@]}" python -u - "$source_log" "$normalized_log" <<'PY'
import ast
from pathlib import Path
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

if "===== CASES =====" in text:
    destination.write_text(text, encoding="utf-8")
    print("source_cases_marker=present")
    print("normalized_log=", destination)
    raise SystemExit(0)

prefix = text.split("===== SUMMARY =====", 1)[0]
cases = []
for raw_line in prefix.splitlines():
    line = raw_line.strip()
    if not line.startswith("{"):
        continue
    value = ast.literal_eval(line)
    if not isinstance(value, dict):
        continue
    if {"game", "turn", "tower_ship", "target_ship", "envelope_class"}.issubset(value):
        cases.append(value)

assert len(cases) == 3, f"expected 3 inline same-line cases, got {len(cases)}"
assert {int(item["game"]) for item in cases} == {360690}
assert {int(item["turn"]) for item in cases} == {41, 44, 185}
assert all(item.get("envelope_class") == "neither_model" for item in cases)

normalized = text.rstrip() + "\n\n===== CASES =====\n"
normalized += "\n".join(repr(item) for item in cases)
normalized += "\n===== INTERPRETATION =====\n"
destination.write_text(normalized, encoding="utf-8")
print("source_cases_marker=absent")
print("recovered_inline_cases=", len(cases))
print("recovered_turns=", tuple(sorted(int(item["turn"]) for item in cases)))
print("normalized_log=", destination)
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/tow_finite_fuel_same_line_stop_context_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage same-line-stop-context \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_same_line_stop_context_audit.py \
        --same-line-log "$normalized_log"

run_stage summary "${lab[@]}" python -u - "$gate_dir/same-line-stop-context.log" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")

def counter(key):
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    return int(matches[-1]) if matches else 0

for key in (
    "cases",
    "strong_mine_classifier_rows",
    "tower_normal_damage_candidate_rows",
    "tower_web_damage_candidate_rows",
    "target_damage_candidate_rows",
    "visible_normal_crossing_rows",
    "visible_web_crossing_rows",
    "observed_inside_visible_web_rows",
    "research_scaled_floor_exact_rows",
):
    print(f"{key}= {counter(key)}")

lead_lines = re.findall(r"^(lead:[a-z0-9_]+)=\s*(\d+)\s*$", text, re.M)
for key, value in lead_lines:
    print(f"{key}= {value}")
assert counter("cases") == 3
assert sum(int(value) for _, value in lead_lines) == 3
print("Mine/web and damage results are bounded context leads unless the existing strong classifier fires.")
print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
