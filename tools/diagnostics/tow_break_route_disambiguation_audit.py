from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import _entity_map
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules import max_nominal_distance
from planets_lab.sim.normal_movement import project_toward_waypoint
from tools.diagnostics.tow_strict_lock_historical_audit import (
    _chain_nodes,
    _engine_count,
    _load_hulls,
    _target_breaks_tow,
    _tow_attempts_by_turn,
    _value,
)


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
DEFAULT_HULLS_JSON = Path("validation/cache/planets-intel-hulls.json")
EXAMPLE_LIMIT = 80


def _nominal_endpoint(entity: Any, *, hull_id: int | None) -> tuple[int, int] | None:
    x = _value(entity, "x")
    y = _value(entity, "y")
    warp = _value(entity, "warp")
    target_x = _value(entity, "targetx")
    target_y = _value(entity, "targety")
    if None in (x, y, warp, target_x, target_y):
        return None

    assert x is not None
    assert y is not None
    assert warp is not None
    assert target_x is not None
    assert target_y is not None

    max_distance = max_nominal_distance(
        warp,
        gravitonic=hull_id in GRAVITONIC_HULL_IDS,
    )
    return project_toward_waypoint(
        x=x,
        y=y,
        target_x=target_x,
        target_y=target_y,
        distance=max_distance,
    )


def _position(entity: Any) -> tuple[int, int] | None:
    x = _value(entity, "x")
    y = _value(entity, "y")
    if x is None or y is None:
        return None
    return x, y


def run(
    *,
    database: Path,
    raw_dir: Path,
    prepared_dir: Path,
    hulls_json: Path,
) -> int:
    hulls = _load_hulls(hulls_json)
    convention = MovementMissionConvention()
    totals: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    connection = duckdb.connect(str(database), read_only=True)
    try:
        game_ids = [
            int(row[0])
            for row in connection.execute(
                "SELECT game_id FROM games ORDER BY game_id"
            ).fetchall()
        ]

        for game_id in game_ids:
            pairs = {
                (int(before_turn), int(after_turn))
                for before_turn, after_turn in connection.execute(
                    """
                    SELECT DISTINCT before_archive_turn, after_archive_turn
                    FROM movement_transitions
                    WHERE game_id = ?
                    ORDER BY before_archive_turn, after_archive_turn
                    """,
                    [game_id],
                ).fetchall()
            }
            after_by_before: dict[int, set[int]] = defaultdict(set)
            for before_turn, after_turn in pairs:
                after_by_before[before_turn].add(after_turn)

            archive = (raw_dir / f"game-{game_id}.zip").read_bytes()
            prepared, cache_hit = load_or_build_prepared_game_cache(
                archive,
                game_id=game_id,
                cache_path=prepared_dir / f"game-{game_id}.pickle",
            )
            entities = _entity_map(prepared.snapshots)
            ship_groups = group_perspective_records(prepared.snapshots, "ship")
            attempts_by_turn = _tow_attempts_by_turn(
                entities=entities,
                ship_groups=ship_groups,
                pairs=pairs,
                convention=convention,
            )
            matches, _observed_counts = _observed_tow_targets(
                entities=entities,
                ship_groups=ship_groups,
                valid_pairs=pairs,
                convention=convention,
            )

            game_counts: Counter[str] = Counter()
            for (before_turn, target_id), matching_towers in sorted(matches.items()):
                if len(matching_towers) != 1:
                    continue

                tower_id = matching_towers[0]
                turn_attempts = attempts_by_turn.get(before_turn, ())
                targeters = tuple(item for item in turn_attempts if item[1] == target_id)
                if len(targeters) != 1:
                    continue

                chain_nodes = _chain_nodes(turn_attempts)
                if tower_id in chain_nodes or target_id in chain_nodes:
                    continue

                tower = entities.get(("ship", before_turn, tower_id))
                target = entities.get(("ship", before_turn, target_id))
                tower_hull_id = _value(tower, "hullid")
                target_hull_id = _value(target, "hullid")
                tower_engine_count = _engine_count(hulls, tower_hull_id)
                target_engine_count = _engine_count(hulls, target_hull_id)

                broke, _reason = _target_breaks_tow(
                    tower_hull_id=tower_hull_id,
                    tower_warp=_value(tower, "warp"),
                    target_hull_id=target_hull_id,
                    target_engine_count=target_engine_count,
                    target_fuel=_value(target, "neutronium"),
                    target_x=_value(target, "x"),
                    target_y=_value(target, "y"),
                    target_warp=_value(target, "warp"),
                    target_x_waypoint=_value(target, "targetx"),
                    target_y_waypoint=_value(target, "targety"),
                )
                if broke is not True:
                    continue

                totals["break_true_observed_route_matches"] += 1
                game_counts["break_true_observed_route_matches"] += 1

                after_turns = after_by_before.get(before_turn, set())
                if len(after_turns) != 1:
                    totals["after_turn_ambiguous"] += 1
                    game_counts["after_turn_ambiguous"] += 1
                    continue
                after_turn = next(iter(after_turns))

                tower_after = entities.get(("ship", after_turn, tower_id))
                target_after = entities.get(("ship", after_turn, target_id))
                observed_target = _position(target_after)
                observed_tower = _position(tower_after)
                target_nominal = _nominal_endpoint(target, hull_id=target_hull_id)
                tower_nominal = _nominal_endpoint(tower, hull_id=tower_hull_id)

                if observed_target is None or observed_tower is None:
                    totals["after_position_missing"] += 1
                    game_counts["after_position_missing"] += 1
                    continue

                if observed_target != observed_tower:
                    totals["route_match_post_position_disagrees"] += 1
                    game_counts["route_match_post_position_disagrees"] += 1

                target_exact = target_nominal == observed_target
                tower_exact = tower_nominal == observed_tower
                if target_nominal is None:
                    totals["target_nominal_unknown"] += 1
                    game_counts["target_nominal_unknown"] += 1
                elif target_exact:
                    totals["target_independent_nominal_exact"] += 1
                    game_counts["target_independent_nominal_exact"] += 1
                else:
                    totals["target_independent_nominal_differs"] += 1
                    game_counts["target_independent_nominal_differs"] += 1

                if tower_nominal is None:
                    totals["tower_nominal_unknown"] += 1
                    game_counts["tower_nominal_unknown"] += 1
                elif tower_exact:
                    totals["tower_independent_nominal_exact"] += 1
                    game_counts["tower_independent_nominal_exact"] += 1
                else:
                    totals["tower_independent_nominal_differs"] += 1
                    game_counts["tower_independent_nominal_differs"] += 1

                if target_exact and tower_exact:
                    totals["both_independent_nominal_exact"] += 1
                    game_counts["both_independent_nominal_exact"] += 1

                after_target_warp = _value(target_after, "warp")
                if after_target_warp == 0:
                    totals["after_target_warp_zero_supporting_only"] += 1
                    game_counts["after_target_warp_zero_supporting_only"] += 1

                if len(examples) < EXAMPLE_LIMIT:
                    examples.append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "after_turn": after_turn,
                            "tower_ship": tower_id,
                            "tower_hull": tower_hull_id,
                            "tower_engines": tower_engine_count,
                            "tower_warp": _value(tower, "warp"),
                            "target_ship": target_id,
                            "target_hull": target_hull_id,
                            "target_engines": target_engine_count,
                            "target_warp": _value(target, "warp"),
                            "target_fuel": _value(target, "neutronium"),
                            "observed_endpoint": observed_target,
                            "target_nominal_endpoint": target_nominal,
                            "tower_nominal_endpoint": tower_nominal,
                            "target_nominal_exact": target_exact,
                            "tower_nominal_exact": tower_exact,
                            "after_target_warp": after_target_warp,
                        }
                    )

            print(
                {
                    "game": game_id,
                    "prepared_cache_hit": cache_hit,
                    "break_true_observed_route_matches": game_counts[
                        "break_true_observed_route_matches"
                    ],
                    "target_independent_nominal_exact": game_counts[
                        "target_independent_nominal_exact"
                    ],
                    "target_independent_nominal_differs": game_counts[
                        "target_independent_nominal_differs"
                    ],
                    "both_independent_nominal_exact": game_counts[
                        "both_independent_nominal_exact"
                    ],
                }
            )
    finally:
        connection.close()

    print()
    print("===== TOW BREAK ROUTE DISAMBIGUATION =====")
    for key in (
        "break_true_observed_route_matches",
        "after_turn_ambiguous",
        "after_position_missing",
        "route_match_post_position_disagrees",
        "target_nominal_unknown",
        "target_independent_nominal_exact",
        "target_independent_nominal_differs",
        "tower_nominal_unknown",
        "tower_independent_nominal_exact",
        "tower_independent_nominal_differs",
        "both_independent_nominal_exact",
        "after_target_warp_zero_supporting_only",
    ):
        print(f"{key}= {totals[key]}")

    print()
    print("===== CASES =====")
    for item in examples:
        print(item)

    print()
    print("===== INTERPRETATION =====")
    print(
        "A tower and target ending together is route evidence, not by itself proof that the Tow lock succeeded."
    )
    print(
        "target_independent_nominal_exact means the target can reach the observed endpoint under its own pre-Host navigation, so the historical route match cannot falsify Four Fingers."
    )
    print(
        "target_independent_nominal_differs remains an investigation case; geometry-only projection intentionally does not absorb fuel proration, warp wells, mines, storms, or other external movement."
    )
    print(
        "after_target_warp_zero is supporting only because historical next-snapshot warp/waypoint fields are editable and are not a reliable immediate post-movement phase boundary."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=DEFAULT_PREPARED_DIR)
    parser.add_argument("--hulls-json", type=Path, default=DEFAULT_HULLS_JSON)
    args = parser.parse_args()
    raise SystemExit(
        run(
            database=args.database,
            raw_dir=args.raw_dir,
            prepared_dir=args.prepared_dir,
            hulls_json=args.hulls_json,
        )
    )


if __name__ == "__main__":
    main()
