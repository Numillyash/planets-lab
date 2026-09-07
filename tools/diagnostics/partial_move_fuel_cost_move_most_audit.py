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

from planets_lab.corpus.movement_differential import _intish
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
    PREPARED_DIR,
    RAW_DIR,
    _mass_state_complete,
    _settings_unlimited_fuel,
    _snapshot_by_owner,
)
from mine_hit_hostorder_differential_audit import _owner_states


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
    distance = requested_distance
    if fuel_available < fuel_required:
        distance *= fuel_available / fuel_required
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
            "Fast population differential for the true-partial Move Most fuel-cost basis. "
            "DuckDB first removes reachable routes before any archive/prepared-state work, then "
            "the diagnostic compares projected-endpoint distance cost against full nominal "
            "warp-squared/effective-range cost. Snapshot fuel remains pre-Host evidence only."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=50)
    args = parser.parse_args()

    print("===== FAST PARTIAL MOVE MOST FUEL COST AUDIT =====", flush=True)
    print("stage=duckdb_prefilter", flush=True)

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
                y_after,
                target_x,
                target_y,
                nominal_max_distance
            FROM movement_transitions
            WHERE readiness_status = 'ready'
              AND intent_class = 'move_most_candidate'
              AND warp BETWEEN 1 AND 9
              AND target_x IS NOT NULL
              AND target_y IS NOT NULL
              AND nominal_max_distance IS NOT NULL
              AND sqrt(
                    (target_x - x_before) * (target_x - x_before)
                  + (target_y - y_before) * (target_y - y_before)
              ) > nominal_max_distance + 1e-9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print(f"prefilter_true_partial_rows={len(rows)}", flush=True)

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    signatures = Counter()
    examples: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        game_rows = by_game[game_id]
        print(f"game={game_id} stage=archive_check candidate_rows={len(game_rows)}", flush=True)
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            totals["missing_archive"] += len(game_rows)
            print(f"game={game_id} skipped=missing_archive", flush=True)
            continue
        archive_data = archive_path.read_bytes()
        unlimited_fuel = _settings_unlimited_fuel(archive_data)
        if unlimited_fuel is True:
            totals["unlimited_fuel_rows_excluded"] += len(game_rows)
            print(f"game={game_id} skipped=unlimited_fuel", flush=True)
            continue

        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True:
            totals["sphere_rows_excluded"] += len(game_rows)
            print(f"game={game_id} skipped=sphere", flush=True)
            continue

        print(f"game={game_id} stage=prepared_cache", flush=True)
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        print(f"game={game_id} prepared cache_hit={cache_hit}", flush=True)

        specs = _static_specs(archive_data)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        imported_states: dict[tuple[int, int], Any] = {}

        game_true_partial = 0
        game_cost_diff = 0
        game_discriminating = 0

        for row in game_rows:
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
                target_x,
                target_y,
                _compiled_nominal,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            origin = (int(x), int(y))
            observed = (int(next_x), int(next_y))
            target = (int(target_x), int(target_y))

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

            snapshot_key = (before_turn, owner_id)
            snapshot = snapshots.get(snapshot_key)
            if snapshot is None:
                totals["owner_snapshot_missing"] += 1
                continue
            if snapshot_key not in imported_states:
                imported_states[snapshot_key] = snapshot.import_state()
            state = imported_states[snapshot_key]
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
            if waypoint_distance <= float(max_distance) + 1e-9:
                totals["prefilter_false_positive"] += 1
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
            if snapshot_fuel < required_projected:
                relation = "below_both"
            elif snapshot_fuel < required_nominal:
                relation = "between_costs"
            else:
                relation = "sufficient_both"
            totals[f"fuel_relation:{relation}"] += 1

            projected_endpoint = _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_projected,
            )
            nominal_endpoint_candidate = _candidate_endpoint(
                origin=origin,
                target=target,
                requested_distance=float(max_distance),
                fuel_available=snapshot_fuel,
                fuel_required=required_nominal,
            )
            projected_exact = projected_endpoint == observed
            nominal_exact = nominal_endpoint_candidate == observed
            if projected_exact:
                totals["projected_cost_endpoint_exact"] += 1
            if nominal_exact:
                totals["nominal_cost_endpoint_exact"] += 1

            signature = (
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
                        "warp": warp,
                        "gravitonic": gravitonic,
                        "origin": origin,
                        "target": target,
                        "observed": observed,
                        "nominal_endpoint": nominal_endpoint,
                        "waypoint_distance": round(waypoint_distance, 6),
                        "max_distance": max_distance,
                        "projected_distance": round(projected_distance, 6),
                        "snapshot_fuel": snapshot_fuel,
                        "after_fuel": _intish(after_raw.get("neutronium")),
                        "movement_mass": movement_mass,
                        "required_projected": required_projected,
                        "required_nominal": required_nominal,
                        "fuel_relation": relation,
                        "projected_cost_endpoint": projected_endpoint,
                        "projected_cost_exact": projected_exact,
                        "nominal_cost_endpoint": nominal_endpoint_candidate,
                        "nominal_cost_exact": nominal_exact,
                        "post_reset": post_reset,
                    }
                )

        print(
            f"game={game_id} done true_partial={game_true_partial} "
            f"cost_diff={game_cost_diff} discriminating={game_discriminating}",
            flush=True,
        )

    print("\n===== SUMMARY =====")
    for key in (
        "true_partial_route",
        "prefilter_false_positive",
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
        "This diagnostic deliberately limits the independent-control population to factual "
        "Move Most candidates. Intercept cases are audited separately, so target post-movement "
        "reconstruction cannot dominate the runtime here."
    )
    print(
        "True-partial geometry is prefiltered in DuckDB before prepared snapshots are opened. "
        "The Python pass rechecks the route using the effective Gravitonic maximum and never "
        "uses NormalMovePlan.partial as a route-partial flag."
    )
    print(
        "Snapshot fuel remains pre-Host evidence. A discriminating endpoint supports a cost basis "
        "only after earlier fuel mutations and other movement mechanics are excluded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
