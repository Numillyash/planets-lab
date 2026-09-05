from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_context import (
    TOW_ATTEMPT,
    MovementMissionConvention,
    _classify_owner_record,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _resolved_value,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _owner_record,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
DEFAULT_HULLS_JSON = Path("validation/cache/planets-intel-hulls.json")
EXAMPLE_LIMIT = 80


def _target_id(raw: Mapping[str, Any]) -> int | None:
    value = _intish(
        raw.get(
            "mission1target",
            raw.get("mission1_target_id", raw.get("mission1targetid")),
        )
    )
    return value if value is not None and value > 0 else None


def _load_hulls(path: Path) -> dict[int, Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        payload = payload.get("hulls")
    if not isinstance(payload, list):
        raise ValueError("hulls JSON must be a list or an object containing a 'hulls' list")

    result: dict[int, Mapping[str, Any]] = {}
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        hull_id = _intish(item.get("id"))
        if hull_id is None or hull_id <= 0:
            continue
        result[hull_id] = item
    if not result:
        raise ValueError("hulls JSON did not contain any usable hull records")
    return result


def _engine_count(hulls: Mapping[int, Mapping[str, Any]], hull_id: int | None) -> int | None:
    if hull_id is None:
        return None
    raw = hulls.get(hull_id)
    if raw is None:
        return None
    for key in ("engines", "enginecount", "engine_count", "engineslots"):
        if key not in raw:
            continue
        value = _intish(raw.get(key))
        return value if value is not None and value >= 0 else None
    return None


def _value(entity: Any, key: str) -> int | None:
    if entity is None:
        return None
    return _intish(_resolved_value(entity, key))


def _tow_attempts_by_turn(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    pairs: set[tuple[int, int]],
    convention: MovementMissionConvention,
) -> dict[int, tuple[tuple[int, int | None], ...]]:
    result: dict[int, list[tuple[int, int | None]]] = defaultdict(list)

    for before_turn, _after_turn in sorted(pairs):
        tower_ids = sorted(
            entity_id
            for kind, turn, entity_id in entities
            if kind == "ship" and turn == before_turn
        )
        for tower_id in tower_ids:
            group = ship_groups.get((before_turn, tower_id), ())
            _, owner = _owner_record(group)
            if owner is None:
                continue
            if _classify_owner_record(owner, convention=convention) != TOW_ATTEMPT:
                continue
            result[before_turn].append((tower_id, _target_id(owner.raw)))

    return {
        turn: tuple(sorted(items))
        for turn, items in result.items()
    }


def _chain_nodes(attempts: tuple[tuple[int, int | None], ...]) -> frozenset[int]:
    tower_ids = {tower_id for tower_id, _target_id_value in attempts}
    nodes: set[int] = set()
    for tower_id, target_id in attempts:
        if target_id is not None and target_id in tower_ids:
            nodes.add(tower_id)
            nodes.add(target_id)
    return frozenset(nodes)


def _target_breaks_tow(
    *,
    tower_hull_id: int | None,
    tower_warp: int | None,
    target_hull_id: int | None,
    target_engine_count: int | None,
    target_fuel: int | None,
    target_x: int | None,
    target_y: int | None,
    target_warp: int | None,
    target_x_waypoint: int | None,
    target_y_waypoint: int | None,
) -> tuple[bool | None, str]:
    if target_fuel is None:
        return None, "target_fuel_unknown"
    if target_fuel <= 25:
        return False, "target_fuel_le_25"

    if target_engine_count is None:
        return None, "target_engine_count_unknown"
    if target_engine_count < 2:
        return False, "target_single_engine"

    if None in (
        target_x,
        target_y,
        target_warp,
        target_x_waypoint,
        target_y_waypoint,
    ):
        return None, "target_navigation_unknown"

    assert target_x is not None
    assert target_y is not None
    assert target_warp is not None
    assert target_x_waypoint is not None
    assert target_y_waypoint is not None

    waypoint_distance = hypot(
        target_x_waypoint - target_x,
        target_y_waypoint - target_y,
    )
    if waypoint_distance <= target_warp * target_warp:
        return False, "target_waypoint_within_warp_square"

    if tower_warp is None:
        return None, "tower_warp_unknown"
    if tower_hull_id is None or target_hull_id is None:
        return None, "hull_id_unknown"

    tower_multiplier = 2 if tower_hull_id in GRAVITONIC_HULL_IDS else 1
    target_multiplier = 2 if target_hull_id in GRAVITONIC_HULL_IDS else 1
    tower_speed = tower_warp * tower_warp * tower_multiplier
    target_speed = target_warp * target_warp * target_multiplier
    return target_speed >= tower_speed, "four_fingers_speed_compare"


def _append_example(
    examples: list[dict[str, Any]],
    *,
    reason: str,
    game_id: int,
    turn: int,
    tower_id: int,
    target_id: int,
    tower_hull_id: int | None,
    target_hull_id: int | None,
    tower_engine_count: int | None,
    target_engine_count: int | None,
    tower_fuel: int | None,
    target_fuel: int | None,
    tower_warp: int | None,
    target_warp: int | None,
    target_x: int | None,
    target_y: int | None,
    target_x_waypoint: int | None,
    target_y_waypoint: int | None,
) -> None:
    if len(examples) >= EXAMPLE_LIMIT:
        return
    waypoint_distance = None
    if None not in (target_x, target_y, target_x_waypoint, target_y_waypoint):
        assert target_x is not None
        assert target_y is not None
        assert target_x_waypoint is not None
        assert target_y_waypoint is not None
        waypoint_distance = round(
            hypot(target_x_waypoint - target_x, target_y_waypoint - target_y),
            3,
        )
    examples.append(
        {
            "reason": reason,
            "game": game_id,
            "turn": turn,
            "tower_ship": tower_id,
            "tower_hull": tower_hull_id,
            "tower_engines": tower_engine_count,
            "tower_fuel": tower_fuel,
            "tower_warp": tower_warp,
            "target_ship": target_id,
            "target_hull": target_hull_id,
            "target_engines": target_engine_count,
            "target_fuel": target_fuel,
            "target_warp": target_warp,
            "target_waypoint_distance": waypoint_distance,
        }
    )


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
    break_reasons: Counter[str] = Counter()
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
            matches, observed_counts = _observed_tow_targets(
                entities=entities,
                ship_groups=ship_groups,
                valid_pairs=pairs,
                convention=convention,
            )

            game_counts: Counter[str] = Counter()
            game_counts.update(observed_counts)

            for (before_turn, target_id), matching_towers in sorted(matches.items()):
                totals["observed_route_targets"] += 1
                totals["observed_route_attempts"] += len(matching_towers)
                game_counts["observed_route_targets"] += 1
                game_counts["observed_route_attempts"] += len(matching_towers)

                if len(matching_towers) != 1:
                    totals["route_equivalent_identity_ambiguous"] += 1
                    game_counts["route_equivalent_identity_ambiguous"] += 1
                    continue

                totals["observed_single_route"] += 1
                game_counts["observed_single_route"] += 1
                tower_id = matching_towers[0]
                turn_attempts = attempts_by_turn.get(before_turn, ())
                targeters = tuple(
                    item for item in turn_attempts if item[1] == target_id
                )
                if len(targeters) != 1:
                    totals["strict_excluded_same_target_contest"] += 1
                    game_counts["strict_excluded_same_target_contest"] += 1
                    continue

                chain_nodes = _chain_nodes(turn_attempts)
                if tower_id in chain_nodes or target_id in chain_nodes:
                    totals["strict_excluded_tow_chain"] += 1
                    game_counts["strict_excluded_tow_chain"] += 1
                    continue

                totals["strict_topology_unique"] += 1
                game_counts["strict_topology_unique"] += 1

                tower = entities.get(("ship", before_turn, tower_id))
                target = entities.get(("ship", before_turn, target_id))
                tower_hull_id = _value(tower, "hullid")
                target_hull_id = _value(target, "hullid")
                tower_engine_count = _engine_count(hulls, tower_hull_id)
                target_engine_count = _engine_count(hulls, target_hull_id)
                tower_fuel = _value(tower, "neutronium")
                target_fuel = _value(target, "neutronium")
                tower_warp = _value(tower, "warp")
                target_warp = _value(target, "warp")
                target_x = _value(target, "x")
                target_y = _value(target, "y")
                target_x_waypoint = _value(target, "targetx")
                target_y_waypoint = _value(target, "targety")

                if tower_engine_count is None:
                    totals["strict_unknown_tower_engine_count"] += 1
                    game_counts["strict_unknown_tower_engine_count"] += 1
                    _append_example(
                        examples,
                        reason="tower_engine_count_unknown",
                        game_id=game_id,
                        turn=before_turn,
                        tower_id=tower_id,
                        target_id=target_id,
                        tower_hull_id=tower_hull_id,
                        target_hull_id=target_hull_id,
                        tower_engine_count=tower_engine_count,
                        target_engine_count=target_engine_count,
                        tower_fuel=tower_fuel,
                        target_fuel=target_fuel,
                        tower_warp=tower_warp,
                        target_warp=target_warp,
                        target_x=target_x,
                        target_y=target_y,
                        target_x_waypoint=target_x_waypoint,
                        target_y_waypoint=target_y_waypoint,
                    )
                    continue
                if tower_engine_count < 2:
                    totals["observed_success_tower_lt2_engines"] += 1
                    game_counts["observed_success_tower_lt2_engines"] += 1
                    _append_example(
                        examples,
                        reason="observed_success_tower_lt2_engines",
                        game_id=game_id,
                        turn=before_turn,
                        tower_id=tower_id,
                        target_id=target_id,
                        tower_hull_id=tower_hull_id,
                        target_hull_id=target_hull_id,
                        tower_engine_count=tower_engine_count,
                        target_engine_count=target_engine_count,
                        tower_fuel=tower_fuel,
                        target_fuel=target_fuel,
                        tower_warp=tower_warp,
                        target_warp=target_warp,
                        target_x=target_x,
                        target_y=target_y,
                        target_x_waypoint=target_x_waypoint,
                        target_y_waypoint=target_y_waypoint,
                    )
                    continue

                totals["tower_engine_eligible"] += 1
                game_counts["tower_engine_eligible"] += 1
                if tower_fuel is None:
                    totals["strict_unknown_tower_fuel"] += 1
                    game_counts["strict_unknown_tower_fuel"] += 1
                elif tower_fuel <= 0:
                    totals["observed_success_tower_nonpositive_fuel"] += 1
                    game_counts["observed_success_tower_nonpositive_fuel"] += 1
                else:
                    totals["tower_positive_fuel"] += 1
                    game_counts["tower_positive_fuel"] += 1

                broke, break_reason = _target_breaks_tow(
                    tower_hull_id=tower_hull_id,
                    tower_warp=tower_warp,
                    target_hull_id=target_hull_id,
                    target_engine_count=target_engine_count,
                    target_fuel=target_fuel,
                    target_x=target_x,
                    target_y=target_y,
                    target_warp=target_warp,
                    target_x_waypoint=target_x_waypoint,
                    target_y_waypoint=target_y_waypoint,
                )
                break_reasons[break_reason] += 1
                if broke is None:
                    totals["strict_unknown_target_break"] += 1
                    game_counts["strict_unknown_target_break"] += 1
                    _append_example(
                        examples,
                        reason=break_reason,
                        game_id=game_id,
                        turn=before_turn,
                        tower_id=tower_id,
                        target_id=target_id,
                        tower_hull_id=tower_hull_id,
                        target_hull_id=target_hull_id,
                        tower_engine_count=tower_engine_count,
                        target_engine_count=target_engine_count,
                        tower_fuel=tower_fuel,
                        target_fuel=target_fuel,
                        tower_warp=tower_warp,
                        target_warp=target_warp,
                        target_x=target_x,
                        target_y=target_y,
                        target_x_waypoint=target_x_waypoint,
                        target_y_waypoint=target_y_waypoint,
                    )
                    continue
                if broke:
                    totals["observed_success_target_break_predicate_true"] += 1
                    game_counts["observed_success_target_break_predicate_true"] += 1
                    _append_example(
                        examples,
                        reason="observed_success_target_break_predicate_true",
                        game_id=game_id,
                        turn=before_turn,
                        tower_id=tower_id,
                        target_id=target_id,
                        tower_hull_id=tower_hull_id,
                        target_hull_id=target_hull_id,
                        tower_engine_count=tower_engine_count,
                        target_engine_count=target_engine_count,
                        tower_fuel=tower_fuel,
                        target_fuel=target_fuel,
                        tower_warp=tower_warp,
                        target_warp=target_warp,
                        target_x=target_x,
                        target_y=target_y,
                        target_x_waypoint=target_x_waypoint,
                        target_y_waypoint=target_y_waypoint,
                    )
                    continue

                totals["target_break_false"] += 1
                game_counts["target_break_false"] += 1
                if tower_fuel is not None and tower_fuel > 0:
                    totals["strict_lock_compatible_positive_fuel"] += 1
                    game_counts["strict_lock_compatible_positive_fuel"] += 1
                else:
                    totals["strict_lock_compatible_except_tower_fuel"] += 1
                    game_counts["strict_lock_compatible_except_tower_fuel"] += 1

            print(
                {
                    "game": game_id,
                    "prepared_cache_hit": cache_hit,
                    "observed_single_route": game_counts["observed_single_route"],
                    "route_equivalent_identity_ambiguous": game_counts[
                        "route_equivalent_identity_ambiguous"
                    ],
                    "strict_topology_unique": game_counts["strict_topology_unique"],
                    "strict_lock_compatible_positive_fuel": game_counts[
                        "strict_lock_compatible_positive_fuel"
                    ],
                    "strict_lock_compatible_except_tower_fuel": game_counts[
                        "strict_lock_compatible_except_tower_fuel"
                    ],
                    "observed_success_tower_lt2_engines": game_counts[
                        "observed_success_tower_lt2_engines"
                    ],
                    "observed_success_target_break_predicate_true": game_counts[
                        "observed_success_target_break_predicate_true"
                    ],
                    "strict_unknown_target_break": game_counts[
                        "strict_unknown_target_break"
                    ],
                }
            )
    finally:
        connection.close()

    print("\n===== HISTORICAL STRICT TOW LOCK AUDIT =====")
    for key in (
        "observed_route_targets",
        "observed_route_attempts",
        "observed_single_route",
        "route_equivalent_identity_ambiguous",
        "strict_excluded_same_target_contest",
        "strict_excluded_tow_chain",
        "strict_topology_unique",
        "strict_unknown_tower_engine_count",
        "observed_success_tower_lt2_engines",
        "tower_engine_eligible",
        "strict_unknown_tower_fuel",
        "observed_success_tower_nonpositive_fuel",
        "tower_positive_fuel",
        "strict_unknown_target_break",
        "observed_success_target_break_predicate_true",
        "target_break_false",
        "strict_lock_compatible_positive_fuel",
        "strict_lock_compatible_except_tower_fuel",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== TARGET BREAK DECISION REASONS =====")
    for reason, count in break_reasons.most_common():
        print(reason, count)

    print("\n===== SANITIZED EXCEPTIONS / UNKNOWNS =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION =====")
    print(
        "This audit uses ex-post owner-visible successful Tow routes only as positive Host evidence. "
        "It does not classify stationary/different-destination attempts as failed Tow, and it does "
        "not infer a winner for route-equivalent multiple towers."
    )
    print(
        "A strong production-compatible result has zero observed_success_tower_lt2_engines and zero "
        "observed_success_target_break_predicate_true, with a large strict_lock_compatible_positive_fuel "
        "population. Nonpositive tower fuel is reported separately because the prepared corpus does not "
        "retain the unlimited-fuel game setting."
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the planets-intel strict Tow-lock predicate against historical successful Tow routes."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=DEFAULT_PREPARED_DIR)
    parser.add_argument("--hulls-json", type=Path, default=DEFAULT_HULLS_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(
        database=args.database,
        raw_dir=args.raw_dir,
        prepared_dir=args.prepared_dir,
        hulls_json=args.hulls_json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
