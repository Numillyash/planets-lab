from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _movement_category,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample


COMPILED_DIR = Path("validation/corpus/compiled/v1")
DATABASE_PATH = COMPILED_DIR / "corpus.duckdb"
ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _point_from_mapping(value: Mapping[str, Any]) -> tuple[int, int] | None:
    for x_key, y_key in (("x", "y"), ("targetx", "targety"), ("target_x", "target_y")):
        x = _intish(value.get(x_key))
        y = _intish(value.get(y_key))
        if x is not None and y is not None:
            return x, y
    return None


def _waypoint_points(value: Any) -> tuple[tuple[int, int], ...]:
    """Extract coordinate pairs from the raw waypoints value without text fields."""

    result: list[tuple[int, int]] = []

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            point = _point_from_mapping(item)
            if point is not None:
                result.append(point)
            for child in item.values():
                if isinstance(child, (Mapping, list, tuple)):
                    visit(child)
            return
        if isinstance(item, (list, tuple)):
            if len(item) == 2:
                x = _intish(item[0])
                y = _intish(item[1])
                if x is not None and y is not None:
                    result.append((x, y))
                    return
            for child in item:
                if isinstance(child, (Mapping, list, tuple)):
                    visit(child)

    visit(value)
    # Preserve order while removing exact duplicates caused by nested representations.
    seen: set[tuple[int, int]] = set()
    unique: list[tuple[int, int]] = []
    for point in result:
        if point in seen:
            continue
        seen.add(point)
        unique.append(point)
    return tuple(unique)


def _candidate_category(
    *,
    turn: int,
    ship_id: int,
    hull_id: int | None,
    origin: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    candidate: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> str:
    sample = MovementSample(
        turn=turn,
        ship_id=ship_id,
        x=origin[0],
        y=origin[1],
        target_x=candidate[0],
        target_y=candidate[1],
        warp=warp,
        next_x=observed[0],
        next_y=observed[1],
        hull_id=hull_id,
    )
    return _movement_category(sample, planets=planets)


def main() -> None:
    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                before_embedded_turn,
                ship_id,
                hull_id,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                warp,
                baseline_category
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id IS NOT NULL
              AND x_before IS NOT NULL
              AND y_before IS NOT NULL
              AND x_after IS NOT NULL
              AND y_after IS NOT NULL
              AND target_x IS NOT NULL
              AND target_y IS NOT NULL
              AND warp IS NOT NULL
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== MULTI-WAYPOINT FINAL RESIDUAL AUDIT =====")
    print("rows=", len(rows))

    rows_by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        rows_by_game[int(row[0])].append(row)

    total = Counter()
    by_hull: dict[int, Counter] = defaultdict(Counter)
    by_game: dict[int, Counter] = defaultdict(Counter)
    point_count_distribution = Counter()
    any_match_categories = Counter()
    first_match_categories = Counter()
    examples: list[dict[str, Any]] = []
    structure_examples: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(rows_by_game.items()):
        archive_path = ARCHIVE_DIR / f"game-{game_id}.zip"
        prepared_path = PREPARED_DIR / f"game-{game_id}.pickle"
        archive = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive,
            game_id=game_id,
            cache_path=prepared_path,
        )
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(game_rows)}")

        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        planets_by_turn = _planet_tuples_by_turn(entities)

        for row in game_rows:
            (
                _,
                before_turn,
                before_embedded_turn,
                ship_id,
                hull_id,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                warp,
                baseline_category,
            ) = row
            before_turn = int(before_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            origin = (int(x_before), int(y_before))
            observed = (int(x_after), int(y_after))
            target = (int(target_x), int(target_y))

            total["rows"] += 1
            by_hull[hull_id]["rows"] += 1
            by_game[game_id]["rows"] += 1
            if target == origin:
                total["target_is_origin"] += 1
                by_hull[hull_id]["target_is_origin"] += 1

            group = ship_groups.get((before_turn, ship_id), ())
            owner_id, owner = _owner_record(group)
            if owner_id is None or owner is None:
                total["owner_missing"] += 1
                continue

            raw_waypoints = owner.raw.get("waypoints")
            if raw_waypoints is None:
                total["waypoints_field_missing"] += 1
                continue
            total["waypoints_field_present"] += 1
            by_hull[hull_id]["waypoints_field_present"] += 1
            by_game[game_id]["waypoints_field_present"] += 1

            points = _waypoint_points(raw_waypoints)
            point_count_distribution[len(points)] += 1
            if not points:
                total["waypoints_no_points"] += 1
                continue

            total["waypoints_have_points"] += 1
            by_hull[hull_id]["waypoints_have_points"] += 1
            by_game[game_id]["waypoints_have_points"] += 1

            if len(structure_examples) < 20:
                structure_examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "ship": ship_id,
                        "hull": hull_id,
                        "raw_type": type(raw_waypoints).__name__,
                        "points": points[:8],
                    }
                )

            planets = planets_by_turn.get(before_turn, ())
            categories: list[str] = []
            for point in points:
                category = _candidate_category(
                    turn=int(before_embedded_turn),
                    ship_id=ship_id,
                    hull_id=hull_id,
                    origin=origin,
                    observed=observed,
                    warp=warp,
                    candidate=point,
                    planets=planets,
                )
                categories.append(category)

            explained_indices = [
                index
                for index, category in enumerate(categories)
                if category in GEOMETRY_EXPLAINED_CATEGORIES
            ]
            if explained_indices:
                total["any_queue_candidate_explains"] += 1
                by_hull[hull_id]["any_queue_candidate_explains"] += 1
                by_game[game_id]["any_queue_candidate_explains"] += 1
                first_index = explained_indices[0]
                any_match_categories[categories[first_index]] += 1
                if first_index == 0:
                    total["first_queue_candidate_explains"] += 1
                    by_hull[hull_id]["first_queue_candidate_explains"] += 1
                    first_match_categories[categories[first_index]] += 1
                if first_index == len(points) - 1:
                    total["last_queue_candidate_explains"] += 1
                    by_hull[hull_id]["last_queue_candidate_explains"] += 1
                if target == origin:
                    total["target_origin_and_queue_explains"] += 1
                    by_hull[hull_id]["target_origin_and_queue_explains"] += 1
                if hull_id == 79:
                    total["hull79_queue_explains"] += 1

                if len(examples) < 50:
                    examples.append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "warp": warp,
                            "origin": origin,
                            "observed": observed,
                            "compiled_target": target,
                            "baseline": baseline_category,
                            "queue_points": points[:8],
                            "explaining_index": first_index,
                            "explaining_point": points[first_index],
                            "category": categories[first_index],
                        }
                    )
            else:
                total["queue_points_do_not_explain"] += 1
                by_hull[hull_id]["queue_points_do_not_explain"] += 1

            if observed in points:
                total["observed_equals_queue_point"] += 1
                by_hull[hull_id]["observed_equals_queue_point"] += 1
            if target in points:
                total["compiled_target_in_queue"] += 1
                by_hull[hull_id]["compiled_target_in_queue"] += 1

    print("\n===== TOTAL =====")
    for key in (
        "rows",
        "target_is_origin",
        "owner_missing",
        "waypoints_field_missing",
        "waypoints_field_present",
        "waypoints_no_points",
        "waypoints_have_points",
        "any_queue_candidate_explains",
        "first_queue_candidate_explains",
        "last_queue_candidate_explains",
        "target_origin_and_queue_explains",
        "observed_equals_queue_point",
        "compiled_target_in_queue",
        "queue_points_do_not_explain",
        "hull79_queue_explains",
    ):
        print(f"{key}=", total[key])

    print("\n===== WAYPOINT POINT COUNT DISTRIBUTION =====")
    for key, count in point_count_distribution.most_common():
        print(key, count)

    print("\n===== EXPLAINED CATEGORIES =====")
    print("any_candidate=", any_match_categories)
    print("first_candidate=", first_match_categories)

    print("\n===== TOP HULLS BY QUEUE EXPLANATION =====")
    print("hull | rows | target_origin | have_points | any_explains | first_explains | observed_eq_point | no_explain")
    for hull_id in sorted(
        by_hull,
        key=lambda hull: (-by_hull[hull]["any_queue_candidate_explains"], -by_hull[hull]["rows"], hull),
    )[:50]:
        stats = by_hull[hull_id]
        print(
            hull_id,
            "|",
            stats["rows"],
            "|",
            stats["target_is_origin"],
            "|",
            stats["waypoints_have_points"],
            "|",
            stats["any_queue_candidate_explains"],
            "|",
            stats["first_queue_candidate_explains"],
            "|",
            stats["observed_equals_queue_point"],
            "|",
            stats["queue_points_do_not_explain"],
        )

    print("\n===== BY GAME =====")
    for game_id, stats in sorted(by_game.items(), key=lambda item: (-item[1]["any_queue_candidate_explains"], item[0])):
        print(game_id, dict(stats))

    print("\n===== SANITIZED WAYPOINT STRUCTURE EXAMPLES =====")
    for item in structure_examples:
        print(item)

    print("\n===== QUEUE-EXPLAINED EXAMPLES =====")
    for item in examples:
        print(item)


if __name__ == "__main__":
    main()
