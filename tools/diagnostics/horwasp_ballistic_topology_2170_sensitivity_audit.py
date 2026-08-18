from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import duckdb

from planets_lab.corpus.compiled_movement_labels import load_external_residual_keys
from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map
from planets_lab.corpus.movement_horwasp_ballistic_context import (
    _classify_ballistic_formula,
    _historical_ballistic_hulls,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_residual_profile import extract_hull_catalog
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


GAME_ID = 591478
ALT_PERIOD = 2170

archive_path = Path(f"validation/corpus/cache/loadall/game-{GAME_ID}.zip")
prepared_path = Path(f"validation/corpus/cache/prepared-v1/game-{GAME_ID}.pickle")
compiled_dir = Path("validation/corpus/compiled/v1")
movement_parquet = (
    compiled_dir
    / "mechanics"
    / "movement_transitions"
    / f"game_id={GAME_ID}"
    / "part-000.parquet"
)
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

catalog = extract_hull_catalog(archive)
ballistic_hulls = _historical_ballistic_hulls(catalog.hulls)
print("ballistic_hulls=", sorted(ballistic_hulls))
print(
    "ballistic_names=",
    {hull_id: catalog.hulls[hull_id].get("name") for hull_id in sorted(ballistic_hulls)},
)

con = duckdb.connect(str(database_path), read_only=True)
try:
    rows = con.execute(
        """
        SELECT
            before_archive_turn,
            after_archive_turn,
            ship_id,
            hull_id,
            horwasp_category,
            horwasp_strong_explained,
            post_horwasp_strong_residual,
            label_issue
        FROM movement_labeled_residual
        WHERE game_id = ?
          AND post_chunnel_residual = true
          AND horwasp_candidate_kind = 'ballistic'
        ORDER BY hull_id, before_archive_turn, ship_id
        """,
        [GAME_ID],
    ).fetchall()
finally:
    con.close()

records = prepared.snapshots
entities = _entity_map(records)
ship_groups = group_perspective_records(records, "ship")
transition_by_key = {
    (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
    for item in prepared.movement_geometry_readiness.results
}
external_keys = set(load_external_residual_keys(movement_parquet))

by_hull: dict[int, Counter[str]] = defaultdict(Counter)
raw_db_mismatches: list[dict[str, object]] = []
gain_categories: dict[int, Counter[str]] = defaultdict(Counter)
loss_categories: dict[int, Counter[str]] = defaultdict(Counter)
examples_gain: list[dict[str, object]] = []
examples_loss: list[dict[str, object]] = []

for (
    before_turn,
    after_turn,
    ship_id,
    hull_id,
    db_category,
    db_strong,
    db_residual,
    label_issue,
) in rows:
    key = (int(before_turn), int(after_turn), int(ship_id))
    hull_id = int(hull_id)
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

    expected_db_category = db_category or "ballistic_unresolved"
    if expected_db_category != raw_name or bool(db_strong) != bool(raw_strong):
        if len(raw_db_mismatches) < 30:
            raw_db_mismatches.append(
                {
                    "key": key,
                    "hull": hull_id,
                    "db": (db_category, bool(db_strong)),
                    "recomputed_raw": (raw_name, bool(raw_strong)),
                }
            )

    stats = by_hull[hull_id]
    stats["rows"] += 1
    stats["db_strong"] += int(bool(db_strong))
    stats["db_residual"] += int(bool(db_residual))
    stats["alt_strong"] += int(bool(alt_strong))
    if not raw_strong and alt_strong:
        stats["gain"] += 1
        gain_categories[hull_id][alt_name] += 1
        if len(examples_gain) < 30:
            examples_gain.append(
                {
                    "turn": int(before_turn),
                    "ship": int(ship_id),
                    "hull": hull_id,
                    "warp": sample.warp,
                    "origin": (sample.x, sample.y),
                    "observed": sample.observed_destination,
                    "raw": (raw_name, bool(raw_strong)),
                    "alt": (alt_name, bool(alt_strong)),
                }
            )
    if raw_strong and not alt_strong:
        stats["loss"] += 1
        loss_categories[hull_id][raw_name] += 1
        if len(examples_loss) < 30:
            examples_loss.append(
                {
                    "turn": int(before_turn),
                    "ship": int(ship_id),
                    "hull": hull_id,
                    "warp": sample.warp,
                    "origin": (sample.x, sample.y),
                    "observed": sample.observed_destination,
                    "raw": (raw_name, bool(raw_strong)),
                    "alt": (alt_name, bool(alt_strong)),
                }
            )

print("\n===== DATABASE RECOMPUTE CHECK =====")
print("ballistic_rows=", len(rows))
print("db_recompute_mismatch_count=", len(raw_db_mismatches))
for item in raw_db_mismatches:
    print(item)

print("\n===== BY HULL: 2150 -> 2170 =====")
print("hull | name | rows | db_strong | db_residual | alt_strong | gain | loss | net")
for hull_id, stats in sorted(
    by_hull.items(),
    key=lambda item: (-(item[1]["gain"] - item[1]["loss"]), -item[1]["rows"], item[0]),
):
    name = str(catalog.hulls.get(hull_id, {}).get("name") or "")
    net = stats["gain"] - stats["loss"]
    print(
        f"{hull_id} | {name} | {stats['rows']} | {stats['db_strong']} | "
        f"{stats['db_residual']} | {stats['alt_strong']} | {stats['gain']} | "
        f"{stats['loss']} | {net}"
    )
    if gain_categories[hull_id]:
        print("  gain_categories=", gain_categories[hull_id])
    if loss_categories[hull_id]:
        print("  loss_categories=", loss_categories[hull_id])

print("\n===== TOTAL PERIOD SENSITIVITY =====")
total_gain = sum(stats["gain"] for stats in by_hull.values())
total_loss = sum(stats["loss"] for stats in by_hull.values())
total_db_strong = sum(stats["db_strong"] for stats in by_hull.values())
total_alt_strong = sum(stats["alt_strong"] for stats in by_hull.values())
print("db_strong=", total_db_strong)
print("alt_strong=", total_alt_strong)
print("current_nonstrong_becomes_alt_strong=", total_gain)
print("current_strong_lost_under_alt=", total_loss)
print("net_strong_change=", total_gain - total_loss)

print("\n===== GAIN EXAMPLES =====")
for item in examples_gain:
    print(item)

print("\n===== LOSS EXAMPLES =====")
for item in examples_loss:
    print(item)

print("\nNOTE: this is a sensitivity audit only.")
print("It substitutes period 2170 for the existing classifier only inside historical game 591478.")
print("It does not generalize 2170 to other games or derive mapwidth+20.")
