from __future__ import annotations

import argparse
import ast
import re
import sys
from math import hypot
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.sim.normal_movement import project_toward_waypoint


EXPECTED_GAME = 360690
EXPECTED_TURN = 41
EXPECTED_TOWER = 425
EXPECTED_TARGET = 353
OFFICIAL_FUEL_DETAILS = "https://help.planets.nu/fuel-details"
OFFICIAL_HOST_ORDER = "https://help.planets.nu/host-order"


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _dict_lines(text: str) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = ast.literal_eval(line)
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, dict):
            result.append(value)
    return tuple(result)


def _source_case(text: str) -> dict[str, Any]:
    if _counter(text, "cases") != 3:
        raise ValueError("unexpected context-resolution case count")
    if _counter(text, "bounded_web_damage_context_rows") != 2:
        raise ValueError("expected exactly two bounded web-context rows")
    if _counter(text, "alchemy_rows") != 1:
        raise ValueError("expected exactly one Alchemy row")
    if _counter(text, "alchemy_exact_cargo_signature_rows") != 1:
        raise ValueError("Alchemy exact cargo signature checkpoint moved")
    if _counter(text, "alchemy_adjusted_envelope_possible_rows") != 1:
        raise ValueError("Alchemy-adjusted envelope checkpoint moved")
    if _counter(text, "alchemy_adjusted_snapshot_exact_rows") != 1:
        raise ValueError("Alchemy-adjusted snapshot checkpoint moved")

    candidates = [
        item for item in _dict_lines(text)
        if item.get("resolution") == "alchemy_mass_phase_lead"
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one Alchemy case, got {len(candidates)}")
    case = candidates[0]
    identity = (
        int(case.get("game", -1)),
        int(case.get("turn", -1)),
        int(case.get("tower_ship", -1)),
        int(case.get("target_ship", -1)),
    )
    if identity != (EXPECTED_GAME, EXPECTED_TURN, EXPECTED_TOWER, EXPECTED_TARGET):
        raise ValueError(f"unexpected Alchemy case identity: {identity}")
    return case


def _stop_context_path(text: str, source: Path) -> Path:
    match = re.search(r"^stop_context_log=\s*(.+?)\s*$", text, re.M)
    if not match:
        raise ValueError("context-resolution log has no stop_context_log provenance")
    path = Path(match.group(1))
    if path.is_file():
        return path
    candidate = REPO_ROOT / path
    if candidate.is_file():
        return candidate
    sibling = source.parent.parent / path.name
    if sibling.is_file():
        return sibling
    raise FileNotFoundError(path)


def _stop_case(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    candidates = [
        item for item in _dict_lines(text)
        if (
            int(item.get("game", -1)) == EXPECTED_GAME
            and int(item.get("turn", -1)) == EXPECTED_TURN
            and int(item.get("tower_ship", -1)) == EXPECTED_TOWER
            and int(item.get("target_ship", -1)) == EXPECTED_TARGET
        )
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one T41 stop-context case, got {len(candidates)}")
    return candidates[0]


def _fuel_endpoint(
    *,
    origin: tuple[int, int],
    waypoint: tuple[int, int],
    fuel_available: int,
    fuel_required: int,
) -> tuple[int, int]:
    if fuel_required <= 0 or fuel_available >= fuel_required:
        return waypoint
    requested_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
    distance = requested_distance * fuel_available / fuel_required
    return project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=waypoint[0],
        target_y=waypoint[1],
        distance=distance,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile the cleaned T41 finite-fuel Tow row against the documented "
            "Nu movement-mass, Alchemy ordering and insufficient-fuel proration rules. "
            "This gate is deliberately bounded to the already-isolated historical row."
        )
    )
    parser.add_argument("--context-resolution-log", type=Path, required=True)
    args = parser.parse_args()

    text = args.context_resolution_log.read_text(encoding="utf-8")
    case = _source_case(text)
    stop_path = _stop_context_path(text, args.context_resolution_log)
    stop = _stop_case(stop_path)
    alchemy = case["alchemy"]

    origin = tuple(int(v) for v in stop["origin"])
    waypoint = tuple(int(v) for v in stop["waypoint"])
    observed = tuple(int(v) for v in stop["observed"])
    warp = 9
    max_distance = warp * warp
    fuel_factor = 8100

    adjusted = alchemy["adjusted_snapshot_prediction"]
    post_alchemy_combined_mass = int(adjusted["combined_mass"])
    tower_fuel = int(adjusted["tower_snapshot_fuel"])
    target_fuel = int(adjusted["target_snapshot_fuel"])
    mass_drop = int(alchemy["mass_drop_candidate"])
    target_nonfuel_after = int(alchemy["target_nonfuel_after"])
    target_mass_after = target_nonfuel_after + target_fuel
    tower_only_mass = post_alchemy_combined_mass - target_mass_after
    pre_alchemy_combined_mass = post_alchemy_combined_mass + mass_drop

    if not bool(alchemy["exact_cargo_signature"]):
        raise ValueError("T41 no longer has the exact Alchemy cargo signature")
    if not bool(alchemy["full_conversion_mass_hypothesis"]):
        raise ValueError("T41 full-conversion mass checkpoint moved")
    if int(alchemy["supply_drop"]) != 2700 or int(alchemy["mineral_gain"]) != 900:
        raise ValueError("T41 Alchemy cargo delta moved")
    if mass_drop != 1800:
        raise ValueError("T41 Alchemy mass-drop candidate moved")

    route_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
    if route_distance >= max_distance:
        raise ValueError("T41 is no longer a reachable-waypoint route")

    def model(total_mass: int) -> dict[str, Any]:
        required = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=total_mass,
            distance_traveled=route_distance,
            max_distance_per_turn=max_distance,
        )
        endpoint = _fuel_endpoint(
            origin=origin,
            waypoint=waypoint,
            fuel_available=tower_fuel,
            fuel_required=required,
        )
        return {
            "total_mass": total_mass,
            "fuel_required": required,
            "fuel_available": tower_fuel,
            "endpoint": endpoint,
            "exact": endpoint == observed,
        }

    pre_alchemy_combined = model(pre_alchemy_combined_mass)
    post_alchemy_combined = model(post_alchemy_combined_mass)
    post_alchemy_tower_only = model(tower_only_mass)

    if int(adjusted["fuel_required"]) != post_alchemy_combined["fuel_required"]:
        raise ValueError("source adjusted fuel requirement disagrees with independent recomputation")
    if tuple(int(v) for v in adjusted["endpoint"]) != post_alchemy_combined["endpoint"]:
        raise ValueError("source adjusted endpoint disagrees with independent recomputation")

    alchemy_basis_discriminator = (
        post_alchemy_combined["exact"] and not pre_alchemy_combined["exact"]
    )
    combined_mass_discriminator = (
        post_alchemy_combined["exact"] and not post_alchemy_tower_only["exact"]
    )

    print("===== FINITE-FUEL TOW DOCUMENTED RECONCILIATION =====")
    print("context_resolution_log=", args.context_resolution_log)
    print("stop_context_log=", stop_path)
    print("official_fuel_details=", OFFICIAL_FUEL_DETAILS)
    print("official_host_order=", OFFICIAL_HOST_ORDER)
    print("documented_claims=", (
        "towed_ship_mass_included",
        "alchemy_before_movement_mass_check",
        "insufficient_fuel_distance_prorated",
    ))
    print({
        "game": EXPECTED_GAME,
        "turn": EXPECTED_TURN,
        "tower_ship": EXPECTED_TOWER,
        "target_ship": EXPECTED_TARGET,
        "origin": origin,
        "waypoint": waypoint,
        "observed": observed,
        "route_distance": route_distance,
        "fuel_factor": fuel_factor,
        "alchemy": {
            "supply_drop": int(alchemy["supply_drop"]),
            "mineral_gain": int(alchemy["mineral_gain"]),
            "mass_drop": mass_drop,
        },
        "pre_alchemy_combined": pre_alchemy_combined,
        "post_alchemy_combined": post_alchemy_combined,
        "post_alchemy_tower_only": post_alchemy_tower_only,
        "alchemy_mass_basis_discriminator": alchemy_basis_discriminator,
        "combined_mass_discriminator": combined_mass_discriminator,
    })

    print("\n===== SUMMARY =====")
    print("cases= 1")
    print(f"pre_alchemy_combined_exact= {int(pre_alchemy_combined['exact'])}")
    print(f"post_alchemy_combined_exact= {int(post_alchemy_combined['exact'])}")
    print(f"post_alchemy_tower_only_exact= {int(post_alchemy_tower_only['exact'])}")
    print(f"alchemy_mass_basis_discriminator= {int(alchemy_basis_discriminator)}")
    print(f"combined_mass_discriminator= {int(combined_mass_discriminator)}")

    if not alchemy_basis_discriminator or not combined_mass_discriminator:
        raise AssertionError("T41 no longer discriminates documented post-Alchemy combined-mass Tow proration")

    print("\n===== INTERPRETATION =====")
    print("Official Nu documentation supplies the rule semantics; this historical row tests those semantics against a cleaned finite-fuel Tow transition.")
    print("T41 discriminates post-Alchemy combined tower+towed mass from both pre-Alchemy mass and tower-only mass under proportional insufficient-fuel movement.")
    print("This gate does not resolve web-hit RNG, Tow contests/chains, or every Tow phase interaction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
