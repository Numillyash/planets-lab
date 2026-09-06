from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from math import hypot
from typing import Any

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.proration import prorate_waypoint_distance
from planets_lab.sim.normal_movement import project_toward_waypoint

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_reported_excess_shortening_residual_audit import (
    DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    TARGET_KEY,
    _effective_sample,
    _load_rows,
    _route_metrics,
    _same_line_metrics,
    _sample,
)
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _candidate(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    distance: float,
    observed: tuple[int, int],
    observed_distance: float,
) -> dict[str, Any]:
    distance = max(0.0, float(distance))
    endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=distance,
    )
    return {
        "distance": round(distance, 6),
        "error": round(observed_distance - distance, 6),
        "within_1_5": abs(observed_distance - distance) <= 1.5,
        "endpoint": endpoint,
        "endpoint_exact": endpoint == observed,
    }


def _prorated_distance(*, requested_distance: float, fuel_available: int, fuel_required: int) -> float:
    if fuel_required <= 0 or fuel_available >= fuel_required:
        return requested_distance
    return prorate_waypoint_distance(
        requested_distance=requested_distance,
        fuel_available=fuel_available,
        fuel_required=fuel_required,
    ).distance


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    print("===== NORMAL-MINE EXCESS FAMILY FUEL-COMPOUND AUDIT =====")
    print("source_rows=", len(rows))

    totals: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    strict_items: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        payload_cache: dict[tuple[int, int], Mapping[str, Any]] = {}
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])

            owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or before_owner is None:
                continue
            if after_owner_id != owner_id or after_owner is None:
                continue

            payload_key = (after_turn, owner_id)
            if payload_key not in payload_cache:
                payload_cache[payload_key] = _raw_turn_payload(
                    archive_data,
                    turn=after_turn,
                    player_id=owner_id,
                )
            reports = [
                excerpt
                for message in _messages(payload_cache[payload_key])
                if (excerpt := _critical_mine_excerpt(message, ship_id=ship_id)) is not None
            ]
            if len(reports) != 1 or reports[0].get("body_has_web_token") is True:
                continue

            sample = _effective_sample(_sample(row), topology)
            hull_id = sample.hull_id
            hull = mine_context.specs.hulls.get(int(hull_id)) if hull_id is not None else None
            if hull is None or hull.tech_level >= 7:
                continue

            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_vector = _vector(origin, target, topology)
            observed_vector = _vector(origin, observed, topology)
            target_distance = hypot(*target_vector)
            observed_distance = hypot(*observed_vector)
            nominal_distance = float(row["nominal_max_distance"] or 0.0)
            regular_distance = min(target_distance, nominal_distance)
            observed_cross, observed_progress = _same_line_metrics(
                origin=origin,
                target=target,
                observed=observed,
                topology=topology,
            )

            event_x = reports[0].get("event_x")
            event_y = reports[0].get("event_y")
            if not isinstance(event_x, int) or not isinstance(event_y, int):
                continue
            impact = (event_x, event_y)
            impact_metrics = _route_metrics(
                origin=origin,
                target=target,
                point=impact,
                topology=topology,
            )
            if (
                impact_metrics is None
                or impact_metrics["cross_track"] > 1.5
                or regular_distance - impact_metrics["progress"] <= 10.0
                or observed_cross is None
                or observed_cross > 1.5
                or observed_progress is None
                or observed_progress <= 0.0
            ):
                continue

            totals["strict_rows"] += 1
            expected_minus10 = max(0.0, regular_distance - 10.0)
            excess = expected_minus10 - observed_distance
            if excess > 1.5:
                totals["excess_rows"] += 1

            before_raw = before_owner.raw
            after_raw = after_owner.raw
            engine_id = _intish(before_raw.get("engineid"))
            fuel_before = _intish(before_raw.get("neutronium"))
            fuel_after = _intish(after_raw.get("neutronium"))
            mass_before = _intish(before_raw.get("mass"))

            engine = mine_context.specs.engines.get(engine_id) if engine_id is not None else None
            if engine is None or fuel_before is None or fuel_before < 0 or mass_before is None or mass_before < 0:
                totals["fuel_inputs_unavailable"] += 1
                continue
            totals["fuel_inputs_ready"] += 1

            fuel_factor = engine.fuel_factor(sample.warp)
            max_distance_per_turn = sample.warp * sample.warp * (2 if sample.gravitonic else 1)
            required_regular = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=mass_before,
                distance_traveled=regular_distance,
                max_distance_per_turn=max_distance_per_turn,
            )
            required_minus10 = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=mass_before,
                distance_traveled=expected_minus10,
                max_distance_per_turn=max_distance_per_turn,
            )
            required_observed = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=mass_before,
                distance_traveled=observed_distance,
                max_distance_per_turn=max_distance_per_turn,
            )

            insufficient_regular = required_regular > 0 and fuel_before < required_regular
            insufficient_minus10 = required_minus10 > 0 and fuel_before < required_minus10
            if insufficient_regular:
                totals["fuel_insufficient_regular"] += 1
                if excess > 1.5:
                    totals["excess_and_fuel_insufficient_regular"] += 1
            else:
                totals["fuel_sufficient_regular"] += 1
                if excess > 1.5:
                    totals["excess_and_fuel_sufficient_regular"] += 1
            if insufficient_minus10:
                totals["fuel_insufficient_minus10"] += 1

            candidates: dict[str, dict[str, Any]] = {}
            candidates["documented_minus10"] = _candidate(
                origin=origin,
                target=target,
                distance=expected_minus10,
                observed=observed,
                observed_distance=observed_distance,
            )

            # Candidate A: documented Nu fuel proration happens first, then a single normal-mine
            # slowdown is applied only if >10 LY remained at the recorded impact.
            fuel_first_distance = _prorated_distance(
                requested_distance=regular_distance,
                fuel_available=fuel_before,
                fuel_required=required_regular,
            )
            fuel_then_minus10_distance = fuel_first_distance
            if impact_metrics["progress"] <= fuel_first_distance + 1.5 and fuel_first_distance - impact_metrics["progress"] > 10.0:
                fuel_then_minus10_distance = max(0.0, fuel_first_distance - 10.0)
            candidates["fuel_then_minus10"] = _candidate(
                origin=origin,
                target=target,
                distance=fuel_then_minus10_distance,
                observed=observed,
                observed_distance=observed_distance,
            )

            # Candidate B: mine-shortened waypoint is established first, then fuel is
            # recomputed/prorated against that shortened requested distance.
            mine_then_fuel_distance = _prorated_distance(
                requested_distance=expected_minus10,
                fuel_available=fuel_before,
                fuel_required=required_minus10,
            )
            candidates["minus10_then_fuel"] = _candidate(
                origin=origin,
                target=target,
                distance=mine_then_fuel_distance,
                observed=observed,
                observed_distance=observed_distance,
            )

            # Candidate C: preserve the documented full-route fuel ratio but apply it
            # to the mine-shortened waypoint. This intentionally tests a distinct Host
            # ordering without asserting it as semantics.
            if required_regular > 0 and fuel_before < required_regular:
                full_ratio = fuel_before / required_regular
                candidates["minus10_then_full_route_fuel_ratio"] = _candidate(
                    origin=origin,
                    target=target,
                    distance=expected_minus10 * full_ratio,
                    observed=observed,
                    observed_distance=observed_distance,
                )

            # Candidate D: discrete Host major-axis -10 clicks, then fuel sufficiency is
            # evaluated for that resulting geometric distance.
            click_minus10_distance = None
            if topology.sphere is not True:
                clicks = _major_axis_clicks(origin=origin, target=target)
                regular_endpoint = project_toward_waypoint(
                    x=origin[0], y=origin[1], target_x=target[0], target_y=target[1], distance=regular_distance
                )
                regular_click = _click_for_point(clicks, regular_endpoint)
                if regular_click is not None:
                    candidate_click = max(0, regular_click - 10)
                    click_point = next((point for click, point in clicks if click == candidate_click), origin)
                    click_minus10_distance = hypot(
                        *_vector(origin, click_point, topology)
                    )
                    click_required = movement_fuel_use(
                        fuel_factor=fuel_factor,
                        total_mass=mass_before,
                        distance_traveled=click_minus10_distance,
                        max_distance_per_turn=max_distance_per_turn,
                    )
                    click_fuel_distance = _prorated_distance(
                        requested_distance=click_minus10_distance,
                        fuel_available=fuel_before,
                        fuel_required=click_required,
                    )
                    candidates["minus10_clicks_then_fuel"] = _candidate(
                        origin=origin,
                        target=target,
                        distance=click_fuel_distance,
                        observed=observed,
                        observed_distance=observed_distance,
                    )

            for name, candidate in candidates.items():
                if candidate["within_1_5"]:
                    model_counts[f"{name}_within_1_5"] += 1
                if candidate["endpoint_exact"]:
                    model_counts[f"{name}_endpoint_exact"] += 1

            item = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "owner_id": owner_id,
                "hull_id": hull_id,
                "warp": sample.warp,
                "regular_distance": round(regular_distance, 6),
                "impact_progress": round(float(impact_metrics["progress"]), 6),
                "observed_distance": round(observed_distance, 6),
                "excess_beyond_minus10": round(excess, 6),
                "engine_id": engine_id,
                "engine_tech": engine.tech_level,
                "fuel_factor": fuel_factor,
                "mass_before": mass_before,
                "fuel_before": fuel_before,
                "fuel_after": fuel_after,
                "fuel_delta": (fuel_before - fuel_after) if fuel_after is not None else None,
                "required_regular": required_regular,
                "required_minus10": required_minus10,
                "required_observed": required_observed,
                "fuel_insufficient_regular": insufficient_regular,
                "fuel_insufficient_minus10": insufficient_minus10,
                "click_minus10_distance": round(click_minus10_distance, 6) if click_minus10_distance is not None else None,
                "candidates": candidates,
            }
            strict_items.append(item)

    print("\n===== SUMMARY =====")
    for key in (
        "strict_rows",
        "excess_rows",
        "fuel_inputs_ready",
        "fuel_inputs_unavailable",
        "fuel_insufficient_regular",
        "fuel_sufficient_regular",
        "fuel_insufficient_minus10",
        "excess_and_fuel_insufficient_regular",
        "excess_and_fuel_sufficient_regular",
    ):
        print(f"{key}=", totals[key])

    print("\n===== COMPOUND MODEL SUMMARY =====")
    for key in sorted(model_counts):
        print(f"{key}=", model_counts[key])

    print("\n===== FUEL-LIMITED STRICT ROWS =====")
    for item in strict_items:
        if item["fuel_insufficient_regular"]:
            print(item)

    print("\n===== EXCESS ROWS WITH FULL-ROUTE FUEL SUFFICIENT =====")
    for item in strict_items:
        if item["excess_beyond_minus10"] > 1.5 and not item["fuel_insufficient_regular"]:
            print(item)

    print("\n===== TARGET =====")
    target = next(
        (item for item in strict_items if (item["game_id"], item["before_turn"], item["ship_id"]) == TARGET_KEY),
        None,
    )
    print(target)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic does not reinterpret post-fuel-proration residual as fuel-free evidence. It tests whether "
        "strict single-normal-mine-report rows still have enough pre-turn neutronium for the regular route and for "
        "the documented one-hit-shortened route, then evaluates several explicit mine/fuel orderings. Pure fuel "
        "proration already classified upstream is not relabeled here; these are compound hypotheses only. No corpus "
        "labels, schemas, accounting, or production mechanics are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
