from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_differential import _entity_map, _planet_tuples_by_turn
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.mass import ship_movement_mass
from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR, _snapshot_by_owner
from tow_finite_fuel_population_audit import _fuel_endpoint

EXAMPLE_LIMIT = 40


def _parse_phase_neither(log_path: Path) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = log_path.read_text(encoding="utf-8")
    match = re.search(r"^phase_neither_possible=\s*(\d+)\s*$", text, re.M)
    if match is None:
        raise ValueError("phase_neither_possible summary counter missing")
    expected = int(match.group(1))
    start_marker = "-- phase_neither_possible --"
    end_marker = "-- mass_import_error --"
    if start_marker not in text or end_marker not in text:
        raise ValueError("phase-neither example markers missing")
    section = text.split(start_marker, 1)[1].split(end_marker, 1)[0]

    examples: list[dict[str, Any]] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            raise ValueError("phase-neither example is not a dict")
        examples.append(value)

    if len(examples) != expected:
        raise ValueError(
            f"phase-neither examples are truncated: expected {expected}, parsed {len(examples)}. "
            "Re-run discovery with --examples >= phase_neither_possible."
        )
    return expected, tuple(examples)


def _planet_at(
    observed: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> int | None:
    matches = [planet_id for planet_id, x, y in planets if (x, y) == observed]
    return matches[0] if len(matches) == 1 else None


def _warp_well_endpoint(
    *,
    origin: tuple[int, int],
    endpoint: tuple[int, int] | None,
    warp: int,
    planets: Sequence[tuple[int, int, int]],
) -> tuple[tuple[int, int] | None, int | None, bool]:
    if endpoint is None:
        return None, None, False
    try:
        planet_id = warp_well_planet_id(
            origin_x=origin[0],
            origin_y=origin[1],
            end_x=endpoint[0],
            end_y=endpoint[1],
            movement_warp=warp,
            planets=planets,
        )
    except WarpWellAmbiguityError:
        return None, None, True
    if planet_id is None:
        return endpoint, None, False
    for candidate_id, x, y in planets:
        if candidate_id == planet_id:
            return (x, y), planet_id, False
    return endpoint, None, False


def _phase_warpwell_envelope(
    *,
    origin: tuple[int, int],
    waypoint: tuple[int, int],
    observed: tuple[int, int],
    geometry_endpoint: tuple[int, int],
    requested_distance: float,
    max_distance: int,
    projected_cost_distance: float,
    nominal_cost_distance: float,
    warp: int,
    fuel_factor: int,
    tower_nonfuel_mass: int,
    target_nonfuel_mass: int,
    tower_fuel_tank: int,
    target_fuel_tank: int,
    planets: Sequence[tuple[int, int, int]],
) -> dict[str, Any]:
    projected_witness: dict[str, Any] | None = None
    nominal_witness: dict[str, Any] | None = None
    ambiguous_states = 0
    states_checked = 0
    fixed_nonfuel_mass = tower_nonfuel_mass + target_nonfuel_mass

    for tower_fuel in range(1, tower_fuel_tank + 1):
        low_mass = fixed_nonfuel_mass + tower_fuel
        low_tens = low_mass // 10
        high_tens = (low_mass + target_fuel_tank) // 10

        for mass_tens in range(low_tens, high_tens + 1):
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
            projected_after, projected_planet, projected_ambiguous = _warp_well_endpoint(
                origin=origin,
                endpoint=projected_endpoint,
                warp=warp,
                planets=planets,
            )
            nominal_after, nominal_planet, nominal_ambiguous = _warp_well_endpoint(
                origin=origin,
                endpoint=nominal_endpoint,
                warp=warp,
                planets=planets,
            )
            if projected_ambiguous or nominal_ambiguous:
                ambiguous_states += 1

            if projected_witness is None and projected_after == observed:
                projected_witness = {
                    "tower_phase_fuel": tower_fuel,
                    "target_phase_fuel_witness": target_fuel,
                    "combined_mass": combined_mass,
                    "fuel_required": projected_required,
                    "pre_warpwell_endpoint": projected_endpoint,
                    "warpwell_planet_id": projected_planet,
                    "observed": observed,
                }
            if nominal_witness is None and nominal_after == observed:
                nominal_witness = {
                    "tower_phase_fuel": tower_fuel,
                    "target_phase_fuel_witness": target_fuel,
                    "combined_mass": combined_mass,
                    "fuel_required": nominal_required,
                    "pre_warpwell_endpoint": nominal_endpoint,
                    "warpwell_planet_id": nominal_planet,
                    "observed": observed,
                }
            if projected_witness is not None and nominal_witness is not None:
                return {
                    "states_checked": states_checked,
                    "ambiguous_states": ambiguous_states,
                    "projected_possible": True,
                    "nominal_possible": True,
                    "projected_witness": projected_witness,
                    "nominal_witness": nominal_witness,
                }

    return {
        "states_checked": states_checked,
        "ambiguous_states": ambiguous_states,
        "projected_possible": projected_witness is not None,
        "nominal_possible": nominal_witness is not None,
        "projected_witness": projected_witness,
        "nominal_witness": nominal_witness,
    }


def _append(
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
            "Follow up the strict finite-fuel Tow phase-neither population by applying "
            "historically eligible ordinary warp wells to full-geometry, snapshot-fuel, "
            "and broad physical phase-fuel candidate endpoints. The discovery log must "
            "contain every phase_neither_possible example. Evidence mining only."
        )
    )
    parser.add_argument("--discovery-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()

    expected, cases = _parse_phase_neither(args.discovery_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in cases:
        by_game[int(item["game"])].append(item)

    totals: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    totals["phase_neither_input"] = expected

    print("===== FINITE-FUEL TOW WARP-WELL FOLLOW-UP =====")
    print("discovery_log=", args.discovery_log)
    print("phase_neither_input=", expected)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        snapshots = _snapshot_by_owner(prepared)
        imported_states: dict[tuple[int, int], Any] = {}
        game_counts = Counter()

        for item in by_game[game_id]:
            turn = int(item["turn"])
            tower_owner = int(item["tower_owner"])
            target_owner = int(item["target_owner"])
            tower_id = int(item["tower_ship"])
            target_id = int(item["target_ship"])
            tower_hull_id = int(item["tower_hull"])
            target_hull_id = int(item["target_hull"])
            warp = int(item["tower_warp"])
            origin = tuple(int(v) for v in item["origin"])
            waypoint = tuple(int(v) for v in item["waypoint"])
            observed = tuple(int(v) for v in item["observed"])
            geometry_endpoint = tuple(int(v) for v in item["geometry_endpoint"])
            max_distance = int(item["max_distance"])
            waypoint_distance = hypot(
                waypoint[0] - origin[0],
                waypoint[1] - origin[1],
            )
            true_partial = bool(item["true_partial"])
            requested_distance = float(max_distance) if true_partial else waypoint_distance
            projected_cost_distance = (
                hypot(
                    geometry_endpoint[0] - origin[0],
                    geometry_endpoint[1] - origin[1],
                )
                if true_partial
                else waypoint_distance
            )
            nominal_cost_distance = float(max_distance) if true_partial else waypoint_distance
            planets = planets_by_turn.get(turn, ())

            totals["cases"] += 1
            game_counts["cases"] += 1

            observed_planet_id = _planet_at(observed, planets)
            if observed_planet_id is not None:
                totals["observed_is_eligible_planet"] += 1
                game_counts["observed_is_eligible_planet"] += 1
            else:
                totals["observed_not_eligible_planet"] += 1
                game_counts["observed_not_eligible_planet"] += 1

            geometry_after, geometry_planet_id, geometry_ambiguous = _warp_well_endpoint(
                origin=origin,
                endpoint=geometry_endpoint,
                warp=warp,
                planets=planets,
            )
            if geometry_ambiguous:
                totals["geometry_warpwell_ambiguous"] += 1
            elif geometry_after == observed:
                totals["geometry_warpwell_exact"] += 1
                game_counts["geometry_warpwell_exact"] += 1

            snapshot_projected_endpoint = item.get("snapshot_projected_endpoint")
            snapshot_nominal_endpoint = item.get("snapshot_nominal_endpoint")
            projected_snapshot_tuple = (
                tuple(int(v) for v in snapshot_projected_endpoint)
                if snapshot_projected_endpoint is not None
                else None
            )
            nominal_snapshot_tuple = (
                tuple(int(v) for v in snapshot_nominal_endpoint)
                if snapshot_nominal_endpoint is not None
                else None
            )
            (
                snapshot_projected_after,
                snapshot_projected_planet,
                snapshot_projected_ambiguous,
            ) = _warp_well_endpoint(
                origin=origin,
                endpoint=projected_snapshot_tuple,
                warp=warp,
                planets=planets,
            )
            (
                snapshot_nominal_after,
                snapshot_nominal_planet,
                snapshot_nominal_ambiguous,
            ) = _warp_well_endpoint(
                origin=origin,
                endpoint=nominal_snapshot_tuple,
                warp=warp,
                planets=planets,
            )
            if snapshot_projected_ambiguous or snapshot_nominal_ambiguous:
                totals["snapshot_warpwell_ambiguous"] += 1

            snapshot_projected_exact = snapshot_projected_after == observed
            snapshot_nominal_exact = snapshot_nominal_after == observed
            if snapshot_projected_exact and snapshot_nominal_exact:
                totals["snapshot_warpwell_both_exact"] += 1
            elif snapshot_nominal_exact:
                totals["snapshot_warpwell_nominal_only"] += 1
            elif snapshot_projected_exact:
                totals["snapshot_warpwell_projected_only"] += 1
            else:
                totals["snapshot_warpwell_neither"] += 1

            tower_snapshot = snapshots.get((turn, tower_owner))
            target_snapshot = snapshots.get((turn, target_owner))
            if tower_snapshot is None or target_snapshot is None:
                totals["owner_snapshot_missing"] += 1
                continue

            tower_key = (turn, tower_owner)
            target_key = (turn, target_owner)
            if tower_key not in imported_states:
                imported_states[tower_key] = tower_snapshot.import_state()
            if target_key not in imported_states:
                imported_states[target_key] = target_snapshot.import_state()
            tower_ship = imported_states[tower_key].ships.get(tower_id)
            target_ship = imported_states[target_key].ships.get(target_id)
            if tower_ship is None or target_ship is None:
                totals["imported_ship_missing"] += 1
                continue

            tower_hull = specs.hulls.get(tower_hull_id)
            target_hull = specs.hulls.get(target_hull_id)
            if tower_hull is None or target_hull is None:
                totals["hull_spec_missing"] += 1
                continue
            if tower_ship.engine_id is None or tower_ship.engine_id not in specs.engines:
                totals["engine_spec_missing"] += 1
                continue

            tower_mass = ship_movement_mass(tower_ship, specs)
            target_mass = ship_movement_mass(target_ship, specs)
            tower_fuel = int(tower_ship.cargo.neutronium)
            target_fuel = int(target_ship.cargo.neutronium)
            tower_nonfuel_mass = tower_mass - tower_fuel
            target_nonfuel_mass = target_mass - target_fuel
            fuel_factor = specs.engines[tower_ship.engine_id].fuel_factor(warp)

            phase = _phase_warpwell_envelope(
                origin=origin,
                waypoint=waypoint,
                observed=observed,
                geometry_endpoint=geometry_endpoint,
                requested_distance=requested_distance,
                max_distance=max_distance,
                projected_cost_distance=projected_cost_distance,
                nominal_cost_distance=nominal_cost_distance,
                warp=warp,
                fuel_factor=fuel_factor,
                tower_nonfuel_mass=tower_nonfuel_mass,
                target_nonfuel_mass=target_nonfuel_mass,
                tower_fuel_tank=tower_hull.fuel_tank,
                target_fuel_tank=target_hull.fuel_tank,
                planets=planets,
            )
            projected_possible = bool(phase["projected_possible"])
            nominal_possible = bool(phase["nominal_possible"])
            if projected_possible and nominal_possible:
                bucket = "phase_warpwell_both_possible"
            elif nominal_possible:
                bucket = "phase_warpwell_nominal_only_possible"
            elif projected_possible:
                bucket = "phase_warpwell_projected_only_possible"
            else:
                bucket = "phase_warpwell_neither_possible"
            totals[bucket] += 1
            game_counts[bucket] += 1
            if int(phase["ambiguous_states"]) > 0:
                totals["phase_warpwell_ambiguous_cases"] += 1

            result = {
                "game": game_id,
                "turn": turn,
                "after_turn": int(item["after_turn"]),
                "tower_ship": tower_id,
                "target_ship": target_id,
                "origin": origin,
                "waypoint": waypoint,
                "observed": observed,
                "observed_planet_id": observed_planet_id,
                "geometry_endpoint": geometry_endpoint,
                "geometry_warpwell_endpoint": geometry_after,
                "geometry_warpwell_planet_id": geometry_planet_id,
                "snapshot_tower_fuel": int(item["snapshot_tower_fuel"]),
                "snapshot_projected_endpoint": projected_snapshot_tuple,
                "snapshot_projected_warpwell_endpoint": snapshot_projected_after,
                "snapshot_projected_warpwell_planet_id": snapshot_projected_planet,
                "snapshot_nominal_endpoint": nominal_snapshot_tuple,
                "snapshot_nominal_warpwell_endpoint": snapshot_nominal_after,
                "snapshot_nominal_warpwell_planet_id": snapshot_nominal_planet,
                "phase_states_checked": int(phase["states_checked"]),
                "phase_warpwell_ambiguous_states": int(phase["ambiguous_states"]),
                "phase_projected_witness": phase["projected_witness"],
                "phase_nominal_witness": phase["nominal_witness"],
            }
            _append(examples, bucket, result, args.examples)
            if geometry_after == observed:
                _append(examples, "geometry_warpwell_exact", result, args.examples)

        print(
            {
                "game": game_id,
                "cache_hit": cache_hit,
                **dict(sorted(game_counts.items())),
            },
            flush=True,
        )

    if totals["cases"] != totals["phase_neither_input"]:
        raise AssertionError(
            f"case accounting mismatch: input={totals['phase_neither_input']} cases={totals['cases']}"
        )

    print("\n===== SUMMARY =====")
    for key in (
        "phase_neither_input",
        "cases",
        "observed_is_eligible_planet",
        "observed_not_eligible_planet",
        "geometry_warpwell_exact",
        "geometry_warpwell_ambiguous",
        "snapshot_warpwell_both_exact",
        "snapshot_warpwell_nominal_only",
        "snapshot_warpwell_projected_only",
        "snapshot_warpwell_neither",
        "snapshot_warpwell_ambiguous",
        "phase_warpwell_both_possible",
        "phase_warpwell_nominal_only_possible",
        "phase_warpwell_projected_only_possible",
        "phase_warpwell_neither_possible",
        "phase_warpwell_ambiguous_cases",
        "owner_snapshot_missing",
        "imported_ship_missing",
        "hull_spec_missing",
        "engine_spec_missing",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== EXAMPLES =====")
    for bucket in (
        "phase_warpwell_nominal_only_possible",
        "phase_warpwell_projected_only_possible",
        "phase_warpwell_both_possible",
        "geometry_warpwell_exact",
        "phase_warpwell_neither_possible",
    ):
        print(f"-- {bucket} --")
        for item in examples[bucket]:
            print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "This pass starts only from the direct phase_neither_possible population and "
        "adds ordinary warp-well capture using the historical per-turn eligible-planet set."
    )
    print(
        "A post-warp-well nominal-only or projected-only result is a discovery signature, "
        "not promotion: transfer/mine/storm/damage/Chunnel and phase-state attribution remain open."
    )
    print(
        "Cases that remain phase_warpwell_neither_possible are the priority population for "
        "the next external-mechanics and non-fuel-transfer audit."
    )
    print("finite-fuel Tow remains OPEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
