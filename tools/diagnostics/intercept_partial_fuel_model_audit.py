from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.mass import ship_movement_mass
from planets_lab.rules.movement import max_nominal_distance
from planets_lab.sim.normal_movement import plan_full_normal_move, project_toward_waypoint

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import (
    DEFAULT_DATABASE,
    INTERCEPT_MISSION_ID,
    PREPARED_DIR,
    RAW_DIR,
    _mass_state_complete,
    _mission,
    _settings_unlimited_fuel,
    _snapshot_by_owner,
    _target_id,
)
from mine_hit_hostorder_differential_audit import _owner_states


def _candidate_endpoint(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    requested_distance: float,
    fuel_available: int,
    fuel_required: int,
    max_distance: int,
) -> tuple[int, int] | None:
    if fuel_required <= 0 or fuel_available < 0:
        return None
    if fuel_available >= fuel_required:
        distance = min(requested_distance, float(max_distance))
    else:
        distance = requested_distance * fuel_available / fuel_required
        distance = min(distance, float(max_distance))
    return project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=distance,
    )


def _exact_denominator_ranges(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
    requested_distance: float,
    fuel_available: int,
    max_distance: int,
    scan_max: int,
) -> tuple[tuple[int, int], ...]:
    exact: list[int] = []
    for fuel_required in range(max(1, fuel_available + 1), scan_max + 1):
        endpoint = _candidate_endpoint(
            origin=origin,
            target=target,
            requested_distance=requested_distance,
            fuel_available=fuel_available,
            fuel_required=fuel_required,
            max_distance=max_distance,
        )
        if endpoint == observed:
            exact.append(fuel_required)
    if not exact:
        return ()
    ranges: list[tuple[int, int]] = []
    start = previous = exact[0]
    for value in exact[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return tuple(ranges)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare several explicit partial-waypoint fuel-proration models for the strict "
            "historical finite-fuel Intercept cases. This is a differential diagnostic only: "
            "it does not promote any model to production semantics."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--denominator-scan-max", type=int, default=500)
    args = parser.parse_args()
    if args.denominator_scan_max < 1:
        parser.error("--denominator-scan-max must be positive")

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                warp,
                x_before,
                y_before,
                x_after,
                y_after
            FROM movement_transitions
            WHERE intent_class = 'intercept'
              AND readiness_status = 'ready'
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    model_exact = Counter()
    cases: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            continue
        archive_data = archive_path.read_bytes()
        if _settings_unlimited_fuel(archive_data) is True:
            continue
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True:
            continue

        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }

        game_cases_before = len(cases)
        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                warp,
                x,
                y,
                next_x,
                next_y,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            origin = (int(x), int(y))
            observed = (int(next_x), int(next_y))

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None or after_raw is None or not same_identity:
                continue
            if _mission(before_raw) != INTERCEPT_MISSION_ID:
                continue
            if str(before_raw.get("friendlycode", "")).strip().lower() == "hyp":
                continue
            if not _mass_state_complete(before_raw):
                continue

            target_id = _target_id(before_raw)
            if target_id is None or target_id == ship_id:
                continue
            target_transition = transition_by_key.get((before_turn, after_turn, target_id))
            if target_transition is None:
                continue
            target_sample = _sample_from_transition(target_transition, entities)
            if target_sample is None:
                continue
            target_owner_id, target_before_raw, target_after_raw, target_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=target_id,
            )
            if (
                target_owner_id is None
                or target_before_raw is None
                or target_after_raw is None
                or not target_same_identity
                or _mission(target_before_raw) == INTERCEPT_MISSION_ID
            ):
                continue

            snapshot = snapshots.get((before_turn, owner_id))
            if snapshot is None:
                continue
            state = snapshot.import_state()
            interceptor = state.ships.get(ship_id)
            if interceptor is None or interceptor.owner_id != owner_id:
                continue

            target_final = tuple(int(value) for value in target_sample.observed_destination)
            gravitonic = hull_id in GRAVITONIC_HULL_IDS
            plan = plan_full_normal_move(
                interceptor,
                specs,
                target_x=target_final[0],
                target_y=target_final[1],
                warp=warp,
                gravitonic=gravitonic,
                allow_partial=True,
                allow_fuel_proration=True,
            )
            if not plan.fuel_limited:
                continue

            totals["strict_snapshot_fuel_limited"] += 1
            if plan.partial:
                totals["partial_waypoint_cases"] += 1
            else:
                totals["reachable_waypoint_cases"] += 1

            snapshot_fuel = _intish(before_raw.get("neutronium"))
            if snapshot_fuel is None or snapshot_fuel < 0:
                totals["snapshot_fuel_missing"] += 1
                continue

            if interceptor.engine_id is None or interceptor.engine_id not in specs.engines:
                totals["engine_missing"] += 1
                continue
            engine = specs.engines[interceptor.engine_id]
            hull = specs.hulls.get(hull_id)
            max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
            waypoint_distance = hypot(
                target_final[0] - origin[0],
                target_final[1] - origin[1],
            )
            nominal_endpoint = project_toward_waypoint(
                x=origin[0],
                y=origin[1],
                target_x=target_final[0],
                target_y=target_final[1],
                distance=max_distance,
            )
            projected_distance = hypot(
                nominal_endpoint[0] - origin[0],
                nominal_endpoint[1] - origin[1],
            )
            movement_mass = ship_movement_mass(interceptor, specs)
            fuel_factor = engine.fuel_factor(warp)
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
            required_waypoint = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=movement_mass,
                distance_traveled=waypoint_distance,
                max_distance_per_turn=max_distance,
            )

            requested_distances = {
                "projected": projected_distance,
                "nominal": float(max_distance),
                "waypoint": waypoint_distance,
            }
            required_costs = {
                "projected_cost": required_projected,
                "nominal_cost": required_nominal,
                "waypoint_cost": required_waypoint,
            }
            model_results: dict[str, dict[str, Any]] = {}
            for requested_name, requested_distance in requested_distances.items():
                for cost_name, required in required_costs.items():
                    model_name = f"{requested_name}_over_{cost_name}"
                    endpoint = _candidate_endpoint(
                        origin=origin,
                        target=target_final,
                        requested_distance=requested_distance,
                        fuel_available=snapshot_fuel,
                        fuel_required=required,
                        max_distance=max_distance,
                    )
                    exact = endpoint == observed
                    if exact:
                        model_exact[model_name] += 1
                    model_results[model_name] = {
                        "endpoint": endpoint,
                        "exact": exact,
                    }

            denominator_ranges = {
                requested_name: _exact_denominator_ranges(
                    origin=origin,
                    target=target_final,
                    observed=observed,
                    requested_distance=requested_distance,
                    fuel_available=snapshot_fuel,
                    max_distance=max_distance,
                    scan_max=args.denominator_scan_max,
                )
                for requested_name, requested_distance in requested_distances.items()
            }

            cases.append(
                {
                    "game": game_id,
                    "turn": before_turn,
                    "after_turn": after_turn,
                    "ship": ship_id,
                    "hull": hull_id,
                    "hull_name": hull.name if hull is not None else None,
                    "engine_id": interceptor.engine_id,
                    "engine_name": engine.name,
                    "warp": warp,
                    "gravitonic": gravitonic,
                    "target_ship": target_id,
                    "origin": origin,
                    "target_final_observed": target_final,
                    "observed": observed,
                    "snapshot_fuel": snapshot_fuel,
                    "after_fuel": _intish(after_raw.get("neutronium")),
                    "movement_mass": movement_mass,
                    "fuel_factor": fuel_factor,
                    "waypoint_distance": round(waypoint_distance, 6),
                    "max_distance": max_distance,
                    "nominal_endpoint": nominal_endpoint,
                    "projected_distance": round(projected_distance, 6),
                    "current_plan_reason": plan.reason,
                    "current_plan_fuel_required": plan.fuel_required,
                    "required_projected": required_projected,
                    "required_nominal": required_nominal,
                    "required_waypoint": required_waypoint,
                    "model_results": model_results,
                    "exact_denominator_ranges": denominator_ranges,
                }
            )

        game_case_count = len(cases) - game_cases_before
        if game_case_count:
            print(
                f"game={game_id} cache_hit={cache_hit} "
                f"strict_snapshot_fuel_limited={game_case_count}"
            )

    print("===== INTERCEPT PARTIAL FUEL MODEL AUDIT =====")
    print("strict_snapshot_fuel_limited=", totals["strict_snapshot_fuel_limited"])
    print("reachable_waypoint_cases=", totals["reachable_waypoint_cases"])
    print("partial_waypoint_cases=", totals["partial_waypoint_cases"])

    print("\n===== MODEL EXACT COUNTS =====")
    for model_name in sorted(model_exact):
        print(f"{model_name}=", model_exact[model_name])

    print("\n===== CASES =====")
    for case in cases:
        print(case)

    print("\n===== INTERPRETATION =====")
    print(
        "The current normal-movement planner deliberately refuses insufficient-fuel partial "
        "waypoints. Alternative rows here are diagnostic hypotheses only and must not be "
        "promoted from a single historical Intercept case."
    )
    print(
        "required_projected uses the integer Host-projected one-turn endpoint; required_nominal "
        "uses the continuous warp-squared maximum; required_waypoint extends the same documented "
        "fuel formula to the full Intercept target distance even when that distance exceeds the "
        "one-turn maximum."
    )
    print(
        "exact_denominator_ranges show which hypothetical integer fuel-required denominator(s) "
        "would rasterize to the factual endpoint for each requested-distance basis."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
