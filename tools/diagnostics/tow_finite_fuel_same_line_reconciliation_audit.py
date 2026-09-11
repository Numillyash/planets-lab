from __future__ import annotations

import argparse
import ast
import re
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any

from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.mass import ship_movement_mass
from planets_lab.rules.movement import max_nominal_distance

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _mass_state_complete,
    _post_reset,
    _snapshot_by_owner,
)
from tow_finite_fuel_population_audit import _fuel_endpoint, _phase_fuel_envelope


EXPECTED_GAME = 360690
EXPECTED_CASES = 3


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _same_line_cases(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    if _counter(text, "cases") != 7:
        raise ValueError("unexpected break-independent case count")
    if _counter(text, "same_line_rows") != EXPECTED_CASES:
        raise ValueError("unexpected same-line checkpoint")
    if _counter(text, "neither_independent_exact") != 7:
        raise ValueError("independent-navigation checkpoint no longer matches")
    if _counter(text, "nonfuel_lock_proven") != 7:
        raise ValueError("non-fuel Tow-lock checkpoint no longer matches")

    try:
        block = text.split("===== CASES =====", 1)[1].split(
            "===== INTERPRETATION =====", 1
        )[0]
    except IndexError as exc:
        raise ValueError("break-independent log has no CASES block") from exc

    result: list[dict[str, Any]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        item = ast.literal_eval(line)
        if not isinstance(item, dict):
            continue
        if item.get("direction") == "same_line_route":
            result.append(item)

    if len(result) != EXPECTED_CASES:
        raise ValueError(f"parsed same-line cases={len(result)} expected={EXPECTED_CASES}")
    if {int(item["game"]) for item in result} != {EXPECTED_GAME}:
        raise ValueError("same-line population moved to an unexpected game")
    return tuple(sorted(result, key=lambda item: int(item["turn"])))


def _intish(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _owner_raw(ship_groups: Any, turn: int, ship_id: int) -> tuple[int | None, Any | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _snapshot_prediction(
    *,
    origin: tuple[int, int],
    waypoint: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    gravitonic: bool,
    fuel_factor: int,
    tower_mass: int,
    target_mass: int,
    tower_fuel: int,
) -> dict[str, Any]:
    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    waypoint_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
    true_partial = waypoint_distance > max_distance
    if true_partial:
        raise ValueError("same-line reconciliation unexpectedly contains a true-partial route")

    combined_required = movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=tower_mass + target_mass,
        distance_traveled=waypoint_distance,
        max_distance_per_turn=max_distance,
    )
    tower_only_required = movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=tower_mass,
        distance_traveled=waypoint_distance,
        max_distance_per_turn=max_distance,
    )
    combined_endpoint = _fuel_endpoint(
        origin=origin,
        waypoint=waypoint,
        geometry_endpoint=waypoint,
        requested_distance=waypoint_distance,
        fuel_available=tower_fuel,
        fuel_required=combined_required,
    )
    tower_only_endpoint = _fuel_endpoint(
        origin=origin,
        waypoint=waypoint,
        geometry_endpoint=waypoint,
        requested_distance=waypoint_distance,
        fuel_available=tower_fuel,
        fuel_required=tower_only_required,
    )
    return {
        "max_distance": max_distance,
        "waypoint_distance": round(waypoint_distance, 6),
        "combined_required": combined_required,
        "combined_endpoint": combined_endpoint,
        "combined_exact": combined_endpoint == observed,
        "tower_only_required": tower_only_required,
        "tower_only_endpoint": tower_only_endpoint,
        "tower_only_exact": tower_only_endpoint == observed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile the exact three post-context same-line finite-fuel Tow rows. "
            "The audit compares the existing physical phase-fuel envelope under combined "
            "tower+target movement mass against a tower-only counterfactual. Snapshot and "
            "post-turn fuel are supporting observations only, not automatic Tow-phase facts."
        )
    )
    parser.add_argument("--break-log", type=Path, required=True)
    args = parser.parse_args()

    cases = _same_line_cases(args.break_log)
    archive_path = RAW_DIR / f"game-{EXPECTED_GAME}.zip"
    cache_path = PREPARED_DIR / f"game-{EXPECTED_GAME}.pickle"
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    if not cache_path.is_file():
        raise FileNotFoundError(f"{cache_path}; bounded follow-up does not rebuild caches")

    archive_data = archive_path.read_bytes()
    prepared, cache_hit = load_or_build_prepared_game_cache(
        archive_data,
        game_id=EXPECTED_GAME,
        cache_path=cache_path,
    )
    specs = _static_specs(archive_data)
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    snapshots = _snapshot_by_owner(prepared)

    totals: Counter[str] = Counter(same_line_input=len(cases))
    output: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW SAME-LINE FUEL RECONCILIATION =====")
    print("break_log=", args.break_log)
    print("same_line_input=", len(cases))
    print("game=", EXPECTED_GAME, "cache_hit=", cache_hit)

    for case in cases:
        turn = int(case["turn"])
        after_turn = turn + 1
        tower_id = int(case["tower_ship"])
        target_id = int(case["target_ship"])
        tower_ctx = case["tower"]
        origin = tuple(int(v) for v in tower_ctx["origin"])
        waypoint = tuple(int(v) for v in tower_ctx["waypoint"])
        observed = tuple(int(v) for v in case["observed"])
        warp = int(tower_ctx["warp"])
        gravitonic = bool(tower_ctx["gravitonic"])

        tower_owner, tower_before = _owner_raw(ship_groups, turn, tower_id)
        target_owner, target_before = _owner_raw(ship_groups, turn, target_id)
        tower_after_owner, tower_after = _owner_raw(ship_groups, after_turn, tower_id)
        target_after_owner, target_after = _owner_raw(ship_groups, after_turn, target_id)
        if tower_owner is None or target_owner is None or tower_before is None or target_before is None:
            raise ValueError(f"T{turn}: owner-visible before state missing")
        if tower_owner != target_owner:
            raise ValueError(f"T{turn}: same-line bounded pass expects same-owner Tow pair")
        if not _mass_state_complete(tower_before) or not _mass_state_complete(target_before):
            raise ValueError(f"T{turn}: mass state incomplete")

        snapshot = snapshots.get((turn, tower_owner))
        if snapshot is None:
            raise ValueError(f"T{turn}: owner snapshot missing")
        state = snapshot.import_state()
        tower_ship = state.ships.get(tower_id)
        target_ship = state.ships.get(target_id)
        if tower_ship is None or target_ship is None:
            raise ValueError(f"T{turn}: Tow pair missing from owner import")

        tower_mass = ship_movement_mass(tower_ship, specs)
        target_mass = ship_movement_mass(target_ship, specs)
        tower_snapshot_fuel = int(tower_ship.cargo.neutronium)
        target_snapshot_fuel = int(target_ship.cargo.neutronium)
        tower_nonfuel_mass = tower_mass - tower_snapshot_fuel
        target_nonfuel_mass = target_mass - target_snapshot_fuel

        tower_hull = specs.hulls.get(tower_ship.hull_id)
        target_hull = specs.hulls.get(target_ship.hull_id)
        if tower_hull is None or target_hull is None:
            raise ValueError(f"T{turn}: hull spec missing")
        if tower_ship.engine_id is None or tower_ship.engine_id not in specs.engines:
            raise ValueError(f"T{turn}: tower engine spec missing")
        fuel_factor = specs.engines[tower_ship.engine_id].fuel_factor(warp)

        combined = _phase_fuel_envelope(
            origin=origin,
            waypoint=waypoint,
            observed=observed,
            warp=warp,
            gravitonic=gravitonic,
            fuel_factor=fuel_factor,
            tower_nonfuel_mass=tower_nonfuel_mass,
            target_nonfuel_mass=target_nonfuel_mass,
            tower_fuel_tank=tower_hull.fuel_tank,
            target_fuel_tank=target_hull.fuel_tank,
        )
        tower_only = _phase_fuel_envelope(
            origin=origin,
            waypoint=waypoint,
            observed=observed,
            warp=warp,
            gravitonic=gravitonic,
            fuel_factor=fuel_factor,
            tower_nonfuel_mass=tower_nonfuel_mass,
            target_nonfuel_mass=0,
            tower_fuel_tank=tower_hull.fuel_tank,
            target_fuel_tank=0,
        )
        if combined["true_partial"] or tower_only["true_partial"]:
            raise ValueError(f"T{turn}: same-line route unexpectedly true-partial")
        if combined["projected_possible"] != combined["nominal_possible"]:
            raise AssertionError(f"T{turn}: reachable combined projected/nominal mismatch")
        if tower_only["projected_possible"] != tower_only["nominal_possible"]:
            raise AssertionError(f"T{turn}: reachable tower-only projected/nominal mismatch")

        combined_possible = bool(combined["nominal_possible"])
        tower_only_possible = bool(tower_only["nominal_possible"])
        if combined_possible and not tower_only_possible:
            envelope_class = "combined_only"
        elif combined_possible and tower_only_possible:
            envelope_class = "both_models"
        elif tower_only_possible:
            envelope_class = "tower_only_only"
        else:
            envelope_class = "neither_model"
        totals[envelope_class] += 1

        snapshot_prediction = _snapshot_prediction(
            origin=origin,
            waypoint=waypoint,
            observed=observed,
            warp=warp,
            gravitonic=gravitonic,
            fuel_factor=fuel_factor,
            tower_mass=tower_mass,
            target_mass=target_mass,
            tower_fuel=tower_snapshot_fuel,
        )
        if snapshot_prediction["combined_exact"]:
            totals["snapshot_combined_exact"] += 1
        if snapshot_prediction["tower_only_exact"]:
            totals["snapshot_tower_only_exact"] += 1

        tower_after_fuel = _intish(tower_after.get("neutronium")) if tower_after is not None else None
        target_after_fuel = _intish(target_after.get("neutronium")) if target_after is not None else None
        same_tower_identity = tower_after_owner == tower_owner and tower_after is not None
        same_target_identity = target_after_owner == target_owner and target_after is not None
        reset_support = bool(same_tower_identity and _post_reset(tower_after, observed))
        if tower_after_fuel == 0 and same_tower_identity:
            totals["tower_after_fuel_zero"] += 1
        if reset_support:
            totals["tower_after_reset_supporting_only"] += 1

        totals["cases"] += 1
        detail = {
            "game": EXPECTED_GAME,
            "turn": turn,
            "tower_ship": tower_id,
            "target_ship": target_id,
            "origin": origin,
            "waypoint": waypoint,
            "observed": observed,
            "warp": warp,
            "fuel_factor": fuel_factor,
            "tower_mass_snapshot": tower_mass,
            "target_mass_snapshot": target_mass,
            "combined_mass_snapshot": tower_mass + target_mass,
            "tower_nonfuel_mass": tower_nonfuel_mass,
            "target_nonfuel_mass": target_nonfuel_mass,
            "tower_fuel_tank": tower_hull.fuel_tank,
            "target_fuel_tank": target_hull.fuel_tank,
            "tower_snapshot_fuel": tower_snapshot_fuel,
            "target_snapshot_fuel": target_snapshot_fuel,
            "tower_after_fuel": tower_after_fuel,
            "target_after_fuel": target_after_fuel,
            "same_tower_identity_after": same_tower_identity,
            "same_target_identity_after": same_target_identity,
            "tower_after_reset_supporting_only": reset_support,
            "snapshot_prediction": snapshot_prediction,
            "combined_phase_envelope": combined,
            "tower_only_phase_envelope": tower_only,
            "envelope_class": envelope_class,
        }
        output.append(detail)
        print(detail, flush=True)

    if totals["cases"] != EXPECTED_CASES:
        raise AssertionError("case accounting mismatch")
    if sum(totals[key] for key in ("combined_only", "both_models", "tower_only_only", "neither_model")) != EXPECTED_CASES:
        raise AssertionError("envelope accounting mismatch")

    print("\n===== SUMMARY =====")
    for key in (
        "same_line_input",
        "cases",
        "combined_only",
        "both_models",
        "tower_only_only",
        "neither_model",
        "snapshot_combined_exact",
        "snapshot_tower_only_exact",
        "tower_after_fuel_zero",
        "tower_after_reset_supporting_only",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== INTERPRETATION =====")
    print(
        "All three rows are reachable-waypoint routes, so projected-vs-nominal partial-leg cost basis is not discriminating here."
    )
    print(
        "combined_only is a bounded historical lead for including the towed ship in Tow movement mass; both_models is non-discriminating."
    )
    print(
        "Snapshot and post-turn fuel/reset observations are supporting evidence only. They do not convert snapshot neutronium into Tow-phase fuel."
    )
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
