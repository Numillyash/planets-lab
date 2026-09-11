from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from math import hypot
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_loadturn import NuLoadTurnError, _ship
from planets_lab.sim.normal_movement import plan_full_normal_move

from combat_host_candidate_set_audit import _owner_rows_for_turn, _serialize
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import _effective_requested_warp
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _owner_raw,
    _static_specs,
)
from combat_host_privateer_rob_initial_decision_audit import run as run_initial_decision


SCHEMA = "planets-lab.combat-host-privateer-rob-initial-cloak-context-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 40
PRIVATEER_RACE_ID = 5
LOKI_HULL_ID = 7
LOKI_RANGE_LY = 10.0
LOKI_MAX_ACTIVE_DAMAGE = 19
STANDARD_CLOAK_MISSION_ID = 10
FOCUS_CLASSIFICATIONS = frozenset(
    {
        "initial_skip_target_outranks_factual",
        "initial_pair_vcr",
    }
)


def _xy(raw: Mapping[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(raw, Mapping):
        return None
    x = _intish(raw.get("x"))
    y = _intish(raw.get("y"))
    if x is None or y is None:
        return None
    return int(x), int(y)


def _distance(a: tuple[int, int] | None, b: tuple[int, int] | None) -> float | None:
    if a is None or b is None:
        return None
    return hypot(a[0] - b[0], a[1] - b[1])


def _within_loki_range(distance: float | None) -> bool | None:
    if distance is None:
        return None
    return distance <= LOKI_RANGE_LY + 1e-9


def _stable_owner_hull_identity(
    *,
    before_owner_id: int,
    before_hull_id: int | None,
    after_owner_id: int | None,
    after_raw: Mapping[str, Any] | None,
) -> bool:
    if after_owner_id != before_owner_id or before_hull_id is None or after_raw is None:
        return False
    after_hull_id = _intish(after_raw.get("hullid", after_raw.get("hull_id")))
    return after_hull_id == before_hull_id


def _basic_cloak_fuel_cost(hull_mass: int | None) -> int | None:
    if hull_mass is None or hull_mass < 0:
        return None
    return max(5, hull_mass // 20)


def _focus_kind(row: Mapping[str, Any]) -> str | None:
    if str(row.get("target_prior_cloak")) != "true":
        return None
    context = row.get("initial_context")
    if not isinstance(context, Mapping):
        return None
    classification = str(context.get("classification") or "")
    if classification not in FOCUS_CLASSIFICATIONS:
        return None
    return classification


def _reference_normal_move(
    *,
    ship_id: int,
    owner_id: int,
    race_id: int | None,
    hull_id: int | None,
    raw: Mapping[str, Any],
    specs: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "resolved": False,
        "reason": None,
    }
    raw_mass = _intish(raw.get("mass"))
    raw_fuel = _intish(raw.get("neutronium"))
    if raw_mass is None or raw_mass <= 0:
        result["reason"] = "raw_mass_missing"
        return result
    effective_warp, issue = _effective_requested_warp(raw, race_id=race_id)
    if issue is not None or effective_warp is None:
        result["reason"] = issue or "effective_warp_unresolved"
        return result
    if effective_warp <= 0:
        result.update(
            {
                "resolved": True,
                "reason": "stationary",
                "effective_warp": int(effective_warp),
                "fuel_used": 0,
                "raw_fuel_before": raw_fuel,
                "raw_reference_remaining_fuel": raw_fuel,
            }
        )
        return result
    try:
        ship = _ship(raw)
    except (NuLoadTurnError, TypeError, ValueError):
        result["reason"] = "ship_import_unresolved"
        return result
    if ship.id != ship_id or ship.owner_id != owner_id:
        result["reason"] = "ship_identity_unresolved"
        return result
    target_x = _intish(raw.get("targetx"))
    target_y = _intish(raw.get("targety"))
    if target_x is None or target_y is None:
        result["reason"] = "waypoint_unknown"
        return result
    try:
        plan = plan_full_normal_move(
            ship,
            specs,
            target_x=int(target_x),
            target_y=int(target_y),
            warp=int(effective_warp),
            gravitonic=hull_id in GRAVITONIC_HULL_IDS,
            allow_partial=True,
            allow_fuel_proration=False,
            movement_mass_override=int(raw_mass),
        )
    except (KeyError, TypeError, ValueError):
        result["reason"] = "normal_plan_unresolved"
        return result
    result.update(
        {
            "resolved": bool(plan.executable),
            "reason": plan.reason,
            "effective_warp": int(effective_warp),
            "destination": [int(plan.destination_x), int(plan.destination_y)],
            "distance": float(plan.distance),
            "fuel_required": int(plan.fuel_required),
            "fuel_used": int(plan.fuel_used),
            "fuel_limited": bool(plan.fuel_limited),
            "raw_fuel_before": raw_fuel,
            "raw_reference_remaining_fuel": (
                int(raw_fuel) - int(plan.fuel_used) if raw_fuel is not None and plan.executable else None
            ),
        }
    )
    return result


def _foreign_origin_rows(
    *,
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    target_ship_id: int,
    target_owner_id: int,
    origin: tuple[int, int] | None,
    races: Mapping[int, int],
) -> list[dict[str, Any]]:
    if origin is None:
        return []
    rows: list[dict[str, Any]] = []
    for ship_id, (owner_id, raw) in sorted(owner_rows.items()):
        if ship_id == target_ship_id or owner_id == target_owner_id:
            continue
        if _xy(raw) != origin:
            continue
        rows.append(
            {
                "ship_id": int(ship_id),
                "owner_id": int(owner_id),
                "race_id": races.get(int(owner_id)),
                "hull_id": _intish(raw.get("hullid", raw.get("hull_id"))),
                "mission": _intish(raw.get("mission")),
                "enemy": _intish(raw.get("enemy")),
                "fuel": _intish(raw.get("neutronium")),
                "iscloaked": raw.get("iscloaked"),
            }
        )
    return rows


def _loki_context(
    *,
    owner_rows_before: Mapping[int, tuple[int, Mapping[str, Any]]],
    owner_rows_after: Mapping[int, tuple[int, Mapping[str, Any]]],
    ship_groups: Mapping[Any, Any],
    battle_turn: int,
    target_origin: tuple[int, int] | None,
    battle_site: tuple[int, int],
) -> dict[str, Any]:
    before_rows: list[dict[str, Any]] = []
    before_ids: set[int] = set()
    for ship_id, (owner_id, raw) in sorted(owner_rows_before.items()):
        hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
        if hull_id != LOKI_HULL_ID:
            continue
        before_ids.add(int(ship_id))
        damage = _intish(raw.get("damage"))
        active_by_damage = damage is not None and 0 <= damage <= LOKI_MAX_ACTIVE_DAMAGE
        start = _xy(raw)
        start_distance = _distance(start, target_origin)
        after_owner_id, after_raw = _owner_raw(ship_groups, battle_turn, int(ship_id))
        stable = _stable_owner_hull_identity(
            before_owner_id=int(owner_id),
            before_hull_id=LOKI_HULL_ID,
            after_owner_id=after_owner_id,
            after_raw=after_raw,
        )
        after_position = _xy(after_raw) if stable else None
        after_distance = _distance(after_position, battle_site)
        before_rows.append(
            {
                "ship_id": int(ship_id),
                "owner_id": int(owner_id),
                "damage": damage,
                "active_by_damage": active_by_damage,
                "start": list(start) if start is not None else None,
                "start_distance_to_target_origin": start_distance,
                "start_within_10": (
                    _within_loki_range(start_distance) if active_by_damage else False
                ),
                "stable_at_t": stable,
                "t_position": list(after_position) if after_position is not None else None,
                "t_distance_to_battle_site": after_distance,
                "t_within_10_attribution": (
                    _within_loki_range(after_distance) if active_by_damage and stable else False
                ),
            }
        )

    after_rows: list[dict[str, Any]] = []
    for ship_id, (owner_id, raw) in sorted(owner_rows_after.items()):
        hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
        if hull_id != LOKI_HULL_ID:
            continue
        damage = _intish(raw.get("damage"))
        active_by_damage = damage is not None and 0 <= damage <= LOKI_MAX_ACTIVE_DAMAGE
        position = _xy(raw)
        distance = _distance(position, battle_site)
        if distance is None or distance > 25.0:
            continue
        after_rows.append(
            {
                "ship_id": int(ship_id),
                "owner_id": int(owner_id),
                "damage": damage,
                "active_by_damage": active_by_damage,
                "position": list(position) if position is not None else None,
                "distance_to_battle_site": distance,
                "within_10_attribution": (
                    _within_loki_range(distance) if active_by_damage else False
                ),
                "present_tminus1": int(ship_id) in before_ids,
            }
        )

    return {
        "tminus1_lokis": before_rows,
        "t_nearby_lokis_attribution_only": after_rows,
        "any_active_start_within_10": any(row["start_within_10"] is True for row in before_rows),
        "any_active_t_within_10_attribution": any(
            row["within_10_attribution"] is True for row in after_rows
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    base = run_initial_decision(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )
    focus_rows = [
        dict(row)
        for row in base.get("examples", ())
        if isinstance(row, Mapping) and _focus_kind(row) is not None
    ]

    rows_by_game: dict[int, list[dict[str, Any]]] = {}
    for row in focus_rows:
        rows_by_game.setdefault(int(row["game_id"]), []).append(row)

    totals: Counter[str] = Counter()
    signatures: Counter[str] = Counter()
    output_rows: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(rows_by_game.items()):
        if game_id == SPECIAL_GAME_ID:
            continue
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            totals["missing_archives"] += 1
            continue
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, race_conflicts = _player_races(prepared.snapshots)
        if race_conflicts:
            totals["race_conflict_games"] += 1
        specs = _static_specs(archive_data)
        before_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        after_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}

        for row in game_rows:
            classification = _focus_kind(row)
            if classification is None:
                continue
            before_turn = int(row["before_turn"])
            battle_turn = int(row["battle_turn"])
            if before_turn not in before_cache:
                before_cache[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            if battle_turn not in after_cache:
                after_cache[battle_turn] = _owner_rows_for_turn(ship_groups, battle_turn)
            owner_rows_before = before_cache[before_turn]
            owner_rows_after = after_cache[battle_turn]

            target_ship_id = int(row["target_ship_id"])
            target_owner_id = int(row["target_owner_id"])
            target_entry = owner_rows_before.get(target_ship_id)
            if target_entry is None:
                totals["target_owner_current_missing"] += 1
                continue
            owner_id, raw = target_entry
            hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
            race_id = races.get(int(owner_id))
            hull = specs.hulls.get(hull_id) if hull_id is not None else None
            hull_mass = int(hull.mass) if hull is not None else None
            cloak_cost = _basic_cloak_fuel_cost(hull_mass)
            fuel = _intish(raw.get("neutronium"))
            damage = _intish(raw.get("damage"))
            mission = _intish(raw.get("mission"))
            origin = _xy(raw)
            battle_site = (int(row["site"][0]), int(row["site"][1]))

            foreign_origin = _foreign_origin_rows(
                owner_rows=owner_rows_before,
                target_ship_id=target_ship_id,
                target_owner_id=target_owner_id,
                origin=origin,
                races=races,
            )
            reference_move = _reference_normal_move(
                ship_id=target_ship_id,
                owner_id=int(owner_id),
                race_id=race_id,
                hull_id=hull_id,
                raw=raw,
                specs=specs,
            )
            loki = _loki_context(
                owner_rows_before=owner_rows_before,
                owner_rows_after=owner_rows_after,
                ship_groups=ship_groups,
                battle_turn=battle_turn,
                target_origin=origin,
                battle_site=battle_site,
            )

            after_owner_id, after_raw = _owner_raw(ship_groups, battle_turn, target_ship_id)
            stable_after = _stable_owner_hull_identity(
                before_owner_id=int(owner_id),
                before_hull_id=hull_id,
                after_owner_id=after_owner_id,
                after_raw=after_raw,
            )
            after_state = None
            if stable_after and after_raw is not None:
                after_state = {
                    "fuel": _intish(after_raw.get("neutronium")),
                    "damage": _intish(after_raw.get("damage")),
                    "iscloaked": after_raw.get("iscloaked"),
                    "position": list(_xy(after_raw)) if _xy(after_raw) is not None else None,
                }

            raw_remaining = reference_move.get("raw_reference_remaining_fuel")
            raw_reference_runs_out = raw_remaining == 0 if isinstance(raw_remaining, int) else None
            no_foreign_at_origin = len(foreign_origin) == 0
            row_signature = (
                f"{classification}|damage={damage}|raw_move_remaining={raw_remaining}|"
                f"foreign_origin={len(foreign_origin)}|loki_start={loki['any_active_start_within_10']}|"
                f"loki_t={loki['any_active_t_within_10_attribution']}"
            )
            signatures[row_signature] += 1
            totals["focus_rows"] += 1
            totals[classification] += 1
            if race_id == PRIVATEER_RACE_ID:
                totals["privateer_targets"] += 1
            if mission == STANDARD_CLOAK_MISSION_ID:
                totals["mission_is_standard_cloak"] += 1
            else:
                totals["mission_not_standard_cloak"] += 1
            if damage == 0:
                totals["tminus1_damage_zero"] += 1
            elif damage is not None and damage > 0:
                totals["tminus1_damage_positive"] += 1
            if fuel is not None and cloak_cost is not None and fuel >= cloak_cost:
                totals["tminus1_basic_cloak_fuel_sufficient"] += 1
            if reference_move.get("resolved") is True:
                totals["reference_move_resolved"] += 1
            if raw_reference_runs_out is True:
                totals["raw_reference_move_runs_out_of_fuel"] += 1
            if no_foreign_at_origin:
                totals["no_foreign_ship_at_rob_origin"] += 1
            else:
                totals["foreign_ship_at_rob_origin"] += 1
            if loki["any_active_start_within_10"]:
                totals["active_loki_start_within_10"] += 1
            if loki["any_active_t_within_10_attribution"]:
                totals["active_loki_t_within_10_attribution"] += 1
            if stable_after:
                totals["stable_target_identity_at_t"] += 1

            output_rows.append(
                {
                    "game_id": game_id,
                    "before_turn": before_turn,
                    "battle_turn": battle_turn,
                    "site": list(battle_site),
                    "classification": classification,
                    "target_ship_id": target_ship_id,
                    "attacker_ship_id": int(row["attacker_ship_id"]),
                    "factual_first_opponent_ship_id": row.get("initial_context", {}).get(
                        "factual_first_opponent_ship_id"
                    ),
                    "target": {
                        "owner_id": int(owner_id),
                        "race_id": race_id,
                        "hull_id": hull_id,
                        "hull_name": hull.name if hull is not None else None,
                        "hull_mass": hull_mass,
                        "mission": mission,
                        "mission_is_standard_cloak": mission == STANDARD_CLOAK_MISSION_ID,
                        "enemy": _intish(raw.get("enemy")),
                        "friendlycode": raw.get("friendlycode"),
                        "fuel": fuel,
                        "damage": damage,
                        "iscloaked": raw.get("iscloaked"),
                        "origin": list(origin) if origin is not None else None,
                        "basic_cloak_fuel_cost": cloak_cost,
                        "basic_cloak_fuel_sufficient": (
                            fuel >= cloak_cost if fuel is not None and cloak_cost is not None else None
                        ),
                    },
                    "position_source": row.get("target_position_source"),
                    "reference_normal_move": reference_move,
                    "rob_origin": {
                        "foreign_colocated_count": len(foreign_origin),
                        "foreign_colocated": foreign_origin,
                        "no_foreign_fuel_source_visible": no_foreign_at_origin,
                        "note": (
                            "Zero foreign owner-current ships at the T-1 origin rules out Rob gaining fuel from a visible "
                            "foreign ship there. A nonzero count is exposure only; diplomacy/cloak/Rob order and the 1% "
                            "failure chance are not reconstructed here."
                        ),
                    },
                    "loki_context": loki,
                    "target_t_identity_stable": stable_after,
                    "target_t_state_attribution_only": after_state,
                    "context_signature": row_signature,
                }
            )

    output_rows.sort(
        key=lambda row: (
            0 if row["classification"] == "initial_skip_target_outranks_factual" else 1,
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["target_ship_id"]),
        )
    )
    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "context_signatures": _serialize(signatures),
            "base_initial_decision_summary": base.get("summary"),
        },
        "rows": output_rows[: args.example_limit],
        "evidence_boundary": (
            "Narrow attribution-only differential over prior-cloak=true clean initial Rob/Meteor rows. The population is "
            "derived from the independently reconstructed initial-decision audit, then enriched from owner-current T-1 "
            "state. Raw movement fuel is a reference calculation using the same deterministic normal-move planner; because "
            "Rob executes before movement it is only causal for fuel exhaustion when no visible foreign ship at the T-1 "
            "origin could have supplied fuel. Loki start proximity uses documented hull 7 / <=19% damage / 10 ly rules. "
            "T Loki proximity and target T state are attribution-only post-Host evidence, not predictor inputs. This tool does "
            "not claim mission9 engages cloak, does not promote raw iscloaked, and does not modify canonical combat rules."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit precombat state context for clean prior-cloaked Privateer Rob initial target decisions."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB INITIAL CLOAK-CONTEXT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: attribution-only state context; no effective-cloak rule is promoted by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
