from __future__ import annotations

from collections import Counter
from math import hypot
from pathlib import Path

import duckdb

from planets_lab.corpus.compiled_movement_labels import load_external_residual_keys
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_ballistic_context import _historical_mite_hulls
from planets_lab.corpus.movement_horwasp_mite_context import (
    ROUND_TOLERANCE_LY,
    _identity,
    _owner_records,
    _same_point,
    _distance,
    _wp,
    classify_scoped_mite_fallback_transition,
    discover_scoped_mite_fallback_runs,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_residual_profile import extract_hull_catalog
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

GAME_ID = 591478
PERIODS = (2170, 2170)

archive_path = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
prepared_path = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")
movement_parquet = Path(
    f"validation/corpus/compiled/v1/mechanics/movement_transitions/game_id={GAME_ID}/part-000.parquet"
)

archive = archive_path.read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive,
    game_id=GAME_ID,
    cache_path=prepared_path,
)
print("prepared_cache_hit=", hit)

records = prepared.snapshots
ship_groups = group_perspective_records(records, "ship")
owner_records = _owner_records(ship_groups)
hull_catalog = extract_hull_catalog(archive)
mite_hulls = _historical_mite_hulls(hull_catalog.hulls)
runs_by_ship = discover_scoped_mite_fallback_runs(
    game_id=GAME_ID,
    ship_groups=ship_groups,
    mite_hulls=mite_hulls,
)

print("mite_hulls=", sorted(mite_hulls))
print("discovered_run_count=", sum(len(v) for v in runs_by_ship.values()))
print("discovered_ship_count=", len(runs_by_ship))
print("run_lengths=", Counter(run.tracking_end - run.tracking_start + 1 for runs in runs_by_ship.values() for run in runs))
print("focus_runs=")
for sid in (1110, 1163, 1167, 1185):
    print(sid, runs_by_ship.get(sid))

residual_keys = load_external_residual_keys(movement_parquet)
transition_by_key = {
    (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
    for item in prepared.movement_geometry_readiness.results
}

# Read just the fields that identify the 786 compiled Mite residual candidates.
connection = duckdb.connect(":memory:")
try:
    candidate_rows = connection.execute(
        """
        SELECT before_archive_turn, after_archive_turn, ship_id, hull_id,
               x_before, y_before, x_after, y_after, warp
        FROM read_parquet(?)
        WHERE post_external_residual = true AND hull_id IN (SELECT * FROM unnest(?))
        ORDER BY before_archive_turn, ship_id
        """,
        [str(movement_parquet), list(sorted(mite_hulls))],
    ).fetchall()
finally:
    connection.close()

print("compiled_mite_candidate_rows=", len(candidate_rows))

counts: Counter[str] = Counter()
mission_counts: Counter[tuple[int | None, int | None]] = Counter()
examples: dict[str, list[dict[str, object]]] = {}


def sample(reason: str, value: dict[str, object]) -> None:
    bucket = examples.setdefault(reason, [])
    if len(bucket) < 6:
        bucket.append(value)


for before, after, ship_id, hull_id, xb, yb, xa, ya, warp in candidate_rows:
    group = ship_groups.get((int(before), int(ship_id)), ())
    owner_id, owner = _owner_record(group)
    if owner_id is None or owner_id <= 0 or owner is None:
        counts["owner_unavailable"] += 1
        continue
    raw = owner.raw
    mission = _intish(raw.get("mission"))
    m1 = _intish(raw.get("mission1target"))
    mission_counts[(mission, m1)] += 1

    origin = (int(xb), int(yb))
    observed = (int(xa), int(ya))
    warp_i = int(warp)

    category, strong = classify_scoped_mite_fallback_transition(
        game_id=GAME_ID,
        before_turn=int(before),
        ship_id=int(ship_id),
        owner_id=int(owner_id),
        raw=raw,
        origin=origin,
        observed=observed,
        warp=warp_i,
        runs_by_ship=runs_by_ship,
    )
    if strong:
        counts["STRONG"] += 1
        sample("STRONG", {"turn": before, "ship": ship_id, "category": category})
        continue

    if warp_i <= 0:
        reason = "warp_nonpositive"
    elif mission != 0 or m1 not in (None, 0):
        reason = "not_clear_state"
    else:
        ident = _identity(int(owner_id), raw)
        same_ship_runs = runs_by_ship.get(int(ship_id), ())
        same_identity_runs = [run for run in same_ship_runs if run.identity == ident]
        eligible = [run for run in same_identity_runs if int(before) >= run.tracking_end + 1]
        if not same_ship_runs:
            reason = "no_discovered_run_for_numeric_id"
        elif not same_identity_runs:
            reason = "run_identity_mismatch"
        elif not eligible:
            reason = "before_run_clear_boundary"
        else:
            run = max(eligible, key=lambda item: (item.tracking_end, item.tracking_start))
            if not _same_point(_wp(raw), run.anchor, periods=PERIODS):
                reason = "wp_not_anchor"
            else:
                remaining = _distance(origin, run.anchor, periods=PERIODS)
                after_remaining = _distance(observed, run.anchor, periods=PERIODS)
                step = _distance(origin, observed, periods=PERIODS)
                if remaining is None or after_remaining is None or step is None:
                    reason = "geometry_unavailable"
                else:
                    progress = remaining - after_remaining
                    expected = min(float(warp_i * warp_i), remaining)
                    if progress < -ROUND_TOLERANCE_LY:
                        reason = "moves_away"
                    elif abs(step - progress) > ROUND_TOLERANCE_LY:
                        reason = "not_straight_toward_anchor"
                    elif abs(step - expected) > ROUND_TOLERANCE_LY:
                        reason = "not_warp2_step"
                    else:
                        reason = "unexpected_classifier_reject"

    counts[reason] += 1
    sample(
        reason,
        {
            "turn": int(before),
            "ship": int(ship_id),
            "hull": int(hull_id),
            "owner": int(owner_id),
            "mission": mission,
            "m1": m1,
            "raw_turn": _intish(raw.get("turn")),
            "xy": origin,
            "next": observed,
            "wp": _wp(raw),
            "warp": warp_i,
            "runs_for_id": len(runs_by_ship.get(int(ship_id), ())),
        },
    )

print("\n===== CANDIDATE CLASSIFICATION =====")
for key, value in counts.most_common():
    print(key, value)

print("\n===== MISSION / M1 TOP =====")
for key, value in mission_counts.most_common(20):
    print(key, value)

print("\n===== EXAMPLES =====")
for reason in counts:
    print("\n--", reason, "--")
    for row in examples.get(reason, []):
        print(row)
