#!/usr/bin/env bash
# Re-run the strict Tow discovery with complete examples, then test whether ordinary
# warp-well capture explains the direct phase-neither population.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

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

gate_head=$checkout_head
gate_dir="logs/finite-fuel-tow-warpwell-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir"
printf 'candidate=%s\n' "$gate_head" | tee "$gate_dir/revisions.txt"
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

run_quiet_stage() {
    local stage=$1
    shift
    printf '\nSTAGE %s\n' "$stage"
    set +e
    "$@" >"$gate_dir/$stage.log" 2>&1
    local rc=$?
    set -e
    printf '%s\t%s\t0\n' "$stage" "$rc" >> "$gate_dir/status.tsv"
    if (( rc != 0 )); then
        tail -n 120 "$gate_dir/$stage.log" >&2 || true
        echo "Stopped at $stage; preserve $gate_dir" >&2
        exit 1
    fi
    grep -E '^(===== FINITE-FUEL TOW HISTORICAL DISCOVERY =====|game=.*stage=prepared_cache|game=.*cache_hit=|phase_neither_possible=|finite-fuel Tow remains OPEN)' \
        "$gate_dir/$stage.log" || true
}

lab=(docker compose run --rm -T -e PYTHONPATH=/workspace/src lab)

run_stage inputs "${lab[@]}" python -u - <<'PY'
from pathlib import Path
import duckdb

database = Path("validation/corpus/compiled/v1/corpus.duckdb")
assert database.is_file(), f"Missing historical database: {database}"
with duckdb.connect(str(database), read_only=True) as con:
    games = [int(row[0]) for row in con.execute("SELECT game_id FROM games ORDER BY game_id").fetchall()]
assert games, "Historical database has no games"
for game in games:
    for path in (
        Path(f"validation/corpus/cache/loadall/game-{game}.zip"),
        Path(f"validation/corpus/cache/prepared-v1/game-{game}.pickle"),
    ):
        assert path.is_file(), f"Missing local evidence/cache: {path}; no corpus rebuild attempted"
print("games=", games)
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path

for raw in (
    "tools/diagnostics/tow_finite_fuel_population_audit.py",
    "tools/diagnostics/tow_finite_fuel_warp_well_audit.py",
):
    path = Path(raw)
    compile(path.read_text(), str(path), "exec")
    print("compiled=", path)
PY

run_stage pytest "${lab[@]}" python -m pytest

# Complete example capture is intentionally written only to the gitignored log
# directory; do not flood the interactive terminal with thousands of evidence rows.
run_quiet_stage discovery-full \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_population_audit.py --examples 100000

run_stage warp-well-followup \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_warp_well_audit.py \
        --discovery-log "$gate_dir/discovery-full.log" \
        --examples 60

run_stage summary "${lab[@]}" python -u - "$gate_dir" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
discovery = (root / "discovery-full.log").read_text()
followup = (root / "warp-well-followup.log").read_text()

def counters(text):
    return {
        key: int(value)
        for key, value in re.findall(r"^([a-z_]+)=\s*(\d+)\s*$", text, re.M)
    }

base = counters(discovery)
post = counters(followup)
assert base.get("phase_neither_possible") is not None, "Base Tow phase-neither counter missing"
assert post.get("phase_neither_input") == base["phase_neither_possible"], (
    "Warp-well follow-up did not consume the complete phase-neither population"
)
assert post.get("cases") == post["phase_neither_input"], "Warp-well case accounting mismatch"
assert (
    post.get("phase_warpwell_both_possible", 0)
    + post.get("phase_warpwell_nominal_only_possible", 0)
    + post.get("phase_warpwell_projected_only_possible", 0)
    + post.get("phase_warpwell_neither_possible", 0)
    == post["cases"]
), "Warp-well phase buckets do not sum to the input population"

for key in (
    "phase_neither_input",
    "observed_is_eligible_planet",
    "geometry_warpwell_exact",
    "snapshot_warpwell_both_exact",
    "snapshot_warpwell_nominal_only",
    "snapshot_warpwell_projected_only",
    "phase_warpwell_both_possible",
    "phase_warpwell_nominal_only_possible",
    "phase_warpwell_projected_only_possible",
    "phase_warpwell_neither_possible",
    "phase_warpwell_ambiguous_cases",
):
    print(f"{key}= {post.get(key, 0)}")

print("Evidence collected only. finite-fuel Tow remains OPEN.")
print("If warp wells collapse the residual, inspect any post-warp-well cost-basis discriminators next.")
print("Otherwise take phase_warpwell_neither_possible into transfer/mine/storm/damage/Chunnel audit.")
print("This runner does not rebuild L1/L2 and does not change planets-intel.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
