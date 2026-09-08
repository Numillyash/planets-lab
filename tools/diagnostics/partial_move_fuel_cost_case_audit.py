from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from math import hypot
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

from planets_lab.corpus.movement_chunnel_context import extract_stable_chunnel_abilities
from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.mass import ship_movement_mass
from planets_lab.rules.movement import max_nominal_distance
from planets_lab.sim.normal_movement import project_toward_waypoint
from planets_lab.validation.movement_geometry import MovementSample

from damage_limited_warp_residual_audit import _max_warp_from_damage, _race_map
from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_external_confounder_audit import (
    _effective_damage_sample,
    _targeted_chunnel_matches,
)
from intercept_fuel_historical_differential_audit import (
    DEFAULT_DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    TOW_MISSION_ID,
    _mass_state_complete,
    _mission,
    _settings_unlimited_fuel,
    _snapshot_by_owner,
    _target_id,
)
from intercept_fuel_phase_state_audit import (
    _compress_int_ranges,
    _friendly_code_class,
    _mechanical_order_fields,
    _owner_snapshot_raw_planets,
    _owner_snapshot_raw_ships,
    _raw_int,
    _transfer_neutronium,
    _transfer_target,
)
from mine_hit_hostorder_differential_audit import _owner_states
from partial_move_fuel_cost_move_most_audit import _candidate_endpoint


def _predicted_post_fuel(phase_fuel: int, fuel_required: int) -> int:
    if fuel_required <= 0:
        return phase_fuel
    return max(0, phase_fuel - fuel_required)


def _phase_cost_basis_scan(
    ship: Any,
    specs: Any,
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    gravitonic: bool,
    scan_cap: int,
) -> dict[str, Any]:
    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    nominal_endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=max_distance,
    )
    projected_distance = hypot(
        nominal_endpoint[0] - origin[0],
        nominal_endpoint[1] - origin[1],
    )

    projected_exact_fuels: list[int] = []
    nominal_exact_fuels: list[int] = []
    projected_exact_post: list[int] = []
    nominal_exact_post: list[int] = []
    both_exact_fuels: list[int] = []
    projected_only_fuels: list[int] = []
    nominal_only_fuels: list[int] = []
    exact_details: list[dict[str, Any]] = []

    for phase_fuel in range(scan_cap + 1):
        candidate = deepcopy(ship)
        candidate.cargo.neutronium = phase_fuel
        if candidate.engine_id is None or candidate.engine_id not in specs.engines:
            continue
        movement_mass = ship_movement_mass(candidate, specs)
        fuel_factor = specs.engines[candidate.engine_id].fuel_factor(warp)
        required_projected = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=movement_mass,
            distance_traveled=projected_distance,
            max_distance_per_turn=max_distance,
        )
        required_nominal = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=movement_mass,
            distance_traveled=float(max_distance),
            max_distance_per_turn=max_distance,
        )
        projected_endpoint = _candidate_endpoint(
            origin=origin,
            target=target,
            requested_distance=float(max_distance),
            fuel_available=phase_fuel,
            fuel_required=required_projected,
        )
        nominal_endpoint_candidate = _candidate_endpoint(
            origin=origin,
            target=target,
            requested_distance=float(max_distance),
            fuel_available=phase_fuel,
            fuel_required=required_nominal,
        )
        projected_exact = projected_endpoint == observed
        nominal_exact = nominal_endpoint_candidate == observed

        if projected_exact:
            projected_exact_fuels.append(phase_fuel)
            projected_exact_post.append(
                _predicted_post_fuel(phase_fuel, required_projected)
            )
        if nominal_exact:
            nominal_exact_fuels.append(phase_fuel)
            nominal_exact_post.append(
                _predicted_post_fuel(phase_fuel, required_nominal)
            )
        if projected_exact and nominal_exact:
            both_exact_fuels.append(phase_fuel)
        elif projected_exact:
            projected_only_fuels.append(phase_fuel)
        elif nominal_exact:
            nominal_only_fuels.append(phase_fuel)

        if projected_exact or nominal_exact:
            exact_details.append(
                {
                    "phase_fuel": phase_fuel,
                    "movement_mass": movement_mass,
                    "required_projected": required_projected,
                    "required_nominal": required_nominal,
                    "projected_endpoint": projected_endpoint,
                    "nominal_endpoint": nominal_endpoint_candidate,
                    "projected_post_fuel": _predicted_post_fuel(
                        phase_fuel, required_projected
                    ),
                    "nominal_post_fuel": _predicted_post_fuel(
                        phase_fuel, required_nominal
                    ),
                }
            )

    return {
        "scan_cap": scan_cap,
        "max_distance": max_distance,
        "nominal_one_turn_endpoint": nominal_endpoint,
        "rasterized_one_turn_distance": round(projected_distance, 6),
        "projected_exact_phase_fuel_ranges": _compress_int_ranges(projected_exact_fuels),
        "nominal_exact_phase_fuel_ranges": _compress_int_ranges(nominal_exact_fuels),
        "both_exact_phase_fuel_ranges": _compress_int_ranges(both_exact_fuels),
        "projected_only_phase_fuel_ranges": _compress_int_ranges(projected_only_fuels),
        "nominal_only_phase_fuel_ranges": _compress_int_ranges(nominal_only_fuels),
        "projected_exact_post_fuel_ranges": _compress_int_ranges(projected_exact_post),
        "nominal_exact_post_fuel_ranges": _compress_int_ranges(nominal_exact_post),
        "exact_phase_details": tuple(exact_details),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Targeted forensic audit for a true-partial Move Most fuel-cost discriminator. "
            "Recomputes movement mass across hypothetical phase-fuel values and checks known "
            "external movement confounders for the exact transition."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--game", type=int, default=360690)
    parser.add_argument("--turn", type=int, default=164)
    parser.add_argument("--ship", type=int, default=41)
    parser.add_argument("--fuel-scan-cap", type=int, default=5000)
    args = parser.parse_args()
    if args.fuel_scan_cap < 0:
        parser.error("--fuel-scan-cap must be non-negative")

    print("===== PARTIAL MOVE MOST FUEL COST CASE AUDIT =====", flush=True)
    print(f"case game={args.game} turn={args.turn} ship={args.ship}", flush=True)

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                before_embedded_turn,
                ship_id,
                hull_id,
                warp,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y
            FROM movement_transitions
            WHERE game_id = ?
              AND before_archive_turn = ?
              AND ship_id = ?
              AND readiness_status = 'ready'
              AND intent_class = 'move_most_candidate'
            ORDER BY after_archive_turn
            """,
            [args.game, args.turn, args.ship],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        print("status=case_not_found")
        return 2
    if len(rows) != 1:
        print(f"status=ambiguous_transition rows={len(rows)}")
        return 2

    (
        game_id,
        before_turn,
        after_turn,
        embedded_turn,
        ship_id,
        hull_id,
        warp,
        x,
        y,
        next_x,
        next_y,
        target_x,
        target_y,
    ) = rows[0]
    game_id = int(game_id)
    before_turn = int(before_turn)
    after_turn = int(after_turn)
    embedded_turn = int(embedded_turn)
    ship_id = int(ship_id)
    hull_id = int(hull_id)
    warp = int(warp)
    origin = (int(x), int(y))
    observed = (int(next_x), int(next_y))
    target = (int(target_x), int(target_y))

    archive_path = RAW_DIR / f"game-{game_id}.zip"
    if not archive_path.exists():
        print(f"status=missing_archive path={archive_path}")
        return 2
    archive_data = archive_path.read_bytes()
    unlimited_fuel = _settings_unlimited_fuel(archive_data)
    topology = effective_sphere_topology(
        game_id=game_id,
        topology=extract_map_topology(archive_data),
    )
    print(f"settings_unlimited_fuel={unlimited_fuel}")
    print(f"sphere={topology.sphere}")
    if unlimited_fuel is True or topology.sphere is True:
        print("status=ineligible_archive")
        return 2

    print("stage=prepared_cache", flush=True)
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=game_id,
        cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
    )
    print(f"prepared cache_hit={cache_hit}", flush=True)

    specs = _static_specs(archive_data)
    entities = _entity_map(prepared.snapshots)
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    snapshots = _snapshot_by_owner(prepared)

    owner_id, before_raw, after_raw, same_identity = _owner_states(
        ship_groups=ship_groups,
        before_turn=before_turn,
        after_turn=after_turn,
        ship_id=ship_id,
    )
    if owner_id is None or before_raw is None or after_raw is None or not same_identity:
        print("status=owner_state_unready")
        return 2
    if not _mass_state_complete(before_raw):
        print("status=mass_state_incomplete")
        return 2

    snapshot = snapshots.get((before_turn, owner_id))
    if snapshot is None:
        print("status=owner_snapshot_missing")
        return 2
    state = snapshot.import_state()
    ship = state.ships.get(ship_id)
    if ship is None or ship.owner_id != owner_id:
        print("status=snapshot_ship_missing")
        return 2
    if ship.engine_id is None or ship.engine_id not in specs.engines:
        print("status=engine_missing")
        return 2

    snapshot_fuel = _intish(before_raw.get("neutronium"))
    after_fuel = _intish(after_raw.get("neutronium"))
    gravitonic = hull_id in GRAVITONIC_HULL_IDS
    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    waypoint_distance = hypot(target[0] - origin[0], target[1] - origin[1])
    true_partial_route = waypoint_distance > float(max_distance) + 1e-9

    scan = _phase_cost_basis_scan(
        ship,
        specs,
        origin=origin,
        target=target,
        observed=observed,
        warp=warp,
        gravitonic=gravitonic,
        scan_cap=args.fuel_scan_cap,
    )

    snapshot_detail = None
    if snapshot_fuel is not None:
        snapshot_candidate = deepcopy(ship)
        snapshot_candidate.cargo.neutronium = snapshot_fuel
        snapshot_mass = ship_movement_mass(snapshot_candidate, specs)
        fuel_factor = specs.engines[snapshot_candidate.engine_id].fuel_factor(warp)
        nominal_one_turn_endpoint = scan["nominal_one_turn_endpoint"]
        exact_projected_distance = hypot(
            nominal_one_turn_endpoint[0] - origin[0],
            nominal_one_turn_endpoint[1] - origin[1],
        )
        required_projected = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=snapshot_mass,
            distance_traveled=exact_projected_distance,
            max_distance_per_turn=max_distance,
        )
        required_nominal = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=snapshot_mass,
            distance_traveled=float(max_distance),
            max_distance_per_turn=max_distance,
        )
        snapshot_detail = {
            "phase_fuel": snapshot_fuel,
            "movement_mass": snapshot_mass,
            "required_projected": required_projected,
            "required_nominal": required_nominal,
            "projected_endpoint": _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_projected,
            ),
            "nominal_endpoint": _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_nominal,
            ),
        }

    raw_ships = _owner_snapshot_raw_ships(snapshot)
    colocated_ships: list[dict[str, Any]] = []
    incoming_transfer_candidates: list[dict[str, Any]] = []
    incoming_tow_tower_ids: list[int] = []
    for raw_ship in raw_ships:
        other_id = _raw_int(raw_ship, "id")
        other_x = _raw_int(raw_ship, "x")
        other_y = _raw_int(raw_ship, "y")
        if other_id is None:
            continue
        if (
            _mission(raw_ship) == TOW_MISSION_ID
            and _target_id(raw_ship) == ship_id
            and (other_x, other_y) == origin
        ):
            incoming_tow_tower_ids.append(other_id)
        if (other_x, other_y) != origin:
            continue
        summary = {
            "ship": other_id,
            "owner": _raw_int(raw_ship, "ownerid", "owner_id"),
            "hull": _raw_int(raw_ship, "hullid", "hull_id"),
            "mission": _mission(raw_ship),
            "mission1target": _target_id(raw_ship),
            "warp": _raw_int(raw_ship, "warp"),
            "neutronium": _raw_int(raw_ship, "neutronium"),
            "friendly_code_class": _friendly_code_class(raw_ship),
            "order_fields": _mechanical_order_fields(raw_ship),
        }
        colocated_ships.append(summary)
        if other_id != ship_id and _transfer_target(raw_ship) == ship_id:
            incoming_transfer_candidates.append(
                {
                    "source_ship": other_id,
                    "source_owner": summary["owner"],
                    "transfer_neutronium": _transfer_neutronium(raw_ship),
                    "order_fields": summary["order_fields"],
                }
            )

    colocated_planets: list[dict[str, Any]] = []
    for raw_planet in _owner_snapshot_raw_planets(snapshot):
        if (
            _raw_int(raw_planet, "x") == origin[0]
            and _raw_int(raw_planet, "y") == origin[1]
        ):
            colocated_planets.append(
                {
                    "planet": _raw_int(raw_planet, "id"),
                    "owner": _raw_int(raw_planet, "ownerid", "owner_id"),
                    "neutronium": _raw_int(raw_planet, "neutronium"),
                    "order_fields": _mechanical_order_fields(raw_planet),
                }
            )

    planets_by_turn = _planet_tuples_by_turn(entities)
    planets = planets_by_turn.get(before_turn, ())
    sample = MovementSample(
        turn=embedded_turn,
        ship_id=ship_id,
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        warp=warp,
        next_x=observed[0],
        next_y=observed[1],
        hull_id=hull_id,
        gravitonic=gravitonic,
        game_id=game_id,
    )
    baseline_category = _movement_category(sample, planets=planets)

    mine_context = build_mine_evidence_context(
        game_id=game_id,
        archive_data=archive_data,
        snapshots=prepared.snapshots,
    )
    mine_evidence = classify_strong_mine_hit_transition(
        context=mine_context,
        before_turn=before_turn,
        after_turn=after_turn,
        ship_id=ship_id,
        owner_id=owner_id,
        before_raw=before_raw,
        sample=sample,
    )

    races = _race_map(prepared.snapshots)
    race_id = races.get(owner_id)
    before_damage = _intish(before_raw.get("damage"))
    after_damage = _intish(after_raw.get("damage"))
    damage_limit = _max_warp_from_damage(before_damage, race_id)
    damage_effective_warp = min(warp, damage_limit) if damage_limit is not None else None
    damage_category = None
    if damage_effective_warp is not None and damage_effective_warp < warp:
        damage_sample = _effective_damage_sample(sample, effective_warp=damage_effective_warp)
        damage_category = _movement_category(damage_sample, planets=planets)

    storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(
        prepared.snapshots
    )
    storm_category = None
    storm_status = None
    if after_turn in storm_conflicts:
        storm_status = "conflict"
    elif after_turn in storm_invalid:
        storm_status = "invalid"
    else:
        storm_category, storm_status = _storm_expected_category(
            sample,
            storms=storms_by_turn.get(after_turn, ()),
            planets=planets,
        )

    tow_targets, _ = _observed_tow_targets(
        entities=entities,
        ship_groups=ship_groups,
        valid_pairs={(before_turn, after_turn)},
        convention=MovementMissionConvention(),
    )
    tow_route_towers = tow_targets.get((before_turn, ship_id), ())

    abilities = extract_stable_chunnel_abilities(archive_data)
    transition_by_key = {
        (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
        for item in prepared.movement_geometry_readiness.results
    }
    chunnel_matches: tuple[dict[str, Any], ...] = ()
    if after_turn not in storm_conflicts and after_turn not in storm_invalid:
        chunnel_matches = _targeted_chunnel_matches(
            before_turn=before_turn,
            after_turn=after_turn,
            ship_id=ship_id,
            owner_id=owner_id,
            observed=observed,
            abilities=abilities,
            entities=entities,
            ship_groups=ship_groups,
            transition_by_key=transition_by_key,
            planets=planets,
            storms=storms_by_turn.get(after_turn, ()),
        )

    known_external_flags: list[str] = []
    if baseline_category in GEOMETRY_EXPLAINED_CATEGORIES:
        known_external_flags.append(f"baseline:{baseline_category}")
    if mine_evidence is not None:
        known_external_flags.append(f"mine:{mine_evidence.category}")
    if damage_category in GEOMETRY_EXPLAINED_CATEGORIES:
        known_external_flags.append(f"damage:{damage_category}")
    if storm_category is not None:
        known_external_flags.append(f"storm:{storm_category}")
    if tow_route_towers:
        known_external_flags.append("observed_tow_route")
    if chunnel_matches:
        known_external_flags.append("observed_chunnel_target_route")

    print("\n===== CASE GEOMETRY / FUEL =====")
    print(
        {
            "game": game_id,
            "turn": before_turn,
            "after_turn": after_turn,
            "ship": ship_id,
            "hull": hull_id,
            "owner": owner_id,
            "owner_race": race_id,
            "warp": warp,
            "gravitonic": gravitonic,
            "origin": origin,
            "target": target,
            "observed": observed,
            "waypoint_distance": round(waypoint_distance, 6),
            "max_distance": max_distance,
            "true_partial_route": true_partial_route,
            "snapshot_fuel": snapshot_fuel,
            "after_fuel": after_fuel,
            "snapshot_detail": snapshot_detail,
        }
    )

    print("\n===== PHASE-FUEL MODEL SCAN =====")
    print(scan)

    print("\n===== OWNER-VISIBLE PRE-HOST CONTEXT =====")
    print(
        {
            "ship_order_fields": _mechanical_order_fields(before_raw),
            "ship_friendly_code_class": _friendly_code_class(before_raw),
            "visible_incoming_transfer_candidates": incoming_transfer_candidates,
            "visible_incoming_tow_tower_ids": tuple(sorted(incoming_tow_tower_ids)),
            "colocated_planets": colocated_planets,
            "colocated_ships": colocated_ships,
        }
    )

    print("\n===== EXTERNAL MOVEMENT CONFOUNDERS =====")
    print(
        {
            "baseline_category": baseline_category,
            "before_damage": before_damage,
            "after_damage": after_damage,
            "damage_warp_limit": damage_limit,
            "damage_effective_warp": damage_effective_warp,
            "damage_category": damage_category,
            "mine_evidence": (
                {
                    "category": mine_evidence.category,
                    "damage_hits": mine_evidence.damage_hits,
                    "slowdown_hits": mine_evidence.slowdown_hits,
                }
                if mine_evidence is not None
                else None
            ),
            "storm_status": storm_status,
            "storm_category": storm_category,
            "observed_tow_route_towers": tuple(tow_route_towers),
            "observed_chunnel_target_events": chunnel_matches,
            "known_external_flags": tuple(known_external_flags),
        }
    )

    print("\n===== SUMMARY =====")
    for key in (
        "projected_exact_phase_fuel_ranges",
        "nominal_exact_phase_fuel_ranges",
        "both_exact_phase_fuel_ranges",
        "projected_only_phase_fuel_ranges",
        "nominal_only_phase_fuel_ranges",
        "projected_exact_post_fuel_ranges",
        "nominal_exact_post_fuel_ranges",
    ):
        print(f"{key}=", scan[key])
    print("visible_incoming_transfer_candidates=", len(incoming_transfer_candidates))
    print("visible_incoming_tow_candidates=", len(incoming_tow_tower_ids))
    print("known_external_flags=", tuple(known_external_flags))

    print("\n===== INTERPRETATION =====")
    print(
        "The phase-fuel scan recomputes movement mass for every hypothetical phase fuel. "
        "A snapshot-fuel match is therefore not privileged over another phase-fuel value."
    )
    print(
        "An empty known_external_flags tuple excludes only the already-modelled factual "
        "mine/storm/damage/Tow/Chunnel explanations checked here. It does not prove that no "
        "hidden or earlier Host state mutation occurred."
    )
    print(
        "Next-turn fuel is supporting evidence only; later Host phases may modify neutronium, "
        "so it is not treated as a movement-phase boundary."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
