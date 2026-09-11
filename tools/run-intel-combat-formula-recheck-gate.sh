#!/usr/bin/env bash
# Recheck two planets-intel combat formulas against immutable cached loadall games.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

branch=$(git symbolic-ref --quiet --short HEAD)
test -n "$branch"
test -z "$(git status --porcelain)"

git fetch origin "$branch"
fetched_head=$(git rev-parse FETCH_HEAD)
checkout_head=$(git rev-parse HEAD)
if test "$checkout_head" != "$fetched_head"; then
    printf 'Checkout is not freshly fetched %s.\nHEAD=%s\nFETCH_HEAD=%s\nUpdate with --ff-only first.\n' \
        "$branch" "$checkout_head" "$fetched_head" >&2
    exit 2
fi

gate_head=$checkout_head
gate_dir="logs/intel-combat-formula-recheck-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir"
printf 'candidate=%s\nbranch=%s\n' "$gate_head" "$branch" | tee "$gate_dir/revisions.txt"
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

run_stage inputs "${lab[@]}" python -u - <<'PY'
from pathlib import Path
archives = sorted(Path("validation/corpus/cache/loadall").glob("game-*.zip"))
print("archives=", len(archives))
for path in archives:
    print("archive=", path.name)
assert archives, "no cached loadall archives found"
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path
path = Path("tools/diagnostics/intel_combat_formula_recheck.py")
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("compiled=", path)
PY

run_stage corpus-recheck \
    "${lab[@]}" \
    python -u tools/diagnostics/intel_combat_formula_recheck.py \
        --output "$gate_dir/report.json"

run_stage summary "${lab[@]}" python -u - "$gate_dir/report.json" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("archives=", report["archives"])
print("federation_counts=", report["federation_shield_recovery"]["counts"])
print("planet_beam_counts=", report["planet_native_beam_tech"]["counts"])
print("assertions=", report["assertions"])
assert report["all_assertions_pass"] is True
print("RESULT: current planets-intel Federation and native-planet-beam formulas are historically discriminated by the cached corpus.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
