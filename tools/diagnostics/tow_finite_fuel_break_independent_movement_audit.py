from __future__ import annotations

import argparse
import ast
import re
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_chunnel_context import _effective_sample
from planets_lab.corpus.movement_damage_context import _race_map, max_warp_from_damage
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _resolved_value,
    _warp_well_destination,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _navigation_endpoint,
    _owner_record,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_population_audit import _nonfuel_lock_proof
from tow_strict_lock_historical_audit import _target_breaks_tow


EXAMPLE_LIMIT = 100
CHUNNEL_EXCLUSION = "observed_chunnel_route_warpwell_exact"


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _resolution_cases(path: Path) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = path.read_text(encoding="utf-8")
    total = _counter(text, "cases")
    excluded = _counter(text, "refined_observed_chunnel_route_warpwell_exact")
    exact_turn_clean = _counter(text, "refined_exact_turn_catalog_no_chunnel_lead")
    if total != 9 or excluded != 2 or exact_turn_clean != 1:
        raise ValueError(
            "unexpected passenger-resolution checkpoint: "
            f"cases={total} chunnel_exact={excluded} exact_turn_clean={exact_turn_clean}"
        )

    try:
        block = text.split("===== CASES =====", 1)[1].split(
            "===== INTERPRETATION =====", 1
        )[0]
    except IndexError as exc:
        raise ValueError("passenger-resolution log has no CASES block") from exc

    cases: list[dict[str, Any]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        item = ast.literal_eval(line)
        if isinstance(item, dict) and "game" in item:
            cases.append(item)
    if len(cases) != total:
        raise ValueError(f"case parsing mismatch: parsed={len(cases)} expected={total}")

    remaining = tuple(
        item for item in cases if str(item.get("refined_lead")) != CHUNNEL_EXCLUSION
    )
    if len(remaining) != total - excluded:
        raise ValueError(
            f"remaining population mismatch: {len(remaining)} != {total - excluded}"
        )
    return total - excluded, remaining


def _value(entity: Any, field: str) -> int | None:
    if entity is None:
        return None
    return _intish(_resolved_value(entity, field))


def _owner_state(
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    *,
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _sample_for_ship(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    before_turn: int,
    after_turn: int,
    ship_id: int,
) -> MovementSample | None:
    before = entities.get(("ship", before_turn, ship_id))
    after = entities.get(("ship", after_turn, ship_id))
    values = (
        _value(before, "x"),
        _value(before, "y"),
        _value(before, "targetx"),
        _value(before, "targety"),
        _value(before, "warp"),
        _value(after, "x"),
        _value(after, "y"),
        _value(before, "hullid"),
    )
    x, y, target_x, target_y, warp, next_x, next_y, hull_id = values
    if None in (x, y, target_x, target_y, warp, next_x, next_y) or hull_id is None:
        return None
    return MovementSample(
        turn=before_turn,
        ship_id=ship_id,
        x=int(x),
        y=int(y),
        target_x=int(target_x),
        target_y=int(target_y),
        warp=int(warp),
        next_x=int(next_x),
        next_y=int(next_y),
        gravitonic=int(hull_id) in GRAVITONIC_HULL_IDS,
        hull_id=int(hull_id),
    )


def _endpoint_with_warpwell(
    sample: MovementSample,
    *,
    planets: Sequence[tuple[int, int, int]],
) -> tuple[tuple[int, int] | None, tuple[int, int] | None, bool]:
    effective = _effective_sample(sample)
    direct = _navigation_endpoint(effective)
    well, ambiguous = _warp_well_destination(
        sample=effective,
        endpoint=direct,
        planets=planets,
    )
    if ambiguous:
        return direct, None, True
    return direct, (well if well is not None else direct), False


def _strict_damage_endpoint(
    sample: MovementSample,
    *,
    raw: Mapping[str, Any] | None,
    race_id: int | None,
    planets: Sequence[tuple[int, int, int]],
) -> dict[str, Any]:
    damage = _intish(raw.get("damage")) if raw is not None else None
    supplies = _intish(raw.get("supplies")) if raw is not None else None
    result: dict[str, Any] = {
        "damage": damage,
        "supplies": supplies,
        "race_id": race_id,
        "effective_warp": None,
        "direct_endpoint": None,
        "endpoint": None,
        "warpwell_ambiguous": False,
        "eligible": False,
    }
    if supplies is None or supplies < 0 or supplies >= 5:
        return result
    effective_warp = max_warp_from_damage(damage, race_id)
    if effective_warp is None or effective_warp >= sample.warp or effective_warp <= 0:
        return result

    damaged = MovementSample(
        turn=sample.turn,
        ship_id=sample.ship_id,
        x=sample.x,
        y=sample.y,
        target_x=sample.target_x,
        target_y=sample.target_y,
        warp=int(effective_warp),
        next_x=sample.next_x,
        next_y=sample.next_y,
        gravitonic=sample.gravitonic,
        hull_id=sample.hull_id,
    )
    direct, endpoint, ambiguous = _endpoint_with_warpwell(damaged, planets=planets)
    result.update(
        {
            "effective_warp": int(effective_warp),
            "direct_endpoint": direct,
            "endpoint": endpoint,
            "warpwell_ambiguous": ambiguous,
            "eligible": True,
        }
    )
    return result


def _independent_navigation(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    races: Mapping[int, int],
    planets: Sequence[tuple[int, int, int]],
    before_turn: int,
    after_turn: int,
    ship_id: int,
    common_destination: tuple[int, int],
) -> dict[str, Any]:
    sample = _sample_for_ship(
        entities=entities,
        before_turn=before_turn,
        after_turn=after_turn,
        ship_id=ship_id,
    )
    owner_id, raw = _owner_state(ship_groups, turn=before_turn, ship_id=ship_id)
    if sample is None:
        return {
            "status": "sample_missing",
            "owner": owner_id,
            "snapshot_fuel": _intish(raw.get("neutronium")) if raw is not None else None,
            "ordinary_exact": False,
            "damage_exact": False,
            "any_exact": False,
        }

    direct, endpoint, ambiguous = _endpoint_with_warpwell(sample, planets=planets)
    ordinary_exact = endpoint == common_destination if endpoint is not None else False
    damage = _strict_damage_endpoint(
        sample,
        raw=raw,
        race_id=races.get(owner_id) if owner_id is not None else None,
        planets=planets,
    )
    damage_exact = damage.get("endpoint") == common_destination if damage.get("endpoint") is not None else False

    after = entities.get(("ship", after_turn, ship_id))
    factual_after = None
    if after is not None:
        ax = _value(after, "x")
        ay = _value(after, "y")
        if ax is not None and ay is not None:
            factual_after = (ax, ay)

    return {
        "status": "ready",
        "owner": owner_id,
        "hull": sample.hull_id,
        "gravitonic": sample.gravitonic,
        "warp": sample.warp,
        "origin": (sample.x, sample.y),
        "waypoint": (sample.target_x, sample.target_y),
        "factual_after": factual_after,
        "snapshot_fuel": _intish(raw.get("neutronium")) if raw is not None else None,
        "ordinary_direct_endpoint": direct,
        "ordinary_endpoint": endpoint,
        "ordinary_warpwell_ambiguous": ambiguous,
        "ordinary_exact": ordinary_exact,
        "damage": damage,
        "damage_exact": damage_exact,
        "any_exact": ordinary_exact or damage_exact,
    }


def _four_fingers_context(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    specs: Any,
    before_turn: int,
    tower_id: int,
    target_id: int,
) -> dict[str, Any]:
    tower = entities.get(("ship", before_turn, tower_id))
    target = entities.get(("ship", before_turn, target_id))
    tower_hull = _value(tower, "hullid")
    target_hull = _value(target, "hullid")
    tower_warp = _value(tower, "warp")
    target_warp = _value(target, "warp")
    target_x = _value(target, "x")
    target_y = _value(target, "y")
    target_x_waypoint = _value(target, "targetx")
    target_y_waypoint = _value(target, "targety")
    _, target_raw = _owner_state(ship_groups, turn=before_turn, ship_id=target_id)
    snapshot_fuel = _intish(target_raw.get("neutronium")) if target_raw is not None else None

    target_engine_count = None
    if target_hull is not None and target_hull in specs.hulls:
        target_engine_count = specs.hulls[target_hull].engine_count

    snapshot_break, snapshot_reason = _target_breaks_tow(
        tower_hull_id=tower_hull,
        tower_warp=tower_warp,
        target_hull_id=target_hull,
        target_engine_count=target_engine_count,
        target_fuel=snapshot_fuel,
        target_x=target_x,
        target_y=target_y,
        target_warp=target_warp,
        target_x_waypoint=target_x_waypoint,
        target_y_waypoint=target_y_waypoint,
    )

    nonfuel_proven = False
    nonfuel_reason = "inputs_unknown"
    if None not in (
        tower_hull,
        tower_warp,
        target_hull,
        target_engine_count,
        target_x,
        target_y,
        target_warp,
        target_x_waypoint,
        target_y_waypoint,
    ):
        nonfuel_proven, nonfuel_reason = _nonfuel_lock_proof(
            tower_hull_id=int(tower_hull),
            tower_warp=int(tower_warp),
            target_hull_id=int(target_hull),
            target_engine_count=int(target_engine_count),
            target_x=int(target_x),
            target_y=int(target_y),
            target_warp=int(target_warp),
            target_waypoint_x=int(target_x_waypoint),
            target_waypoint_y=int(target_y_waypoint),
        )

    waypoint_distance = None
    if None not in (target_x, target_y, target_x_waypoint, target_y_waypoint):
        waypoint_distance = hypot(
            int(target_x_waypoint) - int(target_x),
            int(target_y_waypoint) - int(target_y),
        )

    return {
        "target_engine_count": target_engine_count,
        "target_snapshot_fuel": snapshot_fuel,
        "target_waypoint_distance": round(waypoint_distance, 6) if waypoint_distance is not None else None,
        "snapshot_break": snapshot_break,
        "snapshot_break_reason": snapshot_reason,
        "nonfuel_lock_proven": nonfuel_proven,
        "nonfuel_lock_reason": nonfuel_reason,
        "phase_fuel_can_matter": (not nonfuel_proven and nonfuel_reason == "lock_depends_on_target_phase_fuel"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the exact seven-row post-Chunnel finite-fuel Tow residual for Tow-break / "
            "independent-navigation alternatives. Independent geometry includes Gravitonic speed, "
            "eligible-planet warp wells, and the existing strict no-repair damage alternative. "
            "Snapshot Four Fingers state is diagnostic only; phase fuel remains unknown."
        )
    )
    parser.add_argument("--resolution-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _resolution_cases(args.resolution_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter(remaining_input=expected)
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW BREAK / INDEPENDENT MOVEMENT AUDIT =====")
    print("resolution_log=", args.resolution_log)
    print("remaining_input=", expected)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        cache_path = PREPARED_DIR / f"game-{game_id}.pickle"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        if not cache_path.is_file():
            raise FileNotFoundError(f"{cache_path}; bounded follow-up does not rebuild caches")

        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=cache_path,
        )
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races = _race_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        game_counts: Counter[str] = Counter()

        for case in by_game[game_id]:
            totals["cases"] += 1
            game_counts["cases"] += 1
            turn = int(case["turn"])
            after_turn = turn + 1
            tower_id = int(case["tower_ship"])
            target_id = int(case["target_ship"])
            observed_raw = case.get("observed")
            if not isinstance(observed_raw, tuple) or len(observed_raw) != 2:
                raise ValueError(f"invalid observed coordinate in case: {case}")
            observed = (int(observed_raw[0]), int(observed_raw[1]))
            direction = str(case.get("direction", "unknown"))
            planets = planets_by_turn.get(turn, ())

            tower = _independent_navigation(
                entities=entities,
                ship_groups=ship_groups,
                races=races,
                planets=planets,
                before_turn=turn,
                after_turn=after_turn,
                ship_id=tower_id,
                common_destination=observed,
            )
            target = _independent_navigation(
                entities=entities,
                ship_groups=ship_groups,
                races=races,
                planets=planets,
                before_turn=turn,
                after_turn=after_turn,
                ship_id=target_id,
                common_destination=observed,
            )
            four_fingers = _four_fingers_context(
                entities=entities,
                ship_groups=ship_groups,
                specs=specs,
                before_turn=turn,
                tower_id=tower_id,
                target_id=target_id,
            )

            tower_exact = bool(tower.get("any_exact"))
            target_exact = bool(target.get("any_exact"))
            if tower_exact and target_exact:
                geometry_class = "both_independent_exact"
            elif target_exact:
                geometry_class = "target_independent_exact_only"
            elif tower_exact:
                geometry_class = "tower_independent_exact_only"
            else:
                geometry_class = "neither_independent_exact"
            totals[geometry_class] += 1
            game_counts[geometry_class] += 1

            if tower.get("ordinary_exact"):
                totals["tower_ordinary_exact"] += 1
            if target.get("ordinary_exact"):
                totals["target_ordinary_exact"] += 1
            if tower.get("damage_exact"):
                totals["tower_strict_damage_exact"] += 1
            if target.get("damage_exact"):
                totals["target_strict_damage_exact"] += 1

            snapshot_break = four_fingers["snapshot_break"]
            if snapshot_break is True:
                totals["snapshot_four_fingers_true"] += 1
                game_counts["snapshot_four_fingers_true"] += 1
            elif snapshot_break is False:
                totals["snapshot_four_fingers_false"] += 1
                game_counts["snapshot_four_fingers_false"] += 1
            else:
                totals["snapshot_four_fingers_unknown"] += 1
                game_counts["snapshot_four_fingers_unknown"] += 1

            if four_fingers["nonfuel_lock_proven"]:
                totals["nonfuel_lock_proven"] += 1
                game_counts["nonfuel_lock_proven"] += 1
            elif four_fingers["phase_fuel_can_matter"]:
                totals["lock_depends_on_target_phase_fuel"] += 1
                game_counts["lock_depends_on_target_phase_fuel"] += 1
            else:
                totals["nonfuel_lock_unresolved_other"] += 1
                game_counts["nonfuel_lock_unresolved_other"] += 1

            if target_exact and snapshot_break is True:
                totals["target_exact_with_snapshot_four_fingers"] += 1
            if tower_exact and target_exact and snapshot_break is True:
                totals["both_exact_with_snapshot_four_fingers"] += 1
            if direction == "same_line_route":
                totals["same_line_rows"] += 1
                if geometry_class == "neither_independent_exact":
                    totals["same_line_neither_independent_exact"] += 1
            elif direction == "off_route":
                totals["off_route_rows"] += 1
                if geometry_class == "neither_independent_exact":
                    totals["off_route_neither_independent_exact"] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": turn,
                        "tower_ship": tower_id,
                        "target_ship": target_id,
                        "direction": direction,
                        "observed": observed,
                        "source_refined_lead": case.get("refined_lead"),
                        "geometry_class": geometry_class,
                        "tower": tower,
                        "target": target,
                        "four_fingers": four_fingers,
                    }
                )

        print({"game": game_id, "cache_hit": cache_hit, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["cases"] != expected:
        raise AssertionError(f"case accounting mismatch: {totals['cases']} != {expected}")
    geometry_total = sum(
        totals[key]
        for key in (
            "both_independent_exact",
            "target_independent_exact_only",
            "tower_independent_exact_only",
            "neither_independent_exact",
        )
    )
    if geometry_total != expected:
        raise AssertionError(f"geometry accounting mismatch: {geometry_total} != {expected}")

    print("\n===== SUMMARY =====")
    keys = (
        "remaining_input",
        "cases",
        "same_line_rows",
        "off_route_rows",
        "both_independent_exact",
        "target_independent_exact_only",
        "tower_independent_exact_only",
        "neither_independent_exact",
        "tower_ordinary_exact",
        "target_ordinary_exact",
        "tower_strict_damage_exact",
        "target_strict_damage_exact",
        "snapshot_four_fingers_true",
        "snapshot_four_fingers_false",
        "snapshot_four_fingers_unknown",
        "nonfuel_lock_proven",
        "lock_depends_on_target_phase_fuel",
        "nonfuel_lock_unresolved_other",
        "target_exact_with_snapshot_four_fingers",
        "both_exact_with_snapshot_four_fingers",
        "same_line_neither_independent_exact",
        "off_route_neither_independent_exact",
    )
    for key in keys:
        print(f"{key}= {totals[key]}")

    print("\n===== CASES =====")
    for item in examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "Independent exactness is an alternative-explanation lead: it shows that the factual common endpoint can be reproduced from a participant's own pre-Host navigation without using Tow fuel proration. It does not by itself prove that Tow broke."
    )
    print(
        "snapshot_four_fingers_true uses factual snapshot neutronium only as supporting evidence. The separate nonfuel_lock result preserves the boundary that snapshot fuel is not automatically Tow-phase fuel."
    )
    print(
        "Rows where neither participant is independently exact remain candidates for further external-context cleanup before Tow fuel inference; same-line rows are especially valuable once Tow-break alternatives are excluded."
    )
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
