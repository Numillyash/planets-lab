from __future__ import annotations

from math import hypot
from typing import Any, Mapping

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.proration import prorate_waypoint_distance
from planets_lab.sim.normal_movement import project_toward_waypoint

from normal_mine_single_candidate_immunity_repair_audit import (
    DATABASE,
    EXPECTED_HULL,
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
    _route_metrics,
)


def _candidate(
    *,
    label: str,
    distance: float,
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
) -> dict[str, Any]:
    clamped = max(0.0, min(distance, hypot(target[0] - origin[0], target[1] - origin[1])))
    endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=clamped,
    )
    actual_distance = hypot(endpoint[0] - origin[0], endpoint[1] - origin[1])
    return {
        "label": label,
        "continuous_distance": round(clamped, 6),
        "projected_endpoint": endpoint,
        "projected_distance": round(actual_distance, 6),
        "matches_observed_endpoint": endpoint == observed,
    }


def _prorated_distance(requested: float, *, fuel_available: int, fuel_required: int) -> float:
    if requested <= 0.0:
        return 0.0
    if fuel_required <= 0 or fuel_available >= fuel_required:
        return requested
    return prorate_waypoint_distance(
        requested_distance=requested,
        fuel_available=fuel_available,
        fuel_required=fuel_required,
    ).distance


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

    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])
    owner_id, before_owner = _owner_record(ship_groups.get((before_turn, SHIP_ID), ()))
    after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, SHIP_ID), ()))
    if owner_id != EXPECTED_OWNER or before_owner is None:
        raise SystemExit(f"owner guard failed: expected {EXPECTED_OWNER}, got {owner_id}")
    if after_owner_id != owner_id or after_owner is None:
        raise SystemExit("after-owner identity unavailable")

    sample = _sample(row)
    if sample.hull_id != EXPECTED_HULL:
        raise SystemExit(f"hull guard failed: expected {EXPECTED_HULL}, got {sample.hull_id}")

    topology = effective_sphere_topology(
        game_id=GAME_ID,
        topology=extract_map_topology(archive_data),
    )
    effective_sample = sample
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        effective_sample = sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )

    origin = (effective_sample.x, effective_sample.y)
    target = (effective_sample.target_x, effective_sample.target_y)
    observed = (effective_sample.next_x, effective_sample.next_y)
    target_vector = _vector(origin, target, topology)
    observed_vector = _vector(origin, observed, topology)
    target_distance = hypot(*target_vector)
    observed_distance = hypot(*observed_vector)
    max_distance = effective_sample.warp * effective_sample.warp * (2 if effective_sample.gravitonic else 1)
    planned_distance = min(target_distance, float(max_distance))
    mine_slowed_distance = max(0.0, planned_distance - 10.0)

    before_raw = before_owner.raw
    after_raw = after_owner.raw
    engine_id = _intish(before_raw.get("engineid"))
    fuel_available = _intish(before_raw.get("neutronium"))
    total_mass = _intish(before_raw.get("mass"))
    damage_before = _intish(before_raw.get("damage"))
    fuel_after = _intish(after_raw.get("neutronium"))
    mission_numeric = _intish(before_raw.get("mission"))
    mission1target = _intish(before_raw.get("mission1target", before_raw.get("mission1_target_id")))

    if engine_id is None or fuel_available is None or total_mass is None:
        raise SystemExit(
            f"fuel inputs unavailable: engine_id={engine_id} fuel={fuel_available} mass={total_mass}"
        )

    from planets_lab.corpus.movement_fuel_context import extract_static_specs

    specs = extract_static_specs(archive_data)
    engine = specs.engines.get(engine_id)
    if engine is None:
        raise SystemExit(f"missing engine spec {engine_id}")
    fuel_factor = engine.fuel_factor(effective_sample.warp)

    def fuel_required(distance: float) -> int:
        return movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=total_mass,
            distance_traveled=distance,
            max_distance_per_turn=max_distance,
        )

    required_planned = fuel_required(planned_distance)
    required_mine_slowed = fuel_required(mine_slowed_distance)
    required_observed = fuel_required(observed_distance)

    fuel_only_distance = _prorated_distance(
        planned_distance,
        fuel_available=fuel_available,
        fuel_required=required_planned,
    )
    fuel_then_minus10 = max(0.0, fuel_only_distance - 10.0)
    minus10_then_recompute = _prorated_distance(
        mine_slowed_distance,
        fuel_available=fuel_available,
        fuel_required=required_mine_slowed,
    )
    original_ratio = (
        min(1.0, fuel_available / required_planned)
        if required_planned > 0
        else 1.0
    )
    minus10_then_original_ratio = mine_slowed_distance * original_ratio

    payload = _raw_turn_payload(archive_data, turn=after_turn, player_id=owner_id)
    reports = [
        excerpt
        for message in _messages(payload)
        if (excerpt := _mine_report_excerpt(message, archive_turn=after_turn)) is not None
    ]
    hit_progress = None
    hit_cross_track = None
    hit_point = None
    if len(reports) == 1:
        event_x = reports[0].get("event_x")
        event_y = reports[0].get("event_y")
        if isinstance(event_x, int) and isinstance(event_y, int):
            hit_point = (event_x, event_y)
            metrics = _route_metrics(
                origin=origin,
                route_vector=(float(target_vector[0]), float(target_vector[1])),
                point=hit_point,
                topology=topology,
            )
            if metrics is not None:
                hit_progress = metrics["route_progress"]
                hit_cross_track = metrics["cross_track"]

    segmented: dict[str, Any] = {}
    if hit_progress is not None:
        remaining_to_planned = max(0.0, planned_distance - hit_progress)
        remaining_after_mine_loss = max(0.0, remaining_to_planned - 10.0)
        fuel_to_hit = fuel_required(hit_progress)
        remaining_fuel_after_hit_probe = max(0, fuel_available - fuel_to_hit)
        required_remaining = fuel_required(remaining_to_planned)
        required_remaining_after_loss = fuel_required(remaining_after_mine_loss)
        segmented_remaining_no_loss = _prorated_distance(
            remaining_to_planned,
            fuel_available=remaining_fuel_after_hit_probe,
            fuel_required=required_remaining,
        )
        segmented_remaining_after_loss = _prorated_distance(
            remaining_after_mine_loss,
            fuel_available=remaining_fuel_after_hit_probe,
            fuel_required=required_remaining_after_loss,
        )
        segmented = {
            "hit_progress": round(hit_progress, 6),
            "hit_cross_track": round(hit_cross_track or 0.0, 6),
            "remaining_to_planned": round(remaining_to_planned, 6),
            "remaining_after_10ly_loss": round(remaining_after_mine_loss, 6),
            "fuel_required_to_hit_probe": fuel_to_hit,
            "remaining_fuel_after_hit_probe": remaining_fuel_after_hit_probe,
            "fuel_required_remaining_probe": required_remaining,
            "fuel_required_remaining_after_loss_probe": required_remaining_after_loss,
            "segmented_total_no_loss": round(hit_progress + segmented_remaining_no_loss, 6),
            "segmented_total_after_loss": round(hit_progress + segmented_remaining_after_loss, 6),
        }

    print("===== NORMAL-MINE SINGLE CANDIDATE COMPOUND FUEL AUDIT =====")
    print("game=", GAME_ID)
    print("turn=", before_turn)
    print("ship=", SHIP_ID)
    print("prepared_cache_hit=", cache_hit)
    print("owner_id=", owner_id)
    print("hull_id=", effective_sample.hull_id)
    print("requested_warp=", effective_sample.warp)
    print("mission_numeric=", mission_numeric)
    print("mission1target=", mission1target)
    print("origin=", origin)
    print("target=", target)
    print("observed_endpoint=", observed)
    print("planned_distance=", round(planned_distance, 6))
    print("observed_distance=", round(observed_distance, 6))
    print("mine_only_distance_minus_10=", round(mine_slowed_distance, 6))

    print("\n===== SUBMITTED FUEL STATE =====")
    print("engine_id=", engine_id)
    print("engine_tech=", engine.tech_level)
    print("fuel_factor_at_requested_warp=", fuel_factor)
    print("total_mass=", total_mass)
    print("fuel_available_before=", fuel_available)
    print("fuel_observed_after=", fuel_after)
    print("damage_before=", damage_before)
    print("fuel_required_planned=", required_planned)
    print("fuel_required_mine_slowed=", required_mine_slowed)
    print("fuel_required_observed_distance=", required_observed)
    print("fuel_insufficient_for_planned=", fuel_available < required_planned)
    print("fuel_insufficient_for_mine_slowed=", fuel_available < required_mine_slowed)
    print("fuel_sufficient_for_observed_distance=", fuel_available >= required_observed)

    print("\n===== ORDERING CANDIDATES =====")
    candidates = [
        _candidate(
            label="fuel_only_original_waypoint",
            distance=fuel_only_distance,
            origin=origin,
            target=target,
            observed=observed,
        ),
        _candidate(
            label="mine_only_minus_10",
            distance=mine_slowed_distance,
            origin=origin,
            target=target,
            observed=observed,
        ),
        _candidate(
            label="fuel_proration_then_minus_10",
            distance=fuel_then_minus10,
            origin=origin,
            target=target,
            observed=observed,
        ),
        _candidate(
            label="minus_10_then_recompute_fuel_requirement",
            distance=minus10_then_recompute,
            origin=origin,
            target=target,
            observed=observed,
        ),
        _candidate(
            label="minus_10_then_original_fuel_ratio",
            distance=minus10_then_original_ratio,
            origin=origin,
            target=target,
            observed=observed,
        ),
    ]
    for candidate in candidates:
        print(candidate)

    print("\n===== IMPACT-SEGMENT FUEL PROBES =====")
    print("mine_report_count=", len(reports))
    print("impact_point=", hit_point)
    print(segmented if segmented else None)
    if segmented:
        for label, distance in (
            ("segmented_fuel_no_mine_loss", segmented["segmented_total_no_loss"]),
            ("segmented_fuel_with_10ly_loss", segmented["segmented_total_after_loss"]),
        ):
            print(_candidate(
                label=label,
                distance=float(distance),
                origin=origin,
                target=target,
                observed=observed,
            ))

    print("\n===== SUMMARY =====")
    print("any_simple_ordering_exact_endpoint=", any(item["matches_observed_endpoint"] for item in candidates))
    print("observed_minus_hit_progress=", round(observed_distance - hit_progress, 6) if hit_progress is not None else None)
    print("planned_minus_observed=", round(planned_distance - observed_distance, 6))
    print("mine_only_remaining_discrepancy=", round(mine_slowed_distance - observed_distance, 6))

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This is an evidence-only compound-order audit. It does not change the verified fuel-proration rule, mine "
        "labels, corpus schemas or accounting. Submitted before-turn fuel/mass/engine state is causal input; after-turn "
        "fuel is observational only. The segmented probes deliberately test possible orderings and must not be treated "
        "as Host semantics unless independently supported by additional transitions. Numeric mission fields are printed "
        "without assigning semantic names."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
