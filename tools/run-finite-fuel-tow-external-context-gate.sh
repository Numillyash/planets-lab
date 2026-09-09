#!/usr/bin/env bash
# Reproduce the strict finite-fuel Tow discovery and warp-well follow-up, then
# classify the exact remaining population against already-modelled external context.
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
gate_dir="logs/finite-fuel-tow-external-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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

run_progress_stage() {
    local stage=$1
    shift
    local log_file="$gate_dir/$stage.log"
    local started now elapsed bytes lines rc pid latest

    printf '\nSTAGE %s\n' "$stage"
    started=$(date +%s)

    set +e
    "$@" >"$log_file" 2>&1 &
    pid=$!
    set -e

    while kill -0 "$pid" 2>/dev/null; do
        sleep 10
        if kill -0 "$pid" 2>/dev/null; then
            now=$(date +%s)
            elapsed=$((now - started))
            bytes=$(wc -c <"$log_file" | tr -d '[:space:]')
            lines=$(wc -l <"$log_file" | tr -d '[:space:]')
            printf 'PROGRESS stage=%s elapsed=%ss log_lines=%s log_bytes=%s\n' \
                "$stage" "$elapsed" "$lines" "$bytes"
            latest=$(grep -E "^(\\{'game':|game=|PROGRESS )" "$log_file" | tail -n 1 || true)
            if test -n "$latest"; then
                printf 'LATEST %s\n' "$latest"
            fi
        fi
    done

    set +e
    wait "$pid"
    rc=$?
    set -e

    printf '%s\t%s\t0\n' "$stage" "$rc" >> "$gate_dir/status.tsv"
    if (( rc != 0 )); then
        tail -n 120 "$log_file" >&2 || true
        echo "Stopped at $stage; preserve $gate_dir" >&2
        exit 1
    fi

    now=$(date +%s)
    elapsed=$((now - started))
    printf 'PROGRESS stage=%s completed elapsed=%ss\n' "$stage" "$elapsed"
    grep -E '^(===== |phase_neither_possible=|phase_warpwell_neither_possible=|residual_input=|classified_cases=|with_known_context_or_transfer_confounder=|without_known_context_or_transfer_confounder=|finite-fuel Tow remains OPEN)' \
        "$log_file" | tail -n 40 || true
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
    "tools/diagnostics/tow_finite_fuel_external_context_audit.py",
):
    path = Path(raw)
    compile(path.read_text(), str(path), "exec")
    print("compiled=", path)
PY

run_stage pytest "${lab[@]}" python -m pytest

# Complete example capture stays in gitignored logs. Long historical stages still
# emit a 10-second heartbeat so an interactive run never looks hung.
run_progress_stage discovery-full \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_population_audit.py --examples 100000

run_progress_stage warp-well-full \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_warp_well_audit.py \
        --discovery-log "$gate_dir/discovery-full.log" \
        --examples 100000

run_progress_stage external-context \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_external_context_audit.py \
        --discovery-log "$gate_dir/discovery-full.log" \
        --warpwell-log "$gate_dir/warp-well-full.log" \
        --examples 100000

run_stage summary "${lab[@]}" python -u - "$gate_dir" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
discovery = (root / "discovery-full.log").read_text()
warpwell = (root / "warp-well-full.log").read_text()
external = (root / "external-context.log").read_text()

def counters(text):
    return {
        key: int(value)
        for key, value in re.findall(r"^([a-z_:]+)=\s*(\d+)\s*$", text, re.M)
    }

base = counters(discovery)
post = counters(warpwell)
ctx = counters(external)
assert post.get("phase_neither_input") == base.get("phase_neither_possible"), (
    "Warp-well follow-up did not consume complete direct phase-neither population"
)
assert ctx.get("residual_input") == post.get("phase_warpwell_neither_possible"), (
    "External-context audit did not consume complete post-warp-well residual"
)
assert (
    ctx.get("classified_cases", 0) + ctx.get("identity_or_owner_state_mismatch", 0)
    == ctx["residual_input"]
), "External-context accounting mismatch"

for key in (
    "phase_neither_possible",
):
    print(f"direct_{key}= {base.get(key, 0)}")
for key in (
    "geometry_warpwell_exact",
    "phase_warpwell_both_possible",
    "phase_warpwell_nominal_only_possible",
    "phase_warpwell_projected_only_possible",
    "phase_warpwell_neither_possible",
):
    print(f"{key}= {post.get(key, 0)}")
for key in (
    "residual_input",
    "classified_cases",
    "identity_or_owner_state_mismatch",
    "with_known_context_or_transfer_confounder",
    "without_known_context_or_transfer_confounder",
    "damage_limited_exact",
    "observed_chunnel_target_route",
    "submitted_transfer_confounder",
    "storm_context_conflict",
    "storm_context_invalid",
):
    print(f"{key}= {ctx.get(key, 0)}")
for key, value in sorted(ctx.items()):
    if key.startswith("mine:") or key.startswith("storm:"):
        print(f"{key}= {value}")

print("Evidence collected only. finite-fuel Tow remains OPEN.")
print("Transfer flags are confounders, not proof of successful execution or Tow-phase mass/fuel.")
print("A negative targeted Chunnel result does not exclude passenger Chunnel relocation.")
print("This runner does not rebuild L1/L2 and does not change planets-intel.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
