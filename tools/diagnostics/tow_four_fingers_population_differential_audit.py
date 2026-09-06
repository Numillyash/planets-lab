from __future__ import annotations

import argparse
import sys
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import (
    MovementSample,
    host_major_minor_destination,
)
from tools.diagnostics.tow_strict_lock_historical_audit import (
    _chain_nodes,
    _engine_count,
    _load_hulls,
    _tow_attempts_by_turn,
    _value,
)


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
DEFAULT_RAW_DIR = Path("validation/corpus/cache/loadall")
DEFAULT_PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
DEFAULT_HULLS_JSON = Path("validation/cache/planets-intel-hulls.json")
EXAMPLE_LIMIT = 80

MODELS = (
    "documented_euclidean_base",
    "euclidean_effective_range",
    "box_base_range",
    "box_effective_range",
)


def _xy(entity: Any) -> tuple[int, int] | None:
    x = _value(entity, "x")
    y = _value(entity, "y")
    if x is None or y is None:
        return None
    return x, y


def _gravitonic_multiplier(hull_id: int | None) -> int | None:
    if hull_id is None:
        return None
    return 2 if hull_id in GRAVITONIC_HULL_IDS else 1


def _four_fingers_models(
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
) -> tuple[dict[str, bool | None], dict[str, Any]]:
    unknown = {name: None for name in MODELS}
    detail: dict[str, Any] = {
        "waypoint_distance": None,
        "axis_distance": None,
        "base_range": None,
        "effective_range": None,
        "tower_speed": None,
        "target_speed": None,
        "speed_compare": None,
    }

    if target_fuel is None:
        return unknown, detail
    if target_fuel <= 25:
        return {name: False for name in MODELS}, detail
    if target_engine_count is None:
        return unknown, detail
    if target_engine_count < 2:
        return {name: False for name in MODELS}, detail
    if None in (
        target_x,
        target_y,
        target_warp,
        target_x_waypoint,
        target_y_waypoint,
        tower_warp,
    ):
        return unknown, detail

    tower_multiplier = _gravitonic_multiplier(tower_hull_id)
    target_multiplier = _gravitonic_multiplier(target_hull_id)
    if tower_multiplier is None or target_multiplier is None:
        return unknown, detail

    assert target_x is not None
    assert target_y is not None
    assert target_warp is not None
    assert target_x_waypoint is not None
    assert target_y_waypoint is not None
    assert tower_warp is not None

    dx = target_x_waypoint - target_x
    dy = target_y_waypoint - target_y
    waypoint_distance = hypot(dx, dy)
    axis_distance = max(abs(dx), abs(dy))
    base_range = float(target_warp * target_warp)
    effective_range = base_range * target_multiplier
    tower_speed = float(tower_warp * tower_warp * tower_multiplier)
    target_speed = float(target_warp * target_warp * target_multiplier)
    speed_compare = target_speed >= tower_speed

    detail.update(
        {
            "waypoint_distance": waypoint_distance,
            "axis_distance": axis_distance,
            "base_range": base_range,
            "effective_range": effective_range,
            "tower_speed": tower_speed,
            "target_speed": target_speed,
            "speed_compare": speed_compare,
        }
    )

    return (
        {
            "documented_euclidean_base": waypoint_distance > base_range and speed_compare,
            "euclidean_effective_range": waypoint_distance > effective_range and speed_compare,
            "box_base_range": axis_distance > base_range and speed_compare,
            "box_effective_range": axis_distance > effective_range and speed_compare,
        },
        detail,
    )


def _independent_navigation(
    *,
    entity_before: Any,
    entity_after: Any,
    hull_id: int | None,
    before_turn: int,
    planets: tuple[tuple[int, int, int], ...],
) -> dict[str, Any]:
    x = _value(entity_before, "x")
    y = _value(entity_before, "y")
    target_x = _value(entity_before, "targetx")
    target_y = _value(entity_before, "targety")
    warp = _value(entity_before, "warp")
    after_x = _value(entity_after, "x")
    after_y = _value(entity_after, "y")
    if None in (x, y, target_x, target_y, warp, after_x, after_y):
        return {
            "known": False,
            "regular_endpoint": None,
            "warp_well_endpoint": None,
            "warp_well_ambiguous": None,
            "observed_endpoint": None,
            "exact": None,
            "exact_basis": None,
        }

    assert x is not None
    assert y is not None
    assert target_x is not None
    assert target_y is not None
    assert warp is not None
    assert after_x is not None
    assert after_y is not None

    gravitonic = hull_id in GRAVITONIC_HULL_IDS if hull_id is not None else False
    sample = MovementSample(
        turn=before_turn,
        ship_id=0,
        x=x,
        y=y,
        target_x=target_x,
        target_y=target_y,
        warp=warp,
        next_x=after_x,
        next_y=after_y,
        hull_id=hull_id,
        gravitonic=gravitonic,
    )
    origin = (x, y)
    target = (target_x, target_y)
    observed = (after_x, after_y)
    max_distance = float(warp * warp * (2 if gravitonic else 1))
    target_distance = hypot(target_x - x, target_y - y)

    if warp <= 0:
        regular = origin
    elif target_distance <= max_distance + 1e-9:
        regular = target
    else:
        regular = host_major_minor_destination(sample)

    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=regular,
        planets=planets,
    )
    exact_basis = None
    if observed == regular:
        exact_basis = "regular"
    elif well is not None and observed == well:
        exact_basis = "warp_well"

    return {
        "known": True,
        "regular_endpoint": regular,
        "warp_well_endpoint": well,
        "warp_well_ambiguous": ambiguous,
        "observed_endpoint": observed,
        "exact": exact_basis is not None,
        "exact_basis": exact_basis,
    }


def _append_example(
    examples: list[dict[str, Any]],
    *,
    kind: str,
    game_id: int,
    turn: int,
    tower_id: int,
    target_id: int,
    tower_hull_id: int | None,
    target_hull_id: int | None,
    tower_fuel: int | None,
    target_fuel: int | None,
    models: Mapping[str, bool | None],
    detail: Mapping[str, Any],
    target_nav: Mapping[str, Any],
    tower_nav: Mapping[str, Any],
) -> None:
    if len(examples) >= EXAMPLE_LIMIT:
        return
    examples.append(
        {
            "kind": kind,
            "game": game_id,
            "turn": turn,
            "tower_ship": tower_id,
            "target_ship": target_id,
            "tower_hull": tower_hull_id,
            "target_hull": target_hull_id,
            "tower_fuel": tower_fuel,
            "target_fuel": target_fuel,
            "models": dict(models),
            "geometry": {
                "waypoint_distance": (
                    round(float(detail["waypoint_distance"]), 6)
                    if detail.get("waypoint_distance") is not None
                    else None
                ),
                "axis_distance": detail.get("axis_distance"),
                "base_range": detail.get("base_range"),
                "effective_range": detail.get("effective_range"),
                "tower_speed": detail.get("tower_speed"),
                "target_speed": detail.get("target_speed"),
            },
            "target_independent": dict(target_nav),
            "tower_independent": dict(tower_nav),
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
    model_counts: dict[str, Counter[str]] = {name: Counter() for name in MODELS}
    examples: list[dict[str, Any]] = []

    connection = duckdb.connect(str(database), read_only=True)
    try:
        game_ids = [int(row[0]) for row in connection.execute("SELECT game_id FROM games ORDER BY game_id").fetchall()]

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
            after_by_before = {before: after for before, after in pairs}

            archive = (raw_dir / f"game-{game_id}.zip").read_bytes()
            prepared, cache_hit = load_or_build_prepared_game_cache(
                archive,
                game_id=game_id,
                cache_path=prepared_dir / f"game-{game_id}.pickle",
            )
            entities = _entity_map(prepared.snapshots)
            planets_by_turn = _planet_tuples_by_turn(entities)
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

            game_totals: Counter[str] = Counter()
            seen_attempts: set[tuple[int, int, int]] = set()

            for (before_turn, target_id), matching_towers in sorted(matches.items()):
                if len(matching_towers) != 1:
                    continue
                tower_id = matching_towers[0]
                after_turn = after_by_before.get(before_turn)
                if after_turn is None:
                    continue
                seen_attempts.add((before_turn, tower_id, target_id))

                turn_attempts = attempts_by_turn.get(before_turn, ())
                targeters = tuple(item for item in turn_attempts if item[1] == target_id)
                chain_nodes = _chain_nodes(turn_attempts)
                if len(targeters) != 1 or tower_id in chain_nodes or target_id in chain_nodes:
                    continue

                tower_before = entities.get(("ship", before_turn, tower_id))
                target_before = entities.get(("ship", before_turn, target_id))
                tower_after = entities.get(("ship", after_turn, tower_id))
                target_after = entities.get(("ship", after_turn, target_id))
                if None in (tower_before, target_before, tower_after, target_after):
                    continue

                tower_hull_id = _value(tower_before, "hullid")
                target_hull_id = _value(target_before, "hullid")
                tower_engine_count = _engine_count(hulls, tower_hull_id)
                target_engine_count = _engine_count(hulls, target_hull_id)
                if tower_engine_count is None or tower_engine_count < 2:
                    continue

                tower_fuel = _value(tower_before, "neutronium")
                target_fuel = _value(target_before, "neutronium")
                tower_warp = _value(tower_before, "warp")
                target_warp = _value(target_before, "warp")
                target_x = _value(target_before, "x")
                target_y = _value(target_before, "y")
                target_x_waypoint = _value(target_before, "targetx")
                target_y_waypoint = _value(target_before, "targety")

                models, detail = _four_fingers_models(
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
                target_nav = _independent_navigation(
                    entity_before=target_before,
                    entity_after=target_after,
                    hull_id=target_hull_id,
                    before_turn=before_turn,
                    planets=planets_by_turn.get(before_turn, ()),
                )
                tower_nav = _independent_navigation(
                    entity_before=tower_before,
                    entity_after=tower_after,
                    hull_id=tower_hull_id,
                    before_turn=before_turn,
                    planets=planets_by_turn.get(before_turn, ()),
                )

                totals["positive_route_unique_engine_eligible"] += 1
                game_totals["positive_route_unique_engine_eligible"] += 1
                if target_nav.get("exact") is True:
                    totals["positive_target_independent_exact"] += 1
                    game_totals["positive_target_independent_exact"] += 1
                    continue

                totals["positive_tow_influence_candidates"] += 1
                game_totals["positive_tow_influence_candidates"] += 1
                for model, result in models.items():
                    if result is True:
                        model_counts[model]["positive_contradictions"] += 1
                    elif result is False:
                        model_counts[model]["positive_compatible"] += 1
                    else:
                        model_counts[model]["positive_unknown"] += 1

                if any(result is True for result in models.values()):
                    _append_example(
                        examples,
                        kind="positive_route_model_contradiction",
                        game_id=game_id,
                        turn=before_turn,
                        tower_id=tower_id,
                        target_id=target_id,
                        tower_hull_id=tower_hull_id,
                        target_hull_id=target_hull_id,
                        tower_fuel=tower_fuel,
                        target_fuel=target_fuel,
                        models=models,
                        detail=detail,
                        target_nav=target_nav,
                        tower_nav=tower_nav,
                    )

            for before_turn, attempts in sorted(attempts_by_turn.items()):
                after_turn = after_by_before.get(before_turn)
                if after_turn is None:
                    continue
                target_counts = Counter(target_id for _tower_id, target_id in attempts if target_id is not None)
                chain_nodes = _chain_nodes(attempts)

                for tower_id, target_id in attempts:
                    if target_id is None or target_id <= 0 or target_id == tower_id:
                        continue
                    if (before_turn, tower_id, target_id) in seen_attempts:
                        continue
                    if target_counts[target_id] != 1 or tower_id in chain_nodes or target_id in chain_nodes:
                        continue

                    tower_before = entities.get(("ship", before_turn, tower_id))
                    target_before = entities.get(("ship", before_turn, target_id))
                    tower_after = entities.get(("ship", after_turn, tower_id))
                    target_after = entities.get(("ship", after_turn, target_id))
                    if None in (tower_before, target_before, tower_after, target_after):
                        continue
                    if _xy(tower_before) is None or _xy(target_before) is None:
                        continue
                    if _xy(tower_before) != _xy(target_before):
                        continue
                    if _xy(tower_after) is None or _xy(target_after) is None:
                        continue
                    if _xy(tower_after) == _xy(target_after):
                        continue
                    if _xy(tower_after) == _xy(tower_before):
                        continue

                    tower_hull_id = _value(tower_before, "hullid")
                    target_hull_id = _value(target_before, "hullid")
                    tower_engine_count = _engine_count(hulls, tower_hull_id)
                    target_engine_count = _engine_count(hulls, target_hull_id)
                    tower_fuel = _value(tower_before, "neutronium")
                    target_fuel = _value(target_before, "neutronium")
                    if tower_engine_count is None or tower_engine_count < 2:
                        continue
                    if tower_fuel is None or tower_fuel <= 0:
                        continue

                    target_nav = _independent_navigation(
                        entity_before=target_before,
                        entity_after=target_after,
                        hull_id=target_hull_id,
                        before_turn=before_turn,
                        planets=planets_by_turn.get(before_turn, ()),
                    )
                    tower_nav = _independent_navigation(
                        entity_before=tower_before,
                        entity_after=tower_after,
                        hull_id=tower_hull_id,
                        before_turn=before_turn,
                        planets=planets_by_turn.get(before_turn, ()),
                    )
                    if target_nav.get("exact") is not True or tower_nav.get("exact") is not True:
                        continue

                    models, detail = _four_fingers_models(
                        tower_hull_id=tower_hull_id,
                        tower_warp=_value(tower_before, "warp"),
                        target_hull_id=target_hull_id,
                        target_engine_count=target_engine_count,
                        target_fuel=target_fuel,
                        target_x=_value(target_before, "x"),
                        target_y=_value(target_before, "y"),
                        target_warp=_value(target_before, "warp"),
                        target_x_waypoint=_value(target_before, "targetx"),
                        target_y_waypoint=_value(target_before, "targety"),
                    )
                    if all(result is None for result in models.values()):
                        continue

                    totals["strong_separated_independent_routes"] += 1
                    game_totals["strong_separated_independent_routes"] += 1
                    for model, result in models.items():
                        if result is True:
                            model_counts[model]["separated_support"] += 1
                        elif result is False:
                            model_counts[model]["separated_miss"] += 1
                        else:
                            model_counts[model]["separated_unknown"] += 1

                    if any(result is True for result in models.values()):
                        _append_example(
                            examples,
                            kind="strong_separated_independent_routes",
                            game_id=game_id,
                            turn=before_turn,
                            tower_id=tower_id,
                            target_id=target_id,
                            tower_hull_id=tower_hull_id,
                            target_hull_id=target_hull_id,
                            tower_fuel=tower_fuel,
                            target_fuel=target_fuel,
                            models=models,
                            detail=detail,
                            target_nav=target_nav,
                            tower_nav=tower_nav,
                        )

            print(
                {
                    "game": game_id,
                    "prepared_cache_hit": cache_hit,
                    "positive_tow_influence_candidates": game_totals["positive_tow_influence_candidates"],
                    "positive_target_independent_exact": game_totals["positive_target_independent_exact"],
                    "strong_separated_independent_routes": game_totals["strong_separated_independent_routes"],
                }
            )
    finally:
        connection.close()

    print("\n===== FOUR-FINGERS POPULATION DIFFERENTIAL =====")
    for key in (
        "positive_route_unique_engine_eligible",
        "positive_target_independent_exact",
        "positive_tow_influence_candidates",
        "strong_separated_independent_routes",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== MODEL COUNTS =====")
    for model in MODELS:
        counts = model_counts[model]
        print(
            {
                "model": model,
                "positive_contradictions": counts["positive_contradictions"],
                "positive_compatible": counts["positive_compatible"],
                "positive_unknown": counts["positive_unknown"],
                "separated_support": counts["separated_support"],
                "separated_miss": counts["separated_miss"],
                "separated_unknown": counts["separated_unknown"],
            }
        )

    print("\n===== EXAMPLES =====")
    for item in examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print("Positive Tow-influence candidates are observed same-route Tow pairs after removing cases where the target independently reaches the same endpoint, including an eligible warp-well snap.")
    print("A model predicting break on a positive Tow-influence candidate is a direct historical contradiction for that threshold model, subject to the route-evidence limitations of the corpus.")
    print("Strong separated candidates require unique topology, >=2 tower engines, positive visible tower fuel, colocation, different post positions, and exact independent navigation for both tower and target.")
    print("Separated support is supporting evidence for a break model; separated misses are investigation cases because an unmodeled Tow-failure reason can still exist.")
    print("box_* models are implementation hypotheses only. They test max(abs(dx), abs(dy)) as the long-waypoint gate and are not promoted without differential evidence.")
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
