from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS, _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.mass import ship_movement_mass
from planets_lab.rules.movement import max_nominal_distance

from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR, _snapshot_by_owner
from tow_finite_fuel_population_audit import _fuel_endpoint, _phase_fuel_envelope


EXPECTED_GAME = 360690
EXPECTED_TURNS = (41, 44, 185)


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _cases(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    if _counter(text, "cases") != 3:
        raise ValueError("unexpected stop-context case count")
    if _counter(text, "lead:damage_backed_visible_mine_context") != 2:
        raise ValueError("unexpected web/mine-context checkpoint")
    if _counter(text, "lead:no_visible_mine_or_damage_lead") != 1:
        raise ValueError("unexpected clean-row checkpoint")

    prefix = text.split("===== SUMMARY =====", 1)[0]
    result: list[dict[str, Any]] = []
    for raw_line in prefix.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            continue
        if {"game", "turn", "tower_ship", "target_ship", "lead"}.issubset(value):
            result.append(value)

    if len(result) != 3:
        raise ValueError(f"parsed cases={len(result)} expected=3")
    if {int(item["game"]) for item in result} != {EXPECTED_GAME}:
        raise ValueError("unexpected game in stop-context population")
    turns = tuple(sorted(int(item["turn"]) for item in result))
    if turns != EXPECTED_TURNS:
        raise ValueError(f"unexpected turns={turns}")
    return tuple(sorted(result, key=lambda item: int(item["turn"])))


def _owner_raw(ship_groups: Any, turn: int, ship_id: int) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, owner.raw if owner is not None else None


def _raw_int(raw: Mapping[str, Any], key: str) -> int | None:
    return _intish(raw.get(key))


def _mineral_total(raw: Mapping[str, Any]) -> int | None:
    values = [_raw_int(raw, key) for key in ("duranium", "tritanium", "molybdenum")]
    if any(value is None for value in values):
        return None
    return sum(int(value) for value in values if value is not None)


def _web_context(case: Mapping[str, Any]) -> dict[str, Any]:
    tower_damage = case.get("tower_damage")
    if not isinstance(tower_damage, Mapping):
        raise ValueError(f"T{case['turn']}: tower_damage missing")
    web_hits = tuple(int(value) for value in tower_damage.get("web_hit_candidates", ()))
    web_crossings = tuple(case.get("visible_web_crossings", ()))
    web_at_observed = tuple(case.get("visible_web_at_observed", ()))
    exact_one_web_quantum = web_hits == (1,)
    bounded_context = bool(exact_one_web_quantum and web_crossings and web_at_observed)
    return {
        "exact_one_web_quantum": exact_one_web_quantum,
        "visible_web_crossings": len(web_crossings),
        "visible_web_at_observed": len(web_at_observed),
        "bounded_web_damage_context": bounded_context,
    }


def _alchemy_resolution(
    *,
    case: Mapping[str, Any],
    prepared: Any,
    specs: Any,
    ship_groups: Any,
    snapshots: Any,
) -> dict[str, Any]:
    turn = int(case["turn"])
    after_turn = turn + 1
    tower_id = int(case["tower_ship"])
    target_id = int(case["target_ship"])
    origin = tuple(int(v) for v in case["origin"])
    waypoint = tuple(int(v) for v in case["waypoint"])
    observed = tuple(int(v) for v in case["observed"])

    tower_owner, tower_before_raw = _owner_raw(ship_groups, turn, tower_id)
    target_owner, target_before_raw = _owner_raw(ship_groups, turn, target_id)
    target_after_owner, target_after_raw = _owner_raw(ship_groups, after_turn, target_id)
    if (
        tower_owner is None
        or target_owner is None
        or target_after_owner is None
        or tower_before_raw is None
        or target_before_raw is None
        or target_after_raw is None
        or tower_owner != target_owner
        or target_owner != target_after_owner
    ):
        raise ValueError(f"T{turn}: owner-visible Alchemy states incomplete")

    before_snapshot = snapshots.get((turn, int(tower_owner)))
    after_snapshot = snapshots.get((after_turn, int(tower_owner)))
    if before_snapshot is None or after_snapshot is None:
        raise ValueError(f"T{turn}: owner snapshot missing")
    before_state = before_snapshot.import_state()
    after_state = after_snapshot.import_state()
    tower = before_state.ships.get(tower_id)
    target = before_state.ships.get(target_id)
    target_after = after_state.ships.get(target_id)
    if tower is None or target is None or target_after is None:
        raise ValueError(f"T{turn}: imported Tow pair missing")

    tower_hull = specs.hulls.get(tower.hull_id)
    target_hull = specs.hulls.get(target.hull_id)
    if tower_hull is None or target_hull is None:
        raise ValueError(f"T{turn}: hull spec missing")
    if tower.engine_id is None or tower.engine_id not in specs.engines:
        raise ValueError(f"T{turn}: tower engine spec missing")

    warp = int(tower.warp)
    gravitonic = tower.hull_id in GRAVITONIC_HULL_IDS
    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    route_distance = hypot(waypoint[0] - origin[0], waypoint[1] - origin[1])
    if route_distance > max_distance + 1e-9:
        raise ValueError(f"T{turn}: bounded Alchemy row unexpectedly true-partial")

    tower_mass = ship_movement_mass(tower, specs)
    target_mass = ship_movement_mass(target, specs)
    target_after_mass = ship_movement_mass(target_after, specs)
    tower_fuel = int(tower.cargo.neutronium)
    target_fuel = int(target.cargo.neutronium)
    target_after_fuel = int(target_after.cargo.neutronium)
    tower_nonfuel = tower_mass - tower_fuel
    target_nonfuel = target_mass - target_fuel
    target_after_nonfuel = target_after_mass - target_after_fuel

    supplies_before = _raw_int(target_before_raw, "supplies")
    supplies_after = _raw_int(target_after_raw, "supplies")
    minerals_before = _mineral_total(target_before_raw)
    minerals_after = _mineral_total(target_after_raw)
    supply_drop = None if supplies_before is None or supplies_after is None else supplies_before - supplies_after
    mineral_gain = None if minerals_before is None or minerals_after is None else minerals_after - minerals_before

    special = str(target_hull.special or "")
    alchemy_special = "converts 3 supplies to 1 mineral" in special.lower()
    exact_cargo_signature = bool(
        alchemy_special
        and supply_drop is not None
        and supply_drop > 0
        and supply_drop % 3 == 0
        and mineral_gain == supply_drop // 3
    )

    full_conversion_possible = bool(
        alchemy_special
        and supplies_before is not None
        and supplies_after == 0
        and supplies_before > 0
        and supplies_before % 3 == 0
    )
    converted_supply = supply_drop if exact_cargo_signature else (supplies_before if full_conversion_possible else None)
    mass_drop = None if converted_supply is None else 2 * (converted_supply // 3)
    adjusted_target_nonfuel = None if mass_drop is None else target_nonfuel - mass_drop
    if adjusted_target_nonfuel is not None and adjusted_target_nonfuel < 0:
        raise ValueError(f"T{turn}: negative Alchemy-adjusted non-fuel mass")

    fuel_factor = specs.engines[tower.engine_id].fuel_factor(warp)
    adjusted_envelope = None
    adjusted_snapshot = None
    if adjusted_target_nonfuel is not None:
        adjusted_envelope = _phase_fuel_envelope(
            origin=origin,
            waypoint=waypoint,
            observed=observed,
            warp=warp,
            gravitonic=gravitonic,
            fuel_factor=fuel_factor,
            tower_nonfuel_mass=tower_nonfuel,
            target_nonfuel_mass=adjusted_target_nonfuel,
            tower_fuel_tank=tower_hull.fuel_tank,
            target_fuel_tank=target_hull.fuel_tank,
        )
        adjusted_mass_snapshot_fuel = tower_nonfuel + tower_fuel + adjusted_target_nonfuel + target_fuel
        adjusted_required = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=adjusted_mass_snapshot_fuel,
            distance_traveled=route_distance,
            max_distance_per_turn=max_distance,
        )
        adjusted_endpoint = _fuel_endpoint(
            origin=origin,
            waypoint=waypoint,
            geometry_endpoint=waypoint,
            requested_distance=route_distance,
            fuel_available=tower_fuel,
            fuel_required=adjusted_required,
        )
        adjusted_snapshot = {
            "combined_mass": adjusted_mass_snapshot_fuel,
            "fuel_required": adjusted_required,
            "tower_snapshot_fuel": tower_fuel,
            "target_snapshot_fuel": target_fuel,
            "endpoint": adjusted_endpoint,
            "exact": adjusted_endpoint == observed,
        }

    return {
        "target_hull_id": target.hull_id,
        "target_special": special,
        "supplies_before": supplies_before,
        "supplies_after": supplies_after,
        "supply_drop": supply_drop,
        "minerals_before": minerals_before,
        "minerals_after": minerals_after,
        "mineral_gain": mineral_gain,
        "alchemy_special": alchemy_special,
        "exact_cargo_signature": exact_cargo_signature,
        "full_conversion_mass_hypothesis": full_conversion_possible,
        "mass_drop_candidate": mass_drop,
        "target_nonfuel_snapshot": target_nonfuel,
        "target_nonfuel_after": target_after_nonfuel,
        "target_nonfuel_adjusted": adjusted_target_nonfuel,
        "adjusted_snapshot_prediction": adjusted_snapshot,
        "adjusted_phase_envelope": adjusted_envelope,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the three finite-fuel Tow same-line residuals after stop-context cleanup. "
            "Two damage-backed web rows are kept as bounded external-context confounders. "
            "The one clean T41 row is tested for a target Alchemy mass mutation before Tow. "
            "This is evidence mining only: visible web context does not reconstruct RNG hit "
            "location, and an Alchemy mass match does not by itself prove phase ordering."
        )
    )
    parser.add_argument("--stop-context-log", type=Path, required=True)
    args = parser.parse_args()

    cases = _cases(args.stop_context_log)
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

    totals: Counter[str] = Counter(cases=len(cases))
    print("===== FINITE-FUEL TOW SAME-LINE CONTEXT RESOLUTION =====")
    print("stop_context_log=", args.stop_context_log)
    print("game=", EXPECTED_GAME, "cache_hit=", cache_hit)

    for case in cases:
        turn = int(case["turn"])
        if case["lead"] == "damage_backed_visible_mine_context":
            web = _web_context(case)
            if web["bounded_web_damage_context"]:
                totals["bounded_web_damage_context_rows"] += 1
            else:
                totals["unresolved_damage_context_rows"] += 1
            print({
                "game": EXPECTED_GAME,
                "turn": turn,
                "tower_ship": int(case["tower_ship"]),
                "target_ship": int(case["target_ship"]),
                "resolution": "bounded_web_damage_context" if web["bounded_web_damage_context"] else "unresolved_damage_context",
                "web": web,
                "strong_mine": case.get("strong_mine"),
            })
            continue

        if turn != 41 or case["lead"] != "no_visible_mine_or_damage_lead":
            raise ValueError(f"unexpected clean same-line row T{turn}: {case['lead']}")
        alchemy = _alchemy_resolution(
            case=case,
            prepared=prepared,
            specs=specs,
            ship_groups=ship_groups,
            snapshots=snapshots,
        )
        totals["alchemy_rows"] += 1
        if alchemy["exact_cargo_signature"]:
            totals["alchemy_exact_cargo_signature_rows"] += 1
        if alchemy["full_conversion_mass_hypothesis"]:
            totals["alchemy_full_conversion_hypothesis_rows"] += 1
        envelope = alchemy["adjusted_phase_envelope"]
        if isinstance(envelope, Mapping) and envelope.get("nominal_possible"):
            totals["alchemy_adjusted_envelope_possible_rows"] += 1
        snapshot_prediction = alchemy["adjusted_snapshot_prediction"]
        if isinstance(snapshot_prediction, Mapping) and snapshot_prediction.get("exact"):
            totals["alchemy_adjusted_snapshot_exact_rows"] += 1

        print({
            "game": EXPECTED_GAME,
            "turn": turn,
            "tower_ship": int(case["tower_ship"]),
            "target_ship": int(case["target_ship"]),
            "resolution": "alchemy_mass_phase_lead",
            "alchemy": alchemy,
        })

    print("\n===== SUMMARY =====")
    for key in (
        "cases",
        "bounded_web_damage_context_rows",
        "unresolved_damage_context_rows",
        "alchemy_rows",
        "alchemy_exact_cargo_signature_rows",
        "alchemy_full_conversion_hypothesis_rows",
        "alchemy_adjusted_envelope_possible_rows",
        "alchemy_adjusted_snapshot_exact_rows",
    ):
        print(f"{key}=", totals[key])

    print("\n===== INTERPRETATION =====")
    print("Exact one-web-quantum damage plus a visible hostile web crossing/containment is a bounded external-context confounder; it does not reconstruct the random hit point or promote new mine mechanics.")
    print("An Alchemy-adjusted Tow fuel envelope is only a phase-order lead until the conversion timing is independently established.")
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
