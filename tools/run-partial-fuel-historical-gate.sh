#!/usr/bin/env bash
# Collect historical evidence. Successful execution is not automatic promotion.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

test "$(git symbolic-ref --quiet --short HEAD)" = main
test -z "$(git status --porcelain)"
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" || {
    echo 'Checkout is not actual origin/main; update with --ff-only first.' >&2
    exit 2
}
gate_head=$(git rev-parse HEAD)
implementation=993e76046c3ffaa40acf4b0aa7286d5bd9573480
git merge-base --is-ancestor "$implementation" "$gate_head"
baseline=$(git rev-parse "${implementation}^")
gate_dir="logs/partial-fuel-$(date -u +%Y%m%dT%H%M%SZ)-${gate_head:0:8}-$$"
mkdir -p "$gate_dir/baseline"
printf 'candidate=%s\nbaseline=%s\n' "$gate_head" "$baseline" | tee "$gate_dir/revisions.txt"
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

# Isolate the pre-candidate source; never switch/reset the user's checkout.
git archive "$baseline" src | tar -x -C "$gate_dir/baseline"
run_stage source-diff git diff "$baseline" "$gate_head" -- src/planets_lab

# Keep every command on an explicit source path, even if the container image
# contains an older editable install. Both Intercept passes use the same audit.
lab=(docker compose run --rm -T -e PYTHONPATH=/workspace/src lab)
run_stage inputs "${lab[@]}" python -u - <<'PY'
from pathlib import Path
import duckdb
import planets_lab.sim.normal_movement as movement
print('candidate_planner=', movement.__file__)
assert Path(movement.__file__).resolve() == Path('/workspace/src/planets_lab/sim/normal_movement.py')
database = Path('validation/corpus/compiled/v1/corpus.duckdb')
assert database.is_file(), f'Missing historical database: {database}'
with duckdb.connect(str(database), read_only=True) as con:
    games = [int(row[0]) for row in con.execute('SELECT game_id FROM games ORDER BY game_id').fetchall()]
assert games, 'Historical database has no games'
for game in games:
    for path in (Path(f'validation/corpus/cache/loadall/game-{game}.zip'),
                 Path(f'validation/corpus/cache/prepared-v1/game-{game}.pickle')):
        assert path.is_file(), f'Missing local evidence/cache: {path}; no corpus rebuild attempted'
        stat = path.stat()
        print(path, 'bytes=', stat.st_size, 'mtime_ns=', stat.st_mtime_ns)
print('games=', games)
PY
run_stage pytest "${lab[@]}" python -m pytest
run_stage move-most-anchor "${lab[@]}" python -u tools/diagnostics/partial_move_fuel_cost_case_audit.py --game 360690 --turn 164 --ship 41 --fuel-scan-cap 5000
run_stage move-most-population "${lab[@]}" python -u tools/diagnostics/partial_move_fuel_cost_move_most_audit.py --examples 50
baseline_lab=(docker compose run --rm -T -e "PYTHONPATH=/workspace/$gate_dir/baseline/src" lab)
run_stage baseline-source "${baseline_lab[@]}" python -c 'import planets_lab.sim.normal_movement as m; print(m.__file__); assert "/baseline/src/" in m.__file__'
run_stage intercept-baseline "${baseline_lab[@]}" python -u tools/diagnostics/intercept_fuel_historical_differential_audit.py --examples 50
run_stage intercept-candidate "${lab[@]}" python -u tools/diagnostics/intercept_fuel_historical_differential_audit.py --examples 50
run_stage intercept-confounders "${lab[@]}" python -u tools/diagnostics/intercept_fuel_external_confounder_audit.py
run_stage comparison "${lab[@]}" python -u - "$gate_dir" <<'PY'
import ast
from pathlib import Path
import re
import sys
root = Path(sys.argv[1])
def counters(name):
    text = (root / name).read_text()
    return {key: int(value) for key, value in re.findall(r'^([a-z_]+)=\s*(\d+)\s*$', text, re.M)}
before = counters('intercept-baseline.log')
after = counters('intercept-candidate.log')
assert before and after, 'Missing differential summaries'
for key in sorted(before.keys() | after.keys()):
    print(f'{key}: {before.get(key)} -> {after.get(key)}')
population = counters('move-most-population.log')
expected_population = {
    'prefilter_true_partial_rows': 32371, 'true_partial_route': 15560,
    'prefilter_false_positive': 1495, 'same_integer_cost': 12633,
    'cost_basis_differs': 2927, 'projected_cost_endpoint_exact': 2811,
    'nominal_cost_endpoint_exact': 2812, 'discriminating_endpoint': 1,
    'discriminating_nominal_cost_support': 1,
    'discriminating_projected_cost_support': 0,
}
for key, expected in expected_population.items():
    print(f'Move Most {key}: expected={expected} observed={population.get(key)}')
    assert population.get(key) == expected, 'Move Most population changed; inspect corpus/evidence'
anchor_text = (root / 'move-most-anchor.log').read_text()
expected_scan = {
    'projected_exact_phase_fuel_ranges': (),
    'nominal_exact_phase_fuel_ranges': ((11, 11),),
    'projected_exact_post_fuel_ranges': (),
    'nominal_exact_post_fuel_ranges': ((0, 0),),
    'known_external_flags': (),
}
for key, expected in expected_scan.items():
    match = re.search(r'^' + key + r'=\s*(.+)$', anchor_text, re.M)
    assert match and ast.literal_eval(match.group(1)) == expected, f'Move Most anchor changed: {key}'
for line in (root / 'intercept-candidate.log').read_text().splitlines():
    if not line.startswith("{'game':"):
        continue
    case = ast.literal_eval(line)
    if (case.get('game'), case.get('turn'), case.get('ship')) == (620694, 73, 278):
        print('INTERCEPT ANCHOR:', case)
        break
else:
    raise SystemExit('Anchor absent from examples; inspect population before promotion')
assert case.get('fuel_required_candidate') == 72, 'Unexpected anchor cost'
assert case.get('fuel_limited_candidate') is True and case.get('fuel_exact') is True
assert case.get('geometry_exact') is False
assert case.get('fuel_endpoint') == (2742, 2070)
assert after.get('missing_archive') == 0
assert after.get('fuel_limited_discriminating_contradiction') == before.get('fuel_limited_discriminating_contradiction'), 'Contradiction count changed; inspect evidence'
print('Evidence collected. Review all counts and confounders; finite-fuel Tow remains OPEN.')
print('This runner does not promote rule status or change planets-intel.')
PY
test "$(git rev-parse HEAD)" = "$gate_head"
test -z "$(git status --porcelain)"
printf '\nCOLLECTED: %s\n' "$gate_dir"
cat "$gate_dir/status.tsv"
