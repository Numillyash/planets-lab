from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_residual_context import _storm_consensus_by_turn
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records
from planets_lab.rules.combat.order import BIRD_RACE_ID

from combat_host_candidate_set_audit import _owner_rows_for_turn
from combat_host_initial_standard_target_cloak_residual_audit import run as run_residual
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, _owner_raw, _static_specs
from combat_host_privateer_rob_cloak_fuel_attribution_audit import (
    _glory_start_context,
    _inside_any_ion_disturbance,
    _loki_start_exposure,
)
from combat_host_privateer_rob_initial_cloak_context_audit import (
    _reference_normal_move,
    _xy,
)


SCHEMA = "planets-lab.combat-host-bird-super-spy-cloak-context-audit.v2"
BIRD_SUPER_SPY_MISSION_ID = 9
FOCUS_GAME_ID = 511506
FOCUS_BATTLE_TURN = 94
FOCUS_EXTRA_SHIP_ID = 202
FOCUS_FACTUAL_SHIP_ID = 332
PLANET_ION_PULSE_DEFENSE_THRESHOLD = 30


def _boolish(value: Any) -> bool | None:
    if value is True or value is False:
        return bool(value)
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _planet_ion_pulse_context(
    *,
    planet_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    turn: int,
    ship_owner_id: int,
    position: tuple[int, int] | None,
) -> dict[str, Any]:
    """Conservatively flag a planet which could produce a Super-Spy ion pulse.

    The exact Super Spy Deluxe/Command trigger and random roll are not reconstructed
    here. A foreign planet at the ship location with at least 30 observed defense
    posts is therefore treated as a possible pulse source and fails closed.
    """

    if position is None:
        return {"status": "position_unresolved", "possible": None, "planets": []}

    rows: list[dict[str, Any]] = []
    unresolved = False
    possible = False
    for grouped_turn, planet_id in sorted(planet_groups):
        if grouped_turn != turn:
            continue
        owner_id, raw = _owner_raw(planet_groups, turn, planet_id)
        if raw is None or _xy(raw) != position:
            continue
        defense = _int_value(raw.get("defense"))
        foreign = owner_id is not None and owner_id > 0 and owner_id != ship_owner_id
        row_possible: bool | None
        if not foreign:
            row_possible = False
        elif defense is None:
            row_possible = None
            unresolved = True
        else:
            row_possible = defense >= PLANET_ION_PULSE_DEFENSE_THRESHOLD
            possible = possible or row_possible
        rows.append(
            {
                "planet_id": int(planet_id),
                "owner_id": owner_id,
                "foreign": foreign,
                "defense": defense,
                "friendly_code": raw.get("friendlycode"),
                "possible": row_possible,
            }
        )

    if possible:
        status = "possible"
        resolved_possible: bool | None = True
    elif unresolved:
        status = "unresolved"
        resolved_possible = None
    else:
        status = "clear"
        resolved_possible = False
    return {"status": status, "possible": resolved_possible, "planets": rows}


def _documented_super_spy_effective_cloak_candidate(
    *,
    race_id: int | None,
    mission: int | None,
    hull_can_cloak: bool | None,
    advanced_cloak: bool | None,
    damage: int | None,
    fuel_before: int | None,
    reference_cost: int | None,
    reference_move_resolved: bool,
    reference_remaining_fuel: int | None,
    prior_iscloaked: bool | None,
    ion_start_inside: bool | None,
    planet_ion_pulse_possible: bool | None,
    loki_start_exposed: bool | None,
    active_glory_colocated: bool,
) -> tuple[bool | None, str]:
    """Conservative documented+corpus candidate for the focused Bird residual.

    Official Super Spy documentation says a Bird ship on mission 9 which can
    cloak attempts to cloak normally. Official Cloak documentation says damage
    prevents cloaking and ordinary cloak consumes the normal reference fuel.
    This helper deliberately demands stronger-than-minimal positive evidence:
    archived prior cloak must already be true, ordinary-cloak fuel must remain
    strictly above the reference cost even after independently reconstructed
    normal movement, and every visible decloak context used here must be clear.
    """

    if race_id != BIRD_RACE_ID:
        return None, "outside_bird_scope"
    if mission != BIRD_SUPER_SPY_MISSION_ID:
        return None, "outside_super_spy_scope"
    if hull_can_cloak is not True:
        return None, "cloak_capability_unresolved_or_false"
    if advanced_cloak is not False:
        return None, "advanced_cloak_unresolved"
    if damage is None:
        return None, "damage_unresolved"
    if damage > 0:
        return False, "damage_blocks_cloak"
    if prior_iscloaked is not True:
        return None, "prior_cloak_not_positive"
    if fuel_before is None or reference_cost is None:
        return None, "fuel_or_reference_unresolved"
    if fuel_before <= reference_cost:
        return False, "fuel_not_safely_above_reference_cost"
    if not reference_move_resolved or reference_remaining_fuel is None:
        return None, "reference_move_fuel_unresolved"
    if reference_remaining_fuel <= reference_cost:
        return None, "post_move_fuel_margin_not_positive"
    if ion_start_inside is None:
        return None, "ion_storm_context_unresolved"
    if ion_start_inside:
        return None, "ion_storm_context_present"
    if planet_ion_pulse_possible is None:
        return None, "planet_ion_pulse_context_unresolved"
    if planet_ion_pulse_possible:
        return None, "planet_ion_pulse_possible"
    if loki_start_exposed is None:
        return None, "loki_context_unresolved"
    if loki_start_exposed:
        return None, "loki_context_present"
    if active_glory_colocated:
        return None, "active_glory_context_present"
    return True, "documented_super_spy_ordinary_cloak_supported"


def run(args: argparse.Namespace) -> dict[str, Any]:
    base = run_residual(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            output=None,
        )
    )
    target_row = next(
        (
            row
            for row in base.get("rows", ())
            if isinstance(row, Mapping)
            and int(row.get("game_id", -1)) == FOCUS_GAME_ID
            and int(row.get("battle_turn", -1)) == FOCUS_BATTLE_TURN
        ),
        None,
    )
    if target_row is None:
        return {
            "schema": SCHEMA,
            "read_only": True,
            "summary": {"focus_row_found": False},
            "focus": None,
            "evidence_boundary": "Focused Bird Super Spy context gate; source residual row was unavailable.",
        }

    archive_path = args.archive_dir / f"game-{FOCUS_GAME_ID}.zip"
    if not archive_path.exists():
        return {
            "schema": SCHEMA,
            "read_only": True,
            "summary": {"focus_row_found": True, "archive_found": False},
            "focus": None,
            "evidence_boundary": "Focused Bird Super Spy context gate; historical archive was unavailable.",
        }

    archive_data = archive_path.read_bytes()
    prepared, _ = load_or_build_prepared_game_cache(
        archive_data,
        game_id=FOCUS_GAME_ID,
        cache_path=args.prepared_dir / f"game-{FOCUS_GAME_ID}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    planet_groups = group_perspective_records(prepared.snapshots, "planet")
    races, race_conflicts = _player_races(prepared.snapshots)
    specs = _static_specs(archive_data)
    before_turn = FOCUS_BATTLE_TURN - 1
    owner_rows = _owner_rows_for_turn(ship_groups, before_turn)

    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(
        prepared.snapshots
    )

    def project(ship_id: int) -> dict[str, Any]:
        entry = owner_rows.get(ship_id)
        if entry is None:
            return {"ship_id": ship_id, "owner_current_missing": True}
        owner_id, raw = entry
        race_id = races.get(owner_id)
        hull_id = _int_value(raw.get("hullid", raw.get("hull_id")))
        hull = specs.hulls.get(hull_id) if hull_id is not None else None
        hull_can_cloak = bool(hull.can_cloak) if hull is not None else None
        hull_mass = int(hull.mass) if hull is not None else None
        special = str(getattr(hull, "special", "") or "") if hull is not None else ""
        advanced_cloak = "advanced cloak" in special.lower()
        mission = _int_value(raw.get("mission"))
        damage = _int_value(raw.get("damage"))
        fuel = _int_value(raw.get("neutronium"))
        reference_cost = max(5, hull_mass // 20) if hull_mass is not None and hull_mass >= 0 else None
        position = _xy(raw)

        reference_move = _reference_normal_move(
            ship_id=ship_id,
            owner_id=owner_id,
            race_id=race_id,
            hull_id=hull_id,
            raw=raw,
            specs=specs,
        )
        remaining_fuel = _int_value(reference_move.get("raw_reference_remaining_fuel"))

        loki_exposed, loki_ids = _loki_start_exposure(
            rows=owner_rows,
            target_owner_id=owner_id,
            target_position=position,
        )
        glory_rows = _glory_start_context(
            rows=owner_rows,
            target_owner_id=owner_id,
            target_position=position,
            specs=specs,
        )
        active_glory = any(row.get("active_code") is True for row in glory_rows)
        planet_ion_pulse = _planet_ion_pulse_context(
            planet_groups=planet_groups,
            turn=before_turn,
            ship_owner_id=owner_id,
            position=position,
        )

        if before_turn in storm_conflict_turns:
            ion_inside: bool | None = None
            storm_status = "conflict"
        elif before_turn in storm_invalid_turns:
            ion_inside = None
            storm_status = "invalid"
        else:
            ion_inside = _inside_any_ion_disturbance(
                storms_by_turn.get(before_turn, ()),
                position=position,
            )
            storm_status = "resolved"

        ships_value = target_row.get("ships")
        ships = ships_value if isinstance(ships_value, Mapping) else {}
        base_ship_value = ships.get(str(ship_id))
        base_ship = base_ship_value if isinstance(base_ship_value, Mapping) else {}
        prior_iscloaked = _boolish(base_ship.get("tminus1_iscloaked"))
        candidate, reason = _documented_super_spy_effective_cloak_candidate(
            race_id=race_id,
            mission=mission,
            hull_can_cloak=hull_can_cloak,
            advanced_cloak=advanced_cloak,
            damage=damage,
            fuel_before=fuel,
            reference_cost=reference_cost,
            reference_move_resolved=reference_move.get("resolved") is True,
            reference_remaining_fuel=remaining_fuel,
            prior_iscloaked=prior_iscloaked,
            ion_start_inside=ion_inside,
            planet_ion_pulse_possible=planet_ion_pulse.get("possible"),
            loki_start_exposed=loki_exposed,
            active_glory_colocated=active_glory,
        )

        return {
            "ship_id": ship_id,
            "owner_id": owner_id,
            "race_id": race_id,
            "hull_id": hull_id,
            "hull_name": getattr(hull, "name", None),
            "hull_can_cloak": hull_can_cloak,
            "hull_special": special,
            "advanced_cloak": advanced_cloak,
            "mission": mission,
            "damage": damage,
            "fuel": fuel,
            "reference_cost": reference_cost,
            "fuel_margin": fuel - reference_cost if fuel is not None and reference_cost is not None else None,
            "prior_iscloaked": prior_iscloaked,
            "reference_move": reference_move,
            "storm_status": storm_status,
            "ion_start_inside": ion_inside,
            "planet_ion_pulse": planet_ion_pulse,
            "loki_start_exposed": loki_exposed,
            "loki_ship_ids": loki_ids,
            "active_glory_colocated": active_glory,
            "glory_rows": glory_rows,
            "documented_effective_cloak_supported": candidate,
            "documented_effective_cloak_reason": reason,
            "t_same_owner": base_ship.get("t_same_owner"),
            "t_same_hull": base_ship.get("t_same_hull"),
            "t_iscloaked_attribution_only": base_ship.get("t_iscloaked"),
        }

    extra = project(FOCUS_EXTRA_SHIP_ID)
    factual = project(FOCUS_FACTUAL_SHIP_ID)
    extra_supported = extra.get("documented_effective_cloak_supported") is True
    factual_supported = factual.get("documented_effective_cloak_supported") is True

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "focus_row_found": True,
            "archive_found": True,
            "race_conflicts": len(race_conflicts),
            "extra_ship_documented_effective_cloak_supported": extra_supported,
            "factual_ship_documented_effective_cloak_supported": factual_supported,
            "raw_prior_cloak_control_separates": (
                extra.get("prior_iscloaked") is True
                and factual.get("prior_iscloaked") is True
                and extra_supported
                and not factual_supported
            ),
        },
        "focus": {
            "game_id": FOCUS_GAME_ID,
            "before_turn": before_turn,
            "battle_turn": FOCUS_BATTLE_TURN,
            "active_ship_id": int(target_row["active_ship_id"]),
            "extra_target_ship_id": FOCUS_EXTRA_SHIP_ID,
            "factual_target_ship_id": FOCUS_FACTUAL_SHIP_ID,
            "extra": extra,
            "factual": factual,
            "factual_vcr_id": int(target_row["factual_vcr_id"]),
        },
        "evidence_boundary": (
            "Focused documented Bird Super Spy effective-cloak attribution for the remaining initial STANDARD target "
            "residual. Official Super Spy semantics are documentation; dynamic state comes from archived T-1 and "
            "independently reconstructed movement/context. T state is attribution-only. The positive candidate requires "
            "ordinary cloak, damage0, archived prior cloak=true, strictly positive fuel margin above the ordinary "
            "reference cost before and after reference normal movement, clear ion-storm/Loki/active-Glory context, and "
            "no foreign planet at the origin with a conservatively possible Super-Spy ion pulse. Planet ion-pulse trigger "
            "settings/random resolution are not reconstructed: a foreign planet with >=30 observed defense posts fails "
            "closed as possible."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit documented Bird Super Spy cloak context for the remaining initial STANDARD target residual."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT BIRD SUPER SPY CLOAK CONTEXT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("FOCUS:")
    print(report["focus"])
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: documented/scoped Bird residual gate only; no canonical targetability rule is changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
