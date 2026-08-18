from __future__ import annotations

from collections import Counter
from dataclasses import replace
from math import hypot
from pathlib import Path

import duckdb

from planets_lab.corpus.compiled_movement_labels import load_external_residual_keys
from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map
from planets_lab.corpus.movement_horwasp_ballistic_context import _classify_ballistic_formula
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
HULL_ID = 210
ALT_PERIOD = 2170

archive_path = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
prepared_path = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")
compiled_dir = Path("validation/corpus/compiled/v1")
movement_parquet = compiled_dir / "mechanics" / "movement_transitions" / f"game_id={GAME_ID}" / "part-000.parquet"
database_path = compiled_dir / "corpus.duckdb"

archive = archive_path.read_bytes()
prepared, hit = load_or_build_prepared_game_cache(
    archive,
    game_id=GAME_ID,
    cache_path=prepared_path,
)
print("prepared_cache_hit=", hit)

raw_topology = extract_map_topology(archive)
alt_topology = replace(raw_topology, mapwidth=ALT_PERIOD, mapheight=ALT_PERIOD)
print(
    "raw_topology=",
    {
        "sphere": raw_topology.sphere,
        "mapwidth": raw_topology.mapwidth,
        "mapheight": raw_topology.mapheight,
        "mapshape": raw_topology.mapshape,
        "stable": raw_topology.stable,
    },
)
print(
    "alt_topology=",
    {
        "sphere": alt_topology.sphere,
        "mapwidth": alt_topology.mapwidth,
        "mapheight": alt_topology.mapheight,
        "mapshape": alt_topology.mapshape,
        "stable": alt_topology.stable,
    },
)

con = duckdb.connect(str(database_path), read_only=True)
try:
    rows = con.execute(
        """
        SELECT
            before_archive_turn,
            after_archive_turn,
            ship_id,
            horwasp_category,
            horwasp_strong_explained,
            post_horwasp_strong_residual,
            label_issue
        FROM movement_labeled_residual
        WHERE game_id = ?
          AND hull_id = ?
          AND post_chunnel_residual = true
        ORDER BY before_archive_turn, ship_id
        """,
        [GAME_ID, HULL_ID],
    ).fetchall()
finally:
    con.close()

print("post_chunnel_hull210_rows=", len(rows))
print("db_strong=", sum(bool(row[4]) for row in rows))
print("db_residual=", sum(bool(row[5]) for row in rows))
print("db_categories=", Counter((row[3], bool(row[4])) for row in rows))
print("db_label_issues=", Counter(row[6] for row in rows))

records = prepared.snapshots
entities = _entity_map(records)
ship_groups = group_perspective_records(records, "ship")
transition_by_key = {
    (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
    for item in prepared.movement_geometry_readiness.results
}
external_keys = set(load_external_residual_keys(movement_parquet))

comparison = Counter()
raw_categories = Counter()
alt_categories = Counter()
residual_alt_categories = Counter()
raw_db_mismatches = []
examples_gain = []
examples_still = []
examples_loss = []

def vector_distance(origin, destination, topology):
    if topology.sphere is True and topology.mapwidth and topology.mapheight:
        dx_raw = destination[0] - origin[0]
        dy_raw = destination[1] - origin[1]
        wx = min((dx_raw - topology.mapwidth, dx_raw, dx_raw + topology.mapwidth), key=lambda value: (abs(value), abs(value - dx_raw)))
        wy = min((dy_raw - topology.mapheight, dy_raw, dy_raw + topology.mapheight), key=lambda value: (abs(value), abs(value - dy_raw)))
        return hypot(wx, wy)
    return hypot(destination[0] - origin[0], destination[1] - origin[1])

for before_turn, after_turn, ship_id, db_category, db_strong, db_residual, label_issue in rows:
    key = (int(before_turn), int(after_turn), int(ship_id))
    if key not in external_keys:
        raise AssertionError(f"joined row {key} is not in external residual keys")
    transition = transition_by_key.get(key)
    if transition is None:
        raise AssertionError(f"missing prepared transition {key}")
    sample = _sample_from_transition(transition, entities)
    if sample is None:
        raise AssertionError(f"missing movement sample {key}")
    group = ship_groups.get((int(before_turn), int(ship_id)), ())
    owner_id, owner = _owner_record(group)
    if owner_id is None or owner is None:
        raise AssertionError(f"missing owner record {key}")

    kwargs = dict(
        raw=owner.raw,
        origin=(sample.x, sample.y),
        observed=sample.observed_destination,
        target=(sample.target_x, sample.target_y),
        warp=sample.warp,
    )
    raw_category, raw_strong = _classify_ballistic_formula(topology=raw_topology, **kwargs)
    alt_category, alt_strong = _classify_ballistic_formula(topology=alt_topology, **kwargs)

    raw_name = raw_category or "ballistic_unresolved"
    alt_name = alt_category or "ballistic_unresolved"
    raw_categories[(raw_name, raw_strong)] += 1
    alt_categories[(alt_name, alt_strong)] += 1
    comparison[(raw_strong, alt_strong)] += 1

    expected_db_category = db_category or "ballistic_unresolved"
    if expected_db_category != raw_name or bool(db_strong) != bool(raw_strong):
        if len(raw_db_mismatches) < 20:
            raw_db_mismatches.append(
                {
                    "key": key,
                    "db": (db_category, bool(db_strong)),
                    "recomputed_raw": (raw_name, bool(raw_strong)),
                }
            )

    origin = (sample.x, sample.y)
    observed = sample.observed_destination
    detail = {
        "turn": int(before_turn),
        "ship": int(ship_id),
        "warp": sample.warp,
        "origin": origin,
        "observed": observed,
        "target": (sample.target_x, sample.target_y),
        "raw_distance": round(vector_distance(origin, observed, raw_topology), 3),
        "alt_distance": round(vector_distance(origin, observed, alt_topology), 3),
        "raw": (raw_name, bool(raw_strong)),
        "alt": (alt_name, bool(alt_strong)),
    }

    if bool(db_residual):
        residual_alt_categories[(alt_name, alt_strong)] += 1
        if alt_strong and len(examples_gain) < 20:
            examples_gain.append(detail)
        elif not alt_strong and len(examples_still) < 20:
            examples_still.append(detail)
    elif raw_strong and not alt_strong and len(examples_loss) < 20:
        examples_loss.append(detail)

print("\n===== RECOMPUTED CURRENT TOPOLOGY =====")
print("categories=", raw_categories)
print("db_recompute_mismatch_count=", len(raw_db_mismatches))
for item in raw_db_mismatches:
    print(item)

print("\n===== PERIOD SENSITIVITY =====")
print("strong_current_to_alt=", comparison)
print("alt_categories=", alt_categories)
print("current_residual_alt_categories=", residual_alt_categories)
print("current_residual_becomes_alt_strong=", sum(count for (category, strong), count in residual_alt_categories.items() if strong))
print("current_strong_lost_under_alt=", comparison[(True, False)])

print("\n===== EXAMPLES: CURRENT RESIDUAL -> ALT STRONG =====")
for item in examples_gain:
    print(item)

print("\n===== EXAMPLES: STILL RESIDUAL UNDER ALT =====")
for item in examples_still:
    print(item)

print("\n===== EXAMPLES: CURRENT STRONG -> ALT NONSTRONG =====")
for item in examples_loss:
    print(item)

print("\nNOTE: this audit changes only the wrapped period supplied to the existing ballistic classifier.")
print("It does not assert that 2170 is globally correct; 2170 remains evidence-scoped to game 591478.")
