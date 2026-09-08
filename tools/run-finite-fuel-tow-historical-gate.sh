#!/usr/bin/env bash
# Collect strict finite-fuel Tow historical evidence. Successful execution is not promotion.
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
gate_dir="logs/finite-fuel-tow-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
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
        stat = path.stat()
        print(path, "bytes=", stat.st_size, "mtime_ns=", stat.st_mtime_ns)
print("games=", games)
PY

run_stage tooling "${lab[@]}" python -u - <<'PY'
from pathlib import Path

path = Path("tools/diagnostics/tow_finite_fuel_population_audit.py")
compile(path.read_text(), str(path), "exec")
print("compiled=", path)
PY

run_stage pytest "${lab[@]}" python -m pytest

run_stage tow-discovery \
    "${lab[@]}" \
    python -u tools/diagnostics/tow_finite_fuel_population_audit.py --examples 80

run_stage summary "${lab[@]}" python -u - "$gate_dir" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
text = (root / "tow-discovery.log").read_text()
counters = {
    key: int(value)
    for key, value in re.findall(r"^([a-z_]+)=\s*(\d+)\s*$", text, re.M)
}
assert counters, "Tow discovery summary missing"
assert counters.get("missing_archive") == 0, "Historical archive missing"
assert counters.get("finite_fuel_games", 0) > 0, "No finite-fuel games entered the discovery"
for key in (
    "finite_fuel_games",
    "observed_route_targets",
    "lock_nonfuel_proven",
    "target_visible_to_tower_owner",
    "fuel_model_ready",
    "true_partial_route",
    "reachable_route",
    "geometry_exact",
    "geometry_differs",
    "snapshot_nominal_only",
    "snapshot_projected_only",
    "phase_nominal_only_possible",
    "phase_projected_only_possible",
    "phase_both_possible",
    "phase_neither_possible",
):
    print(f"{key}= {counters.get(key, 0)}")
print("Evidence collected only. finite-fuel Tow remains OPEN.")
print("Review discovery examples and run targeted external/transfer confounder audits before promotion.")
print("This runner does not rebuild L1/L2 and does not change planets-intel.")
PY

test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"

printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
