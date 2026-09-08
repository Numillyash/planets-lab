from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
)
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
from tow_strict_lock_historical_audit import _chain_nodes, _tow_attempts_by_turn


EXAMPLE_LIMIT = 80


def _raw_int(raw: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in raw:
            value = _intish(raw.get(key))
            if value is not None:
                return value
    return None


def _visible_ship_raw(snapshot: Any, ship_id: int) -> Mapping[str, Any] | None:
    raw_ships = snapshot.mechanics_payload.get("ships", [])
    if not isinstance(raw_ships, list):
        return None
    matches = [
        raw
        for raw in raw_ships
        if isinstance(raw, Mapping) and _raw_int(raw, "id") == ship_id
    ]
    return matches[0] if len(matches) == 1 else None


def _nonfuel_lock_proof(
    *,
    tower_hull_id: int,
    tower_warp: int,
    target_hull_id: int,
    target_engine_count: int,
    target_x: int | None,
    target_y: int | None,
    target_warp: int | None,
    target_waypoint_x: int | None,
    target_waypoint_y: int | None,
) -> tuple[bool, str]:
    """Prove that Four Fingers cannot break Tow without using target fuel.

    Snapshot neutronium is deliberately absent. If the target could break Tow
    whenever its Tow-phase fuel were >25 KT, this helper returns unresolved.
    """

    if target_engine_count < 2:
        return True, "target_lt2_engines"

    if None in (
        target_x,
        target_y,
        target_warp,
        target_waypoint_x,
        target_waypoint_y,
    ):
        return False, "target_navigation_unknown"

    assert target_x is not None
    assert target_y is not None
    assert target_warp is not None
    assert target_waypoint_x is not None
    assert target_waypoint_y is not None

    target_waypoint_distance = hypot(
        target_waypoint_x - target_x,
        target_waypoint_y - target_y,
    )
    if target_waypoint_distance <= target_warp * target_warp:
        return True, "target_waypoint_within_warp_square"

    tower_speed = max_nominal_distance(
        tower_warp,
        gravitonic=tower_hull_id in GRAVITONIC_HULL_IDS,
    )
    target_speed = max_nominal_distance(
        target_warp,
        gravitonic=target_hull_id in GRAVITONIC_HULL_IDS,
    )
    if target_speed < tower_speed:
        return True, "target_effectively_slower"

    return False, "lock_depends_on_target_phase_fuel"


def _fuel_endpoint(
    *,
    origin: tuple[int, int],
    waypoint: tuple[int, int],
    geometry_endpoint: tuple[int, int],
    requested_distance: float,
    fuel_available: int,
    fuel_required: int,
) -> tuple[int, int] | None:
    if fuel_required < 0 or fuel_available < 0:
        return None
    if fuel_required == 0 or fuel_available >= fuel_required:
        return geometry_endpoint
    prorated_distance = requested_distance * fuel_available / fuel_required
    return project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=waypoint[0],
        target_y=waypoint[1],
        distance=prorated_distance,
    )


def _phase_fuel_envelope(
    *,
    origin: tuple[int, int],
    waypoint: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    gravitonic: bool,
    fuel_factor: int,
    tower_nonfuel_mass: int,
    target_nonfuel_mass: int,
    tower_fuel_tank: int,
    target_fuel_tank: int,
) -> dict[str, Any]:
    """Search physical fuel-capacity envelopes while holding non-fuel mass fixed.

    Tower Tow-phase fuel is scanned over 1..tank. Target fuel is scanned through
    the mass/10 bins it can induce, because movement_fuel_use only observes the
    truncated 10-KT mass. This is deliberately broader than snapshot fuel and
    therefore cannot be read as factual phase-state reconstruction.
    """

    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    waypoint_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
    true_partial = waypoint_distance > max_distance
    requested_distance = float(max_distance) if true_partial else waypoint_distance

    if true_partial:
        geometry_endpoint = project_toward_waypoint(
            x=origin[0],
            y=origin[1],
            target_x=waypoint[0],
            target_y=waypoint[1],
            distance=max_distance,
        )
        projected_cost_distance = hypot(
            geometry_endpoint[0] - origin[0],
            geometry_endpoint[1] - origin[1],
        )
        nominal_cost_distance = float(max_distance)
    else:
        geometry_endpoint = waypoint
        projected_cost_distance = waypoint_distance
        nominal_cost_distance = waypoint_distance

    projected_witness: dict[str, Any] | None = None
    nominal_witness: dict[str, Any] | None = None
    states_checked = 0

    fixed_nonfuel_mass = tower_nonfuel_mass + target_nonfuel_mass
    for tower_fuel in range(1, tower_fuel_tank + 1):
        low_mass = fixed_nonfuel_mass + tower_fuel
        low_tens = low_mass // 10
        high_tens = (low_mass + target_fuel_tank) // 10

        for mass_tens in range(low_tens, high_tens + 1):
            # Pick one target-fuel value in this exact 10-KT mass bin.
            target_fuel = max(0, mass_tens * 10 - low_mass)
            if target_fuel > target_fuel_tank:
                continue
            combined_mass = low_mass + target_fuel
            if combined_mass // 10 != mass_tens:
                continue

            states_checked += 1
            projected_required = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=combined_mass,
                distance_traveled=projected_cost_distance,
                max_distance_per_turn=max_distance,
            )
            nominal_required = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=combined_mass,
                distance_traveled=nominal_cost_distance,
                max_distance_per_turn=max_distance,
            )
            projected_endpoint = _fuel_endpoint(
                origin=origin,
                waypoint=waypoint,
                geometry_endpoint=geometry_endpoint,
                requested_distance=requested_distance,
                fuel_available=tower_fuel,
                fuel_required=projected_required,
            )
            nominal_endpoint = _fuel_endpoint(
                origin=origin,
                waypoint=waypoint,
                geometry_endpoint=geometry_endpoint,
                requested_distance=requested_distance,
                fuel_available=tower_fuel,
                fuel_required=nominal_required,
            )

            if projected_witness is None and projected_endpoint == observed:
                projected_witness = {
                    "tower_phase_fuel": tower_fuel,
                    "target_phase_fuel_witness": target_fuel,
                    "combined_mass": combined_mass,
                    "fuel_required": projected_required,
                    "endpoint": projected_endpoint,
                }
            if nominal_witness is None and nominal_endpoint == observed:
                nominal_witness = {
                    "tower_phase_fuel": tower_fuel,
                    "target_phase_fuel_witness": target_fuel,
                    "combined_mass": combined_mass,
                    "fuel_required": nominal_required,
                    "endpoint": nominal_endpoint,
                }
            if projected_witness is not None and nominal_witness is not None:
                return {
                    "true_partial": true_partial,
                    "waypoint_distance": waypoint_distance,
                    "max_distance": max_distance,
                    "geometry_endpoint": geometry_endpoint,
                    "projected_cost_distance": projected_cost_distance,
                    "nominal_cost_distance": nominal_cost_distance,
                    "states_checked": states_checked,
                    "projected_possible": True,
                    "nominal_possible": True,
                    "projected_witness": projected_witness,
                    "nominal_witness": nominal_witness,
                }

    return {
        "true_partial": true_partial,
        "waypoint_distance": waypoint_distance,
        "max_distance": max_distance,
        "geometry_endpoint": geometry_endpoint,
        "projected_cost_distance": projected_cost_distance,
        "nominal_cost_distance": nominal_cost_distance,
        "states_checked": states_checked,
        "projected_possible": projected_witness is not None,
        "nominal_possible": nominal_witness is not None,
        "projected_witness": projected_witness,
        "nominal_witness": nominal_witness,
    }


def _append_example(
    examples: dict[str, list[dict[str, Any]]],
    bucket: str,
    item: dict[str, Any],
    limit: int,
) -> None:
    if len(examples[bucket]) < limit:
        examples[bucket].append(item)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Discover strict finite-fuel Tow historical differentials. Successful "
            "Tow routes are restricted to unique owner-visible tower identities, "
            "non-sphere finite-fuel games, no same-target contests/chains, same-"
            "identity tower/target state, and Four Fingers locks provable without "
            "using target snapshot fuel. Snapshot fuel is evidence only. The phase "
            "envelope varies only neutronium within physical tank capacities while "
            "holding non-fuel mass fixed. This diagnostic never promotes Tow."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        game_ids = [
            int(row[0])
            for row in con.execute("SELECT game_id FROM games ORDER BY game_id").fetchall()
        ]
        pairs_by_game = {
            game_id: {
                (int(row[0]), int(row[1]))
                for row in con.execute(
                    """
                    SELECT DISTINCT before_archive_turn, after_archive_turn
                    FROM movement_transitions
                    WHERE game_id = ?
                    ORDER BY before_archive_turn, after_archive_turn
                    """,
                    [game_id],
                ).fetchall()
            }
            for game_id in game_ids
        }
    finally:
        con.close()

    print("===== FINITE-FUEL TOW HISTORICAL DISCOVERY =====")
    print("games=", game_ids)

    totals: Counter[str] = Counter()
    lock_reasons: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in game_ids:
        totals["games"] += 1
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            totals["missing_archive"] += 1
            print(f"game={game_id} missing_archive")
            continue

        archive_data = archive_path.read_bytes()
        unlimited_fuel = _settings_unlimited_fuel(archive_data)
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True:
            totals["sphere_excluded_games"] += 1
            print(f"game={game_id} skipped=sphere")
            continue
        if unlimited_fuel is True:
            totals["unlimited_fuel_excluded_games"] += 1
            print(f"game={game_id} skipped=unlimited_fuel")
            continue
        if unlimited_fuel is None:
            totals["fuel_setting_unknown_games"] += 1
            print(f"game={game_id} skipped=fuel_setting_unknown")
            continue
        totals["finite_fuel_games"] += 1

        print(f"game={game_id} stage=prepared_cache", flush=True)
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        convention = MovementMissionConvention()
        pairs = pairs_by_game[game_id]
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
        totals["observed_tow_attempt_records"] += observed_counts.get("tow_attempt_records", 0)
        totals["observed_route_targets"] += len(matches)

        imported_states: dict[tuple[int, int], Any] = {}
        game_ready = 0

        for (before_turn, target_id), matching_towers in sorted(matches.items()):
            if len(matching_towers) != 1:
                totals["route_identity_ambiguous"] += 1
                continue

            tower_id = matching_towers[0]
            turn_attempts = attempts_by_turn.get(before_turn, ())
            targeters = tuple(item for item in turn_attempts if item[1] == target_id)
            if len(targeters) != 1:
                totals["strict_excluded_same_target_contest"] += 1
                continue

            chain_nodes = _chain_nodes(turn_attempts)
            if tower_id in chain_nodes or target_id in chain_nodes:
                totals["strict_excluded_tow_chain"] += 1
                continue

            after_turns = {
                after_turn
                for pair_before, after_turn in pairs
                if pair_before == before_turn
            }
            if len(after_turns) != 1:
                totals["turn_pair_ambiguous"] += 1
                continue
            actual_after_turn = next(iter(after_turns))

            tower_owner_id, tower_before_raw, tower_after_raw, tower_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=actual_after_turn,
                ship_id=tower_id,
            )
            target_owner_id, target_before_raw, target_after_raw, target_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=actual_after_turn,
                ship_id=target_id,
            )
            if (
                tower_owner_id is None
                or tower_before_raw is None
                or tower_after_raw is None
                or target_owner_id is None
                or target_before_raw is None
                or target_after_raw is None
            ):
                totals["owner_state_missing"] += 1
                continue
            if not tower_same_identity or not target_same_identity:
                totals["identity_break"] += 1
                continue
            mission_target = _raw_int(
                tower_before_raw,
                "mission1target",
                "mission1_target_id",
                "mission1targetid",
            )
            if mission_target != target_id:
                totals["tower_target_mismatch"] += 1
                continue
            if str(tower_before_raw.get("friendlycode", "")).strip().lower() == "hyp":
                totals["tower_hyp_excluded"] += 1
                continue
            if str(target_before_raw.get("friendlycode", "")).strip().lower() == "hyp":
                totals["target_hyp_excluded"] += 1
                continue

            tower_x = _raw_int(tower_before_raw, "x")
            tower_y = _raw_int(tower_before_raw, "y")
            target_x = _raw_int(target_before_raw, "x")
            target_y = _raw_int(target_before_raw, "y")
            if None in (tower_x, tower_y, target_x, target_y):
                totals["geometry_missing"] += 1
                continue
            assert tower_x is not None and tower_y is not None
            assert target_x is not None and target_y is not None
            if (tower_x, tower_y) != (target_x, target_y):
                totals["not_colocated"] += 1
                continue

            tower_hull_id = _raw_int(tower_before_raw, "hullid", "hull_id")
            target_hull_id = _raw_int(target_before_raw, "hullid", "hull_id")
            if tower_hull_id is None or target_hull_id is None:
                totals["hull_missing"] += 1
                continue
            tower_hull = specs.hulls.get(tower_hull_id)
            target_hull = specs.hulls.get(target_hull_id)
            if tower_hull is None or target_hull is None:
                totals["hull_spec_missing"] += 1
                continue
            if tower_hull.engine_count < 2:
                totals["tower_engine_ineligible"] += 1
                continue

            tower_warp = _raw_int(tower_before_raw, "warp")
            if tower_warp is None or not 1 <= tower_warp <= 9:
                totals["tower_warp_invalid"] += 1
                continue
            target_warp = _raw_int(target_before_raw, "warp")
            target_waypoint_x = _raw_int(target_before_raw, "targetx", "waypointx")
            target_waypoint_y = _raw_int(target_before_raw, "targety", "waypointy")
            proven_lock, lock_reason = _nonfuel_lock_proof(
                tower_hull_id=tower_hull_id,
                tower_warp=tower_warp,
                target_hull_id=target_hull_id,
                target_engine_count=target_hull.engine_count,
                target_x=target_x,
                target_y=target_y,
                target_warp=target_warp,
                target_waypoint_x=target_waypoint_x,
                target_waypoint_y=target_waypoint_y,
            )
            lock_reasons[lock_reason] += 1
            if not proven_lock:
                totals["lock_nonfuel_unresolved"] += 1
                continue
            totals["lock_nonfuel_proven"] += 1

            tower_waypoint_x = _raw_int(tower_before_raw, "targetx", "waypointx")
            tower_waypoint_y = _raw_int(tower_before_raw, "targety", "waypointy")
            observed_x = _raw_int(tower_after_raw, "x")
            observed_y = _raw_int(tower_after_raw, "y")
            if None in (tower_waypoint_x, tower_waypoint_y, observed_x, observed_y):
                totals["tower_route_missing"] += 1
                continue
            assert tower_waypoint_x is not None and tower_waypoint_y is not None
            assert observed_x is not None and observed_y is not None
            origin = (tower_x, tower_y)
            waypoint = (tower_waypoint_x, tower_waypoint_y)
            observed = (observed_x, observed_y)
            target_after_x = _raw_int(target_after_raw, "x")
            target_after_y = _raw_int(target_after_raw, "y")
            if (target_after_x, target_after_y) != observed:
                totals["cross_owner_after_destination_disagrees"] += 1
                continue
            if waypoint == origin or observed == origin:
                totals["stationary_or_zero_waypoint_excluded"] += 1
                continue

            if not _mass_state_complete(tower_before_raw) or not _mass_state_complete(target_before_raw):
                totals["mass_state_incomplete"] += 1
                continue

            tower_snapshot = snapshots.get((before_turn, tower_owner_id))
            target_snapshot = snapshots.get((before_turn, target_owner_id))
            if tower_snapshot is None or target_snapshot is None:
                totals["owner_snapshot_missing"] += 1
                continue

            target_visible_raw = _visible_ship_raw(tower_snapshot, target_id)
            if target_visible_raw is None:
                totals["target_not_visible_to_tower_owner"] += 1
                continue
            visible_target_x = _raw_int(target_visible_raw, "x")
            visible_target_y = _raw_int(target_visible_raw, "y")
            if (visible_target_x, visible_target_y) != (target_x, target_y):
                totals["target_visible_geometry_disagrees"] += 1
                continue
            totals["target_visible_to_tower_owner"] += 1

            try:
                tower_key = (before_turn, tower_owner_id)
                if tower_key not in imported_states:
                    imported_states[tower_key] = tower_snapshot.import_state()
                target_key = (before_turn, target_owner_id)
                if target_key not in imported_states:
                    imported_states[target_key] = target_snapshot.import_state()
                tower_ship = imported_states[tower_key].ships.get(tower_id)
                target_ship = imported_states[target_key].ships.get(target_id)
                if (
                    tower_ship is None
                    or tower_ship.owner_id != tower_owner_id
                    or target_ship is None
                    or target_ship.owner_id != target_owner_id
                ):
                    totals["imported_ship_missing"] += 1
                    continue

                tower_snapshot_mass = ship_movement_mass(tower_ship, specs)
                target_snapshot_mass = ship_movement_mass(target_ship, specs)
            except (KeyError, ValueError) as exc:
                totals["mass_import_error"] += 1
                _append_example(
                    examples,
                    "mass_import_error",
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "tower_ship": tower_id,
                        "target_ship": target_id,
                        "error": str(exc),
                    },
                    args.examples,
                )
                continue

            if tower_ship.engine_id is None or tower_ship.engine_id not in specs.engines:
                totals["tower_engine_spec_missing"] += 1
                continue
            fuel_factor = specs.engines[tower_ship.engine_id].fuel_factor(tower_warp)
            tower_snapshot_fuel = int(tower_ship.cargo.neutronium)
            target_snapshot_fuel = int(target_ship.cargo.neutronium)
            tower_nonfuel_mass = tower_snapshot_mass - tower_snapshot_fuel
            target_nonfuel_mass = target_snapshot_mass - target_snapshot_fuel

            envelope = _phase_fuel_envelope(
                origin=origin,
                waypoint=waypoint,
                observed=observed,
                warp=tower_warp,
                gravitonic=tower_hull_id in GRAVITONIC_HULL_IDS,
                fuel_factor=fuel_factor,
                tower_nonfuel_mass=tower_nonfuel_mass,
                target_nonfuel_mass=target_nonfuel_mass,
                tower_fuel_tank=tower_hull.fuel_tank,
                target_fuel_tank=target_hull.fuel_tank,
            )

            max_distance = int(envelope["max_distance"])
            waypoint_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
            requested_distance = (
                float(max_distance)
                if bool(envelope["true_partial"])
                else waypoint_distance
            )
            snapshot_combined_mass = tower_snapshot_mass + target_snapshot_mass
            snapshot_projected_required = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=snapshot_combined_mass,
                distance_traveled=float(envelope["projected_cost_distance"]),
                max_distance_per_turn=max_distance,
            )
            snapshot_nominal_required = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=snapshot_combined_mass,
                distance_traveled=float(envelope["nominal_cost_distance"]),
                max_distance_per_turn=max_distance,
            )
            snapshot_projected_endpoint = _fuel_endpoint(
                origin=origin,
                waypoint=waypoint,
                geometry_endpoint=envelope["geometry_endpoint"],
                requested_distance=requested_distance,
                fuel_available=tower_snapshot_fuel,
                fuel_required=snapshot_projected_required,
            )
            snapshot_nominal_endpoint = _fuel_endpoint(
                origin=origin,
                waypoint=waypoint,
                geometry_endpoint=envelope["geometry_endpoint"],
                requested_distance=requested_distance,
                fuel_available=tower_snapshot_fuel,
                fuel_required=snapshot_nominal_required,
            )
            geometry_exact = envelope["geometry_endpoint"] == observed
            snapshot_projected_exact = snapshot_projected_endpoint == observed
            snapshot_nominal_exact = snapshot_nominal_endpoint == observed

            totals["fuel_model_ready"] += 1
            game_ready += 1
            totals["true_partial_route" if envelope["true_partial"] else "reachable_route"] += 1
            totals["geometry_exact" if geometry_exact else "geometry_differs"] += 1
            totals["snapshot_tower_fuel_zero" if tower_snapshot_fuel == 0 else "snapshot_tower_fuel_positive"] += 1
            totals["snapshot_projected_exact" if snapshot_projected_exact else "snapshot_projected_differs"] += 1
            totals["snapshot_nominal_exact" if snapshot_nominal_exact else "snapshot_nominal_differs"] += 1

            if snapshot_nominal_exact and not snapshot_projected_exact:
                totals["snapshot_nominal_only"] += 1
            elif snapshot_projected_exact and not snapshot_nominal_exact:
                totals["snapshot_projected_only"] += 1
            elif snapshot_projected_exact and snapshot_nominal_exact:
                totals["snapshot_both"] += 1
            else:
                totals["snapshot_neither"] += 1

            projected_possible = bool(envelope["projected_possible"])
            nominal_possible = bool(envelope["nominal_possible"])
            if projected_possible and nominal_possible:
                phase_bucket = "phase_both_possible"
            elif nominal_possible:
                phase_bucket = "phase_nominal_only_possible"
            elif projected_possible:
                phase_bucket = "phase_projected_only_possible"
            else:
                phase_bucket = "phase_neither_possible"
            totals[phase_bucket] += 1

            example = {
                "game": game_id,
                "turn": before_turn,
                "after_turn": actual_after_turn,
                "tower_ship": tower_id,
                "target_ship": target_id,
                "tower_owner": tower_owner_id,
                "target_owner": target_owner_id,
                "tower_hull": tower_hull_id,
                "target_hull": target_hull_id,
                "tower_warp": tower_warp,
                "lock_proof": lock_reason,
                "origin": origin,
                "waypoint": waypoint,
                "observed": observed,
                "geometry_endpoint": envelope["geometry_endpoint"],
                "true_partial": envelope["true_partial"],
                "waypoint_distance": round(float(envelope["waypoint_distance"]), 6),
                "max_distance": max_distance,
                "snapshot_tower_fuel": tower_snapshot_fuel,
                "snapshot_target_fuel": target_snapshot_fuel,
                "snapshot_combined_mass": snapshot_combined_mass,
                "snapshot_projected_required": snapshot_projected_required,
                "snapshot_nominal_required": snapshot_nominal_required,
                "snapshot_projected_endpoint": snapshot_projected_endpoint,
                "snapshot_nominal_endpoint": snapshot_nominal_endpoint,
                "geometry_exact": geometry_exact,
                "snapshot_projected_exact": snapshot_projected_exact,
                "snapshot_nominal_exact": snapshot_nominal_exact,
                "tower_after_fuel_supporting_only": _raw_int(tower_after_raw, "neutronium"),
                "phase_states_checked": envelope["states_checked"],
                "phase_projected_possible": projected_possible,
                "phase_nominal_possible": nominal_possible,
                "phase_projected_witness": envelope["projected_witness"],
                "phase_nominal_witness": envelope["nominal_witness"],
            }
            _append_example(examples, phase_bucket, example, args.examples)
            if (
                not geometry_exact
                and snapshot_nominal_exact
                and not snapshot_projected_exact
            ):
                _append_example(examples, "snapshot_nominal_discriminator", example, args.examples)
            if (
                not geometry_exact
                and snapshot_projected_exact
                and not snapshot_nominal_exact
            ):
                _append_example(examples, "snapshot_projected_discriminator", example, args.examples)

        print(
            f"game={game_id} cache_hit={cache_hit} "
            f"observed_routes={len(matches)} fuel_model_ready={game_ready}",
            flush=True,
        )

    print("\n===== SUMMARY =====")
    keys = (
        "games",
        "missing_archive",
        "finite_fuel_games",
        "sphere_excluded_games",
        "unlimited_fuel_excluded_games",
        "fuel_setting_unknown_games",
        "observed_tow_attempt_records",
        "observed_route_targets",
        "route_identity_ambiguous",
        "strict_excluded_same_target_contest",
        "strict_excluded_tow_chain",
        "turn_pair_ambiguous",
        "owner_state_missing",
        "identity_break",
        "tower_target_mismatch",
        "tower_hyp_excluded",
        "target_hyp_excluded",
        "geometry_missing",
        "not_colocated",
        "hull_missing",
        "hull_spec_missing",
        "tower_engine_ineligible",
        "tower_warp_invalid",
        "lock_nonfuel_unresolved",
        "lock_nonfuel_proven",
        "tower_route_missing",
        "cross_owner_after_destination_disagrees",
        "stationary_or_zero_waypoint_excluded",
        "mass_state_incomplete",
        "owner_snapshot_missing",
        "target_not_visible_to_tower_owner",
        "target_visible_geometry_disagrees",
        "target_visible_to_tower_owner",
        "imported_ship_missing",
        "mass_import_error",
        "tower_engine_spec_missing",
        "fuel_model_ready",
        "true_partial_route",
        "reachable_route",
        "geometry_exact",
        "geometry_differs",
        "snapshot_tower_fuel_zero",
        "snapshot_tower_fuel_positive",
        "snapshot_projected_exact",
        "snapshot_projected_differs",
        "snapshot_nominal_exact",
        "snapshot_nominal_differs",
        "snapshot_nominal_only",
        "snapshot_projected_only",
        "snapshot_both",
        "snapshot_neither",
        "phase_both_possible",
        "phase_nominal_only_possible",
        "phase_projected_only_possible",
        "phase_neither_possible",
    )
    for key in keys:
        print(f"{key}= {totals[key]}")

    print("\n===== NON-FUEL LOCK PROOFS =====")
    for key, value in lock_reasons.most_common():
        print(f"{key}= {value}")

    print("\n===== EXAMPLES =====")
    for bucket in (
        "snapshot_nominal_discriminator",
        "snapshot_projected_discriminator",
        "phase_nominal_only_possible",
        "phase_projected_only_possible",
        "phase_both_possible",
        "phase_neither_possible",
        "mass_import_error",
    ):
        print(f"-- {bucket} --")
        for item in examples[bucket]:
            print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "Snapshot tower/target neutronium is pre-Host evidence only. Exact snapshot "
        "matches are candidate evidence, not Tow-phase facts."
    )
    print(
        "The phase envelope varies neutronium across physical tank capacities while "
        "holding all non-fuel cargo/components at their owner-visible owner snapshots. "
        "Target mass is joined from the target owner's historical perspective for "
        "research only; the target is separately required to be visible in the tower "
        "owner's snapshot. This does not imply production visibility of target internals."
    )
    print(
        "The envelope addresses fuel-phase uncertainty only. Earlier non-fuel cargo "
        "transfers and external movement mechanics can still confound a match."
    )
    print(
        "phase_nominal_only_possible is the strongest discovery signature here: the "
        "factual endpoint is reachable somewhere in the broad fuel envelope under the "
        "continuous nominal-leg cost basis and nowhere under rasterized-endpoint cost. "
        "It still requires a targeted transfer/mine/storm/damage/warp-well/Chunnel "
        "confounder audit before any Tow promotion."
    )
    print("finite-fuel Tow remains OPEN; this diagnostic never changes rule status.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
