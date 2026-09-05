from __future__ import annotations

from math import floor, hypot

from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim.normal_movement import project_toward_waypoint

from normal_mine_single_candidate_immunity_repair_audit import (
    BEFORE_TURN,
    DATABASE,
    EXPECTED_OWNER,
    GAME_ID,
    PREPARED_DIR,
    RAW_DIR,
    SHIP_ID,
    _load_row,
    _sample,
)
from normal_mine_single_candidate_post_hit_motion_audit import (
    _messages,
    _mine_report_excerpt,
    _raw_turn_payload,
)


def _round_nearest_nonnegative(value: float) -> int:
    return floor(value + 0.5)


def _major_axis_clicks(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
) -> list[tuple[int, tuple[int, int]]]:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    if abs_dx == 0 and abs_dy == 0:
        return [(0, origin)]

    result: list[tuple[int, tuple[int, int]]] = []
    if abs_dx >= abs_dy:
        major = abs_dx
        minor = abs_dy
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        for click in range(major + 1):
            minor_move = _round_nearest_nonnegative(click * minor / major) if major else 0
            result.append((click, (origin[0] + sx * click, origin[1] + sy * minor_move)))
    else:
        major = abs_dy
        minor = abs_dx
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        for click in range(major + 1):
            minor_move = _round_nearest_nonnegative(click * minor / major) if major else 0
            result.append((click, (origin[0] + sx * minor_move, origin[1] + sy * click)))
    return result


def _click_for_point(
    clicks: list[tuple[int, tuple[int, int]]],
    point: tuple[int, int],
) -> int | None:
    matches = [click for click, candidate in clicks if candidate == point]
    if len(matches) == 1:
        return matches[0]
    return None


def _nearest_planets(
    *,
    point: tuple[int, int],
    planets: tuple[tuple[int, int, int], ...],
    limit: int = 8,
) -> list[dict[str, object]]:
    ranked = sorted(
        (
            hypot(px - point[0], py - point[1]),
            planet_id,
            px,
            py,
        )
        for planet_id, px, py in planets
    )
    return [
        {
            "planet_id": planet_id,
            "planet_xy": (px, py),
            "distance": round(distance, 6),
        }
        for distance, planet_id, px, py in ranked[:limit]
    ]


def _penalty_matches(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    planned_distance: float,
    observed: tuple[int, int],
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for tenth in range(0, 401):
        penalty = tenth / 10.0
        distance = max(0.0, planned_distance - penalty)
        endpoint = project_toward_waypoint(
            x=origin[0],
            y=origin[1],
            target_x=target[0],
            target_y=target[1],
            distance=distance,
        )
        if endpoint == observed:
            matches.append({"penalty": penalty, "distance": round(distance, 6)})
    return matches


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    row = _load_row()
    archive_path = RAW_DIR / f"game-{GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=GAME_ID,
        cache_path=PREPARED_DIR / f"game-{GAME_ID}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    owner_id, before_owner = _owner_record(ship_groups.get((BEFORE_TURN, SHIP_ID), ()))
    after_turn = int(row["after_archive_turn"])
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, SHIP_ID), ()))
    if owner_id != EXPECTED_OWNER or before_owner is None:
        raise SystemExit(f"before owner guard failed: {owner_id}")
    if after_owner_id != owner_id or after_owner is None:
        raise SystemExit("after owner identity unavailable")

    raw_topology = extract_map_topology(archive_data)
    topology = effective_sphere_topology(game_id=GAME_ID, topology=raw_topology)
    sample = _sample(row)
    effective_sample = sample
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        effective_sample = sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )

    origin = (effective_sample.x, effective_sample.y)
    target = (effective_sample.target_x, effective_sample.target_y)
    observed = effective_sample.observed_destination
    target_vector = _vector(origin, target, topology)
    target_distance = hypot(*target_vector)
    planned_distance = min(target_distance, float(row["nominal_max_distance"] or target_distance))
    mine_only_distance = max(0.0, planned_distance - 10.0)
    mine_only_endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=mine_only_distance,
    )

    after_payload = _raw_turn_payload(archive_data, turn=after_turn, player_id=owner_id)
    reports = [
        excerpt
        for message in _messages(after_payload)
        if (excerpt := _mine_report_excerpt(message, archive_turn=after_turn)) is not None
    ]
    report_points = [
        (int(report["event_x"]), int(report["event_y"]))
        for report in reports
        if isinstance(report.get("event_x"), int) and isinstance(report.get("event_y"), int)
    ]

    clicks = _major_axis_clicks(origin=origin, target=target)
    impact_point = report_points[0] if len(report_points) == 1 else None
    impact_click = _click_for_point(clicks, impact_point) if impact_point is not None else None
    observed_click = _click_for_point(clicks, observed)
    mine_only_click = _click_for_point(clicks, mine_only_endpoint)
    target_click = _click_for_point(clicks, target)

    entities = _entity_map(prepared.snapshots)
    planets_by_turn = _planet_tuples_by_turn(entities)
    before_planets = planets_by_turn.get(BEFORE_TURN, ())
    after_planets = planets_by_turn.get(after_turn, ())

    before_raw = before_owner.raw
    after_raw = after_owner.raw

    print("===== NORMAL-MINE SINGLE CANDIDATE STEP / STATE / WARP-WELL AUDIT =====")
    print("game=", GAME_ID)
    print("turn=", BEFORE_TURN)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("origin=", origin)
    print("target=", target)
    print("observed_endpoint=", observed)
    print("planned_distance=", round(planned_distance, 6))
    print("mine_only_distance_minus_10=", round(mine_only_distance, 6))
    print("mine_only_endpoint=", mine_only_endpoint)

    print("\n===== POST-TURN NAVIGATION STATE =====")
    print("before_warp=", _intish(before_raw.get("warp")))
    print("after_warp=", _intish(after_raw.get("warp")))
    print("before_target=", (
        _intish(before_raw.get("targetx", before_raw.get("waypointx"))),
        _intish(before_raw.get("targety", before_raw.get("waypointy"))),
    ))
    print("after_target=", (
        _intish(after_raw.get("targetx", after_raw.get("waypointx"))),
        _intish(after_raw.get("targety", after_raw.get("waypointy"))),
    ))
    print("after_target_equals_observed=", (
        _intish(after_raw.get("targetx", after_raw.get("waypointx"))),
        _intish(after_raw.get("targety", after_raw.get("waypointy"))),
    ) == observed)
    print("before_neutronium=", _intish(before_raw.get("neutronium")))
    print("after_neutronium=", _intish(after_raw.get("neutronium")))
    print("before_damage=", _intish(before_raw.get("damage")))
    print("after_damage=", _intish(after_raw.get("damage")))
    print("before_supplies=", _intish(before_raw.get("supplies")))
    print("after_supplies=", _intish(after_raw.get("supplies")))

    print("\n===== EXACT MAJOR-AXIS CLICK RECONSTRUCTION =====")
    print("route_major_click_count=", target_click)
    print("impact_point=", impact_point)
    print("impact_click=", impact_click)
    print("observed_click=", observed_click)
    print("mine_only_click=", mine_only_click)
    print("target_click=", target_click)
    print("clicks_after_impact_to_observed=", observed_click - impact_click if impact_click is not None and observed_click is not None else None)
    print("clicks_removed_vs_target=", target_click - observed_click if target_click is not None and observed_click is not None else None)
    print("clicks_removed_by_scalar_minus_10=", target_click - mine_only_click if target_click is not None and mine_only_click is not None else None)
    if impact_click is not None:
        lo = max(0, impact_click - 3)
        hi = min(len(clicks), impact_click + 9)
        print("click_window_around_impact=", clicks[lo:hi])
    if observed_click is not None:
        lo = max(0, observed_click - 3)
        hi = min(len(clicks), observed_click + 4)
        print("click_window_around_observed=", clicks[lo:hi])

    print("\n===== SCALAR PENALTY ENDPOINT SEARCH =====")
    exact_penalties = _penalty_matches(
        origin=origin,
        target=target,
        planned_distance=planned_distance,
        observed=observed,
    )
    print("penalty_values_0_to_40_step_0.1_that_match_observed=", exact_penalties)

    print("\n===== WARP-WELL / PLANET PROXIMITY =====")
    for archive_turn, planets in ((BEFORE_TURN, before_planets), (after_turn, after_planets)):
        print(f"archive_turn={archive_turn} eligible_planets={len(planets)}")
        for label, endpoint in (
            ("regular", target),
            ("mine_only", mine_only_endpoint),
            ("observed", observed),
        ):
            well, ambiguous = _warp_well_destination(
                sample=effective_sample,
                endpoint=endpoint,
                planets=planets,
            )
            print({
                "label": label,
                "endpoint": endpoint,
                "warp_well_destination": well,
                "warp_well_ambiguous": ambiguous,
                "nearest_planets": _nearest_planets(point=endpoint, planets=planets, limit=5),
            })

    print("\n===== SUMMARY =====")
    print("single_mine_report=", len(reports) == 1)
    print("impact_and_observed_are_exact_route_clicks=", impact_click is not None and observed_click is not None)
    print("post_impact_major_clicks=", observed_click - impact_click if impact_click is not None and observed_click is not None else None)
    print("scalar_minus_10_matches_observed=", mine_only_endpoint == observed)
    print("observed_is_planet_before_turn=", any((px, py) == observed for _, px, py in before_planets))
    print("observed_is_planet_after_turn=", any((px, py) == observed for _, px, py in after_planets))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic is evidence-only. The major-axis click sequence reproduces the already validated Host-style "
        "integer route geometry but does not assume an undocumented mine-hit counter mutation. Warp-well checks reuse "
        "the production eligibility/settings logic. Post-turn warp/waypoint state is observational output and must not "
        "be treated as causal ordering without an independent differential."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
