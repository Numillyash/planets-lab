from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from planets_lab.sim.normal_movement import plan_full_normal_move

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import (
    DEFAULT_DATABASE,
    INTERCEPT_MISSION_ID,
    PREPARED_DIR,
    RAW_DIR,
    TOW_MISSION_ID,
    _geometry_endpoint,
    _mass_state_complete,
    _mission,
    _settings_unlimited_fuel,
    _snapshot_by_owner,
    _target_id,
)
from mine_hit_hostorder_differential_audit import _owner_states


ORDER_FIELD_TOKENS = (
    "transfer",
    "neutron",
    "fuel",
    "beamup",
    "unload",
    "load",
)


def _raw_int(raw: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in raw:
            value = _intish(raw.get(key))
            if value is not None:
                return value
    return None


def _owner_snapshot_raw_ships(snapshot: Any) -> tuple[Mapping[str, Any], ...]:
    payload = snapshot.mechanics_payload
    ships = payload.get("ships", ()) if isinstance(payload, Mapping) else ()
    if not isinstance(ships, Sequence) or isinstance(ships, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in ships if isinstance(item, Mapping))


def _owner_snapshot_raw_planets(snapshot: Any) -> tuple[Mapping[str, Any], ...]:
    payload = snapshot.mechanics_payload
    planets = payload.get("planets", ()) if isinstance(payload, Mapping) else ()
    if not isinstance(planets, Sequence) or isinstance(planets, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in planets if isinstance(item, Mapping))


def _mechanical_order_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in sorted(raw.items(), key=lambda item: str(item[0])):
        normalized = str(key).lower()
        if not any(token in normalized for token in ORDER_FIELD_TOKENS):
            continue
        if normalized == "neutronium":
            continue
        if value in (None, "", 0, False, [], {}):
            continue
        if isinstance(value, (str, int, float, bool)):
            result[str(key)] = value
    return result


def _friendly_code_class(raw: Mapping[str, Any]) -> str:
    value = raw.get("friendlycode", raw.get("friendly_code", ""))
    if not isinstance(value, str):
        return "missing"
    value = value.strip().lower()
    if not value:
        return "empty"
    if value == "hyp":
        return "hyp"
    if value.isdigit() and len(value) <= 3:
        return "numeric"
    return "other"


def _transfer_target(raw: Mapping[str, Any]) -> int | None:
    preferred = (
        "transfertargetid",
        "transfer_target_id",
        "transfertarget",
        "transfer_target",
    )
    value = _raw_int(raw, *preferred)
    if value is not None and value > 0:
        return value
    for key, raw_value in raw.items():
        normalized = str(key).lower()
        if "transfer" in normalized and "target" in normalized:
            value = _intish(raw_value)
            if value is not None and value > 0:
                return value
    return None


def _transfer_neutronium(raw: Mapping[str, Any]) -> int | None:
    preferred = (
        "transferneutronium",
        "transfer_neutronium",
        "transferfuel",
        "transfer_fuel",
    )
    value = _raw_int(raw, *preferred)
    if value is not None:
        return value
    for key, raw_value in raw.items():
        normalized = str(key).lower()
        if "transfer" in normalized and ("neutron" in normalized or "fuel" in normalized):
            value = _intish(raw_value)
            if value is not None:
                return value
    return None


def _compress_int_ranges(values: Sequence[int]) -> tuple[tuple[int, int], ...]:
    if not values:
        return ()
    ordered = sorted(set(int(value) for value in values))
    ranges: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return tuple(ranges)


def _phase_fuel_scan(
    interceptor: Any,
    specs: Any,
    *,
    target_final: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    gravitonic: bool,
    scan_cap: int,
) -> dict[str, Any]:
    exact_fuels: list[int] = []
    exact_post_fuels: list[int] = []
    first_full_geometry_fuel: int | None = None
    first_executable_fuel: int | None = None
    plan_errors = 0

    for phase_fuel in range(scan_cap + 1):
        candidate = deepcopy(interceptor)
        candidate.cargo.neutronium = phase_fuel
        try:
            plan = plan_full_normal_move(
                candidate,
                specs,
                target_x=int(target_final[0]),
                target_y=int(target_final[1]),
                warp=warp,
                gravitonic=gravitonic,
                allow_partial=True,
                allow_fuel_proration=True,
            )
        except (KeyError, ValueError):
            plan_errors += 1
            continue
        if not plan.executable:
            continue
        if first_executable_fuel is None:
            first_executable_fuel = phase_fuel
        endpoint = (plan.destination_x, plan.destination_y)
        if endpoint == target_final and first_full_geometry_fuel is None:
            first_full_geometry_fuel = phase_fuel
        if endpoint == observed:
            exact_fuels.append(phase_fuel)
            exact_post_fuels.append(phase_fuel - plan.fuel_used)

    return {
        "scan_cap": scan_cap,
        "plan_errors": plan_errors,
        "first_executable_phase_fuel": first_executable_fuel,
        "first_full_geometry_phase_fuel": first_full_geometry_fuel,
        "observed_endpoint_phase_fuel_ranges": _compress_int_ranges(exact_fuels),
        "observed_endpoint_post_fuel_ranges": _compress_int_ranges(exact_post_fuels),
        "observed_endpoint_min_phase_fuel": min(exact_fuels) if exact_fuels else None,
        "observed_endpoint_max_phase_fuel": max(exact_fuels) if exact_fuels else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Drill into historical finite-fuel Intercept cases after the broad differential. "
            "For each strict snapshot-fuel-limited candidate, scan hypothetical fuel at the "
            "actual Intercept phase while recomputing movement mass, compare the next factual "
            "fuel state, and expose only mechanical same-location evidence for possible earlier "
            "Host fuel mutations such as ship transfers. This is diagnostic evidence only."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--fuel-scan-cap", type=int, default=5000)
    args = parser.parse_args()
    if args.fuel_scan_cap < 0:
        parser.error("--fuel-scan-cap must be non-negative")

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
    cases: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            continue
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        specs = _static_specs(archive_data)
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True or _settings_unlimited_fuel(archive_data) is True:
            continue

        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }

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
            plan = plan_full_normal_move(
                interceptor,
                specs,
                target_x=target_final[0],
                target_y=target_final[1],
                warp=warp,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                allow_partial=True,
                allow_fuel_proration=True,
            )
            if not plan.fuel_limited:
                continue

            totals["strict_snapshot_fuel_limited"] += 1
            snapshot_fuel = _intish(before_raw.get("neutronium"))
            after_fuel = _intish(after_raw.get("neutronium"))
            geometry_endpoint = _geometry_endpoint(
                x=origin[0],
                y=origin[1],
                target_x=target_final[0],
                target_y=target_final[1],
                warp=warp,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
            )
            fuel_endpoint = (
                (plan.destination_x, plan.destination_y)
                if plan.executable
                else None
            )

            scan = _phase_fuel_scan(
                interceptor,
                specs,
                target_final=target_final,
                observed=observed,
                warp=warp,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                scan_cap=args.fuel_scan_cap,
            )
            min_phase_fuel = scan["observed_endpoint_min_phase_fuel"]
            snapshot_to_min_delta = (
                min_phase_fuel - snapshot_fuel
                if min_phase_fuel is not None and snapshot_fuel is not None
                else None
            )

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
                    transfer_fuel = _transfer_neutronium(raw_ship)
                    incoming_transfer_candidates.append(
                        {
                            "source_ship": other_id,
                            "source_owner": summary["owner"],
                            "transfer_neutronium": transfer_fuel,
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
                        }
                    )

            post_fuel_ranges = scan["observed_endpoint_post_fuel_ranges"]
            after_fuel_consistent = False
            if after_fuel is not None:
                after_fuel_consistent = any(
                    low <= after_fuel <= high for low, high in post_fuel_ranges
                )
            if after_fuel_consistent:
                totals["after_fuel_consistent_with_some_exact_phase_fuel"] += 1
            if incoming_transfer_candidates:
                totals["visible_incoming_transfer_candidate"] += 1
            if incoming_tow_tower_ids:
                totals["visible_incoming_tow_candidate"] += 1

            cases.append(
                {
                    "game": game_id,
                    "turn": before_turn,
                    "after_turn": after_turn,
                    "ship": ship_id,
                    "hull": hull_id,
                    "warp": warp,
                    "target_ship": target_id,
                    "origin": origin,
                    "target_final_observed": target_final,
                    "observed": observed,
                    "observed_distance": round(hypot(observed[0] - origin[0], observed[1] - origin[1]), 3),
                    "snapshot_fuel": snapshot_fuel,
                    "after_fuel": after_fuel,
                    "snapshot_mass": plan.total_mass,
                    "snapshot_required_fuel": plan.fuel_required,
                    "snapshot_plan_executable": plan.executable,
                    "snapshot_plan_reason": plan.reason,
                    "geometry_endpoint": geometry_endpoint,
                    "snapshot_fuel_endpoint": fuel_endpoint,
                    "geometry_exact": geometry_endpoint == observed,
                    "snapshot_fuel_exact": fuel_endpoint == observed if fuel_endpoint is not None else False,
                    "phase_scan": scan,
                    "snapshot_to_min_exact_phase_fuel_delta": snapshot_to_min_delta,
                    "after_fuel_consistent_with_some_exact_phase_fuel": after_fuel_consistent,
                    "interceptor_order_fields": _mechanical_order_fields(before_raw),
                    "interceptor_friendly_code_class": _friendly_code_class(before_raw),
                    "visible_incoming_transfer_candidates": incoming_transfer_candidates,
                    "visible_incoming_tow_tower_ids": tuple(sorted(incoming_tow_tower_ids)),
                    "colocated_planets": colocated_planets,
                    "colocated_ships": colocated_ships,
                }
            )

    print("===== INTERCEPT PHASE FUEL STATE AUDIT =====")
    print("strict_snapshot_fuel_limited=", totals["strict_snapshot_fuel_limited"])
    print(
        "after_fuel_consistent_with_some_exact_phase_fuel=",
        totals["after_fuel_consistent_with_some_exact_phase_fuel"],
    )
    print("visible_incoming_transfer_candidate=", totals["visible_incoming_transfer_candidate"])
    print("visible_incoming_tow_candidate=", totals["visible_incoming_tow_candidate"])
    print("fuel_scan_cap=", args.fuel_scan_cap)

    print("\n===== CASES =====")
    for case in cases:
        print(case)

    print("\n===== INTERPRETATION =====")
    print(
        "The phase-fuel scan recomputes movement mass for every hypothetical Intercept-phase "
        "fuel amount; it does not hold the pre-Host mass constant while changing fuel."
    )
    print(
        "A non-zero snapshot_to_min_exact_phase_fuel_delta is evidence that the pre-Host "
        "snapshot fuel cannot itself explain the observed endpoint under the candidate rule."
    )
    print(
        "Visible transfer/Tow candidates are only factual owner-visible mechanisms that may "
        "explain an earlier state mutation. Their absence does not prove no hidden mutation."
    )
    print(
        "Next-turn after_fuel consistency is supporting only: later Host phases may also alter "
        "state, so it is not treated as an Intercept phase boundary."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
