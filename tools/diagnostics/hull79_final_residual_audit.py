from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_residual_profile import extract_hull_catalog
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


HULL_ID = 79
ROOT = Path("validation/corpus/compiled/v1")
DB_PATH = ROOT / "corpus.duckdb"
ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _value(raw: Mapping[str, Any], key: str) -> int | None:
    return _intish(raw.get(key))


def _distance_bucket(distance: float) -> str:
    if distance <= 1.5:
        return "<=1.5"
    if distance <= 10:
        return "1.5-10"
    if distance <= 50:
        return "10-50"
    if distance <= 90:
        return "50-90"
    if distance <= 150:
        return "90-150"
    if distance <= 500:
        return "150-500"
    if distance <= 1000:
        return "500-1000"
    return ">1000"


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def main() -> None:
    if not DB_PATH.is_file():
        raise SystemExit(f"missing compiled corpus database: {DB_PATH}")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                settings_hash,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                baseline_category,
                warp,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                observed_distance,
                nominal_max_distance
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id = ?
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """,
            [HULL_ID],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        raise SystemExit(f"no final residual rows for hull {HULL_ID}")

    rows_by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        rows_by_game[int(row[0])].append(row)

    print("===== HULL 79 FINAL RESIDUAL AUDIT =====")
    print("rows=", len(rows))
    print("games=", sorted(rows_by_game))

    print("\n===== HISTORICAL HULL CATALOG =====")
    catalog_fingerprints = Counter()
    for game_id in sorted(rows_by_game):
        archive_path = ARCHIVE_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        catalog = extract_hull_catalog(archive_data)
        hull = dict(catalog.hulls.get(HULL_ID, {}))
        fingerprint = tuple(
            (key, repr(hull.get(key)))
            for key in (
                "name",
                "raceid",
                "mass",
                "cargo",
                "fueltank",
                "crew",
                "engines",
                "beams",
                "torps",
                "launchers",
                "bays",
                "cancloak",
                "gravitonic",
                "isbase",
                "special",
                "advantage_ids",
                "advantage_names",
            )
        )
        catalog_fingerprints[fingerprint] += 1
        print(
            {
                "game_id": game_id,
                "catalog_consistent": catalog.consistent,
                "hull": hull,
            }
        )
    print("catalog_distinct_fingerprints=", len(catalog_fingerprints))

    by_game = Counter()
    baseline = Counter()
    warp_counts = Counter()
    distance_buckets = Counter()
    ratio_buckets = Counter()
    waypoint_relation = Counter()
    mission_pairs = Counter()
    selected_raw_values: dict[str, Counter[Any]] = defaultdict(Counter)
    raw_key_counts = Counter()
    displacement = Counter()
    examples: list[dict[str, Any]] = []
    reconstruction_issues = Counter()

    selected_keys = (
        "mission",
        "mission1",
        "mission1target",
        "missiontarget",
        "targetid",
        "targettype",
        "warp",
        "heading",
        "neutronium",
        "fuel",
        "mass",
        "damage",
        "cloak",
        "cloaked",
        "iscloaked",
    )

    for game_id, game_rows in sorted(rows_by_game.items()):
        archive_path = ARCHIVE_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        transitions = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }
        print(
            f"prepared game={game_id} cache_hit={prepared_hit} rows={len(game_rows)}"
        )

        for row in game_rows:
            (
                _game_id,
                settings_hash,
                before_turn,
                after_turn,
                ship_id,
                baseline_category,
                warp,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                observed_distance,
                nominal,
            ) = row

            by_game[(game_id, str(settings_hash))] += 1
            baseline[str(baseline_category)] += 1
            warp_counts[int(warp) if warp is not None else None] += 1
            observed_distance = float(observed_distance or 0.0)
            nominal = float(nominal or 0.0)
            distance_buckets[_distance_bucket(observed_distance)] += 1
            ratio_buckets[_ratio_bucket(observed_distance, nominal)] += 1

            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))
            waypoint = (int(target_x), int(target_y))
            if observed == origin:
                waypoint_relation["observed=origin"] += 1
            if observed == waypoint:
                waypoint_relation["observed=waypoint"] += 1
            if waypoint == origin:
                waypoint_relation["waypoint=origin"] += 1
            if observed != origin and observed != waypoint:
                waypoint_relation["observed=other"] += 1

            displacement[(observed[0] - origin[0], observed[1] - origin[1])] += 1

            transition = transitions.get((int(before_turn), int(after_turn), int(ship_id)))
            if transition is None:
                reconstruction_issues["transition_missing"] += 1
                continue
            sample = _sample_from_transition(transition, entities)
            if sample is None:
                reconstruction_issues["sample_missing"] += 1
                continue
            group = ship_groups.get((int(before_turn), int(ship_id)), ())
            owner_id, owner = _owner_record(group)
            if owner_id is None or owner is None:
                reconstruction_issues["owner_record_missing"] += 1
                continue

            raw = owner.raw
            raw_key_counts.update(str(key) for key in raw)
            mission = _value(raw, "mission")
            mission1 = _value(raw, "mission1")
            mission_pairs[(mission, mission1)] += 1
            for key in selected_keys:
                value = raw.get(key)
                if isinstance(value, (bool, int, float)) or value is None:
                    selected_raw_values[key][value] += 1

            if len(examples) < 40:
                examples.append(
                    {
                        "game": game_id,
                        "turn": int(before_turn),
                        "ship": int(ship_id),
                        "warp": sample.warp,
                        "origin": origin,
                        "observed": observed,
                        "waypoint": waypoint,
                        "distance": round(observed_distance, 3),
                        "nominal": round(nominal, 3),
                        "baseline": baseline_category,
                        "mission": mission,
                        "mission1": mission1,
                        "heading": _value(raw, "heading"),
                        "neutronium": _value(raw, "neutronium"),
                        "damage": _value(raw, "damage"),
                    }
                )

    print("\n===== BY GAME =====")
    for key, count in by_game.most_common():
        print(key, count)

    print("\n===== BASELINE CATEGORIES =====")
    for key, count in baseline.most_common():
        print(key, count)

    print("\n===== WARP =====")
    for key, count in warp_counts.most_common():
        print(key, count)

    print("\n===== DISTANCE BUCKETS =====")
    for key, count in distance_buckets.most_common():
        print(key, count)

    print("\n===== OBSERVED / NOMINAL RATIO =====")
    for key, count in ratio_buckets.most_common():
        print(key, count)

    print("\n===== WAYPOINT RELATION =====")
    for key, count in waypoint_relation.most_common():
        print(key, count)

    print("\n===== MISSION / MISSION1 =====")
    for key, count in mission_pairs.most_common():
        print(key, count)

    print("\n===== SELECTED RAW FIELD VALUES =====")
    for key in selected_keys:
        values = selected_raw_values.get(key)
        if not values:
            continue
        print(key, values.most_common(20))

    print("\n===== RAW KEY PRESENCE =====")
    for key, count in raw_key_counts.most_common():
        print(key, count)

    print("\n===== TOP RAW DISPLACEMENTS =====")
    for key, count in displacement.most_common(30):
        print(key, count, "distance=", round(hypot(*key), 3))

    print("\n===== RECONSTRUCTION ISSUES =====")
    print(reconstruction_issues)

    print("\n===== EXAMPLES =====")
    for example in examples:
        print(example)


if __name__ == "__main__":
    main()
