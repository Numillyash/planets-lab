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
from planets_lab.sim.normal_movement import project_toward_waypoint

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


MOVE_MOST_INTENT = "move_most_candidate"
INTERCEPT_INTENT = "intercept"


def _candidate_endpoint(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    requested_distance: float,
    fuel_available: int,
    fuel_required: int,
) -> tuple[int, int] | None:
    if fuel_required <= 0 or fuel_available < 0:
        return None
    if fuel_available >= fuel_required:
        distance = requested_distance
    else:
        distance = requested_distance * fuel_available / fuel_required
    return project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=distance,
    )


def _post_reset(after_raw: Any, observed: tuple[int, int]) -> bool:
    if not hasattr(after_raw, "get"):
        return False
    fuel = _intish(after_raw.get("neutronium"))
    warp = _intish(after_raw.get("warp"))
    target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    return fuel == 0 and warp == 0 and (target_x, target_y) == observed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Population differential for the fuel-cost basis of true partial one-turn movement. "
            "It compares fuel computed from the integer Host-projected endpoint distance against "
            "fuel computed from the continuous nominal warp-squared distance. Snapshot fuel is "
            "evidence only: pre-movement Host phases may mutate it."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

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
                intent_class,
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y
            FROM movement_transitions
            WHERE readiness_status = 'ready'
              AND warp BETWEEN 1 AND 9
              AND intent_class IN ('move_most_candidate', 'intercept')
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    signatures = Counter()
    examples: list[dict[str, Any]] = []

    print("===== PARTIAL MOVE FUEL COST POPULATION AUDIT =====")
    print("candidate_transition_rows=", len(rows))

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            totals["missing_archive"] += len(by_game[game_id])
            continue
        archive_data = archive_path.read_bytes()
        unlimited_fuel = _settings_unlimited_fuel(archive_data)
        if unlimited_fuel is True:
            totals["unlimited_fuel_rows_excluded"] += len(by_game[game_id])
            continue

        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True:
            totals["sphere_rows_excluded"] += len(by_game[game_id])
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

        game_true_partial = 0
        game_cost_diff = 0
        game_discriminating = 0

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                warp,
                intent_class,
                x,
                y,
                next_x,
                next_y,
                raw_target_x,
                raw_target_y,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            intent_class = str(intent_class)
            origin = (int(x), int(y))
            observed = (int(next_x), int(next_y))

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None or after_raw is None or not same_identity:
                totals["owner_state_unready"] += 1
                continue
            if not _mass_state_complete(before_raw):
                totals["mass_state_incomplete"] += 1
                continue

            if intent_class == INTERCEPT_INTENT:
                if _mission(before_raw) != INTERCEPT_MISSION_ID:
                    totals["intercept_mission_mismatch"] += 1
                    continue
                target_id = _target_id(before_raw)
                if target_id is None or target_id == ship_id:
                    totals["intercept_target_invalid"] += 1
                    continue
                target_transition = transition_by_key.get((before_turn, after_turn, target_id))
                if target_transition is None:
                    totals["intercept_target_transition_missing"] += 1
                    continue
                target_sample = _sample_from_transition(target_transition, entities)
                if target_sample is None:
                    totals["intercept_target_geometry_missing"] += 1
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
                    totals["intercept_target_state_unready"] += 1
                    continue
                target = tuple(int(value) for value in target_sample.observed_destination)
            else:
                target_id = None
                if raw_target_x is None or raw_target_y is None:
                    totals["move_most_target_missing"] += 1
                    continue
                target = (int(raw_target_x), int(raw_target_y))

            snapshot = snapshots.get((before_turn, owner_id))
            if snapshot is None:
                totals["owner_snapshot_missing"] += 1
                continue
            state = snapshot.import_state()
            ship = state.ships.get(ship_id)
            if ship is None or ship.owner_id != owner_id:
                totals["snapshot_ship_missing"] += 1
                continue
            snapshot_fuel = _intish(before_raw.get("neutronium"))
            if snapshot_fuel is None or snapshot_fuel < 0:
                totals["snapshot_fuel_missing"] += 1
                continue
            if ship.engine_id is None or ship.engine_id not in specs.engines:
                totals["engine_missing"] += 1
                continue

            gravitonic = hull_id in GRAVITONIC_HULL_IDS
            max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
            waypoint_distance = hypot(target[0] - origin[0], target[1] - origin[1])
            route_partial = waypoint_distance > float(max_distance) + 1e-9
            if not route_partial:
                totals["reachable_route"] += 1
                continue

            totals["true_partial_route"] += 1
            game_true_partial += 1
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
            movement_mass = ship_movement_mass(ship, specs)
            fuel_factor = specs.engines[ship.engine_id].fuel_factor(warp)
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
            if required_projected == required_nominal:
                totals["same_integer_cost"] += 1
                continue

            totals["cost_basis_differs"] += 1
            game_cost_diff += 1
            relation = (
                "below_both"
                if snapshot_fuel < required_projected
                else "between_costs"
                if snapshot_fuel < required_nominal
                else "sufficient_both"
            )
            totals[f"fuel_relation:{relation}"] += 1

            projected_cost_endpoint = _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_projected,
            )
            nominal_cost_endpoint = _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_nominal,
            )
            projected_exact = projected_cost_endpoint == observed
            nominal_exact = nominal_cost_endpoint == observed
            if projected_exact:
                totals["projected_cost_endpoint_exact"] += 1
            if nominal_exact:
                totals["nominal_cost_endpoint_exact"] += 1

            signature = (
                intent_class,
                relation,
                "projected_exact" if projected_exact else "projected_diff",
                "nominal_exact" if nominal_exact else "nominal_diff",
            )
            signatures[signature] += 1
            discriminating = projected_exact != nominal_exact
            if discriminating:
                totals["discriminating_endpoint"] += 1
                game_discriminating += 1
                if nominal_exact:
                    totals["discriminating_nominal_cost_support"] += 1
                else:
                    totals["discriminating_projected_cost_support"] += 1

            after_fuel = _intish(after_raw.get("neutronium"))
            post_reset = _post_reset(after_raw, observed)
            if discriminating and post_reset:
                totals["discriminating_with_post_reset"] += 1

            if (discriminating or relation != "sufficient_both") and len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "ship": ship_id,
                        "hull": hull_id,
                        "intent": intent_class,
                        "target_ship": target_id,
                        "warp": warp,
                        "origin": origin,
                        "target": target,
                        "observed": observed,
                        "nominal_endpoint": nominal_endpoint,
                        "waypoint_distance": round(waypoint_distance, 6),
                        "max_distance": max_distance,
                        "projected_distance": round(projected_distance, 6),
                        "snapshot_fuel": snapshot_fuel,
                        "after_fuel": after_fuel,
                        "movement_mass": movement_mass,
                        "required_projected": required_projected,
                        "required_nominal": required_nominal,
                        "fuel_relation": relation,
                        "projected_cost_endpoint": projected_cost_endpoint,
                        "projected_cost_exact": projected_exact,
                        "nominal_cost_endpoint": nominal_cost_endpoint,
                        "nominal_cost_exact": nominal_exact,
                        "post_reset": post_reset,
                    }
                )

        if game_true_partial:
            print(
                f"game={game_id} cache_hit={cache_hit} true_partial={game_true_partial} "
                f"cost_diff={game_cost_diff} discriminating={game_discriminating}"
            )

    print("\n===== SUMMARY =====")
    for key in (
        "true_partial_route",
        "reachable_route",
        "same_integer_cost",
        "cost_basis_differs",
        "fuel_relation:below_both",
        "fuel_relation:between_costs",
        "fuel_relation:sufficient_both",
        "projected_cost_endpoint_exact",
        "nominal_cost_endpoint_exact",
        "discriminating_endpoint",
        "discriminating_nominal_cost_support",
        "discriminating_projected_cost_support",
        "discriminating_with_post_reset",
    ):
        print(f"{key}=", totals[key])

    print("\n===== DIFFERENTIAL SIGNATURES =====")
    for signature, count in sorted(signatures.items(), key=lambda item: (-item[1], item[0])):
        print(count, signature)

    print("\n===== EXAMPLES =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION =====")
    print(
        "route_partial is defined geometrically as target distance > effective one-turn maximum; "
        "it does not reuse NormalMovePlan.partial, which also becomes true after reachable fuel "
        "proration and therefore is not a route-partial flag."
    )
    print(
        "The only model difference tested here is the fuel-cost distance basis for a true partial "
        "one-turn leg: integer projected endpoint distance versus continuous nominal maximum."
    )
    print(
        "Snapshot fuel remains pre-Host evidence rather than an Intercept/Move-Most phase fact. "
        "A discriminating endpoint is therefore evidence for a model only after earlier fuel-state "
        "mutations and other movement mechanics are considered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
