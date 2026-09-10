from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

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
from planets_lab.sim.normal_movement import NormalMovePlan, plan_full_normal_move

from combat_host_candidate_set_audit import _owner_rows_for_turn
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _effective_requested_warp,
    _inbound_transfer_targets,
    _nonzero_transfer_amount,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, _owner_raw, _static_specs


SCHEMA = "planets-lab.combat-host-initial-standard-target-residual-audit.v1"

# These are the only two broad-scope mismatches from the 2026-09-10 initial
# plain-STANDARD target-order runtime. The factual pair itself is not used to
# alter any mechanics; it is included only so the diagnostic can distinguish
# the extra reconstructed target from the factual target after the fact.
TARGETS: tuple[dict[str, Any], ...] = (
    {
        "game_id": 360690,
        "battle_turn": 83,
        "site": (2374, 2260),
        "active_ship_id": 264,
        "extra_target_ship_id": 98,
        "factual_target_ship_id": 190,
        "factual_vcr_id": 666,
    },
    {
        "game_id": 511506,
        "battle_turn": 94,
        "site": (2716, 1999),
        "active_ship_id": 496,
        "extra_target_ship_id": 202,
        "factual_target_ship_id": 332,
        "factual_vcr_id": 728,
    },
)


def _remaining_fuel_from_plan(
    raw: Mapping[str, Any],
    plan: NormalMovePlan,
) -> int | None:
    """Return reconstructed fuel after this ordinary normal-movement plan.

    The result is deliberately available only when the plan is executable and
    the T-1 neutronium value is known. It does not account for transfers, web
    drain, mine hits, Tow/Intercept/Chunnel or other external branches; callers
    must keep those confounders separate before treating the value as decisive.
    """

    fuel = _intish(raw.get("neutronium"))
    if fuel is None or fuel < 0 or not plan.executable:
        return None
    if plan.fuel_used < 0 or plan.fuel_used > fuel:
        return None
    return int(fuel - plan.fuel_used)


def _normal_fuel_projection(
    *,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any],
    race_id: int | None,
    specs: Any,
    inbound_transfer_targets: frozenset[int],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "targetx": _intish(raw.get("targetx")),
        "targety": _intish(raw.get("targety")),
        "warp": _intish(raw.get("warp")),
        "engineid": _intish(raw.get("engineid")),
        "hullid": _intish(raw.get("hullid", raw.get("hull_id"))),
        "mass": _intish(raw.get("mass")),
        "damage": _intish(raw.get("damage")),
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode"),
        "tminus1_fuel": _intish(raw.get("neutronium")),
        "outbound_transfer": _nonzero_transfer_amount(raw),
        "inbound_transfer": ship_id in inbound_transfer_targets,
    }

    effective_warp, warp_issue = _effective_requested_warp(raw, race_id=race_id)
    result["effective_warp"] = effective_warp
    result["warp_issue"] = warp_issue

    if result["outbound_transfer"] or result["inbound_transfer"]:
        result["fuel_projection_status"] = "transfer_confounder"
        result["postmove_fuel"] = None
        return result

    fc = raw.get("friendlycode")
    if isinstance(fc, str) and fc.strip().lower() == "mkt":
        result["fuel_projection_status"] = "pre_move_mkt_mass_change"
        result["postmove_fuel"] = None
        return result

    if warp_issue is not None or effective_warp is None:
        result["fuel_projection_status"] = warp_issue or "effective_warp_unresolved"
        result["postmove_fuel"] = None
        return result

    try:
        ship = _ship(raw)
    except (NuLoadTurnError, TypeError, ValueError):
        result["fuel_projection_status"] = "ship_import_unresolved"
        result["postmove_fuel"] = None
        return result

    if ship.id != ship_id or ship.owner_id != owner_id:
        result["fuel_projection_status"] = "ship_identity_unresolved"
        result["postmove_fuel"] = None
        return result

    target_x = _intish(raw.get("targetx"))
    target_y = _intish(raw.get("targety"))
    raw_mass = _intish(raw.get("mass"))
    if target_x is None or target_y is None or raw_mass is None or raw_mass <= 0:
        result["fuel_projection_status"] = "movement_inputs_unresolved"
        result["postmove_fuel"] = None
        return result

    try:
        plan = plan_full_normal_move(
            ship,
            specs,
            target_x=int(target_x),
            target_y=int(target_y),
            warp=int(effective_warp),
            gravitonic=ship.hull_id in GRAVITONIC_HULL_IDS,
            allow_partial=True,
            allow_fuel_proration=False,
            movement_mass_override=int(raw_mass),
        )
    except (KeyError, TypeError, ValueError):
        result["fuel_projection_status"] = "normal_plan_unresolved"
        result["postmove_fuel"] = None
        return result

    result.update(
        {
            "plan_executable": plan.executable,
            "plan_reason": plan.reason,
            "destination": [int(plan.destination_x), int(plan.destination_y)],
            "distance": plan.distance,
            "max_distance": plan.max_distance,
            "total_mass": plan.total_mass,
            "fuel_factor": plan.fuel_factor,
            "fuel_required": plan.fuel_required,
            "fuel_used": plan.fuel_used,
            "fuel_limited": plan.fuel_limited,
            "partial": plan.partial,
        }
    )
    remaining = _remaining_fuel_from_plan(raw, plan)
    result["postmove_fuel"] = remaining
    result["postmove_has_fuel"] = None if remaining is None else remaining > 0
    result["fuel_projection_status"] = "resolved" if remaining is not None else "unresolved"
    return result


def _t_state_projection(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "ownerid": _intish(raw.get("ownerid", raw.get("owner_id"))),
        "neutronium": _intish(raw.get("neutronium")),
        "damage": _intish(raw.get("damage")),
        "mission": _intish(raw.get("mission")),
        "friendlycode": raw.get("friendlycode"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_archives: list[int] = []

    by_game: dict[int, list[dict[str, Any]]] = {}
    for target in TARGETS:
        by_game.setdefault(int(target["game_id"]), []).append(target)

    for game_id, game_targets in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            missing_archives.append(game_id)
            continue
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        specs = _static_specs(archive_data)
        races, _race_conflicts = _player_races(prepared.snapshots)

        for target in game_targets:
            battle_turn = int(target["battle_turn"])
            before_turn = battle_turn - 1
            owner_rows = _owner_rows_for_turn(ship_groups, before_turn)
            inbound_targets = _inbound_transfer_targets(owner_rows)
            ship_ids = (
                int(target["active_ship_id"]),
                int(target["extra_target_ship_id"]),
                int(target["factual_target_ship_id"]),
            )
            ship_results: dict[str, Any] = {}
            for ship_id in ship_ids:
                before = owner_rows.get(ship_id)
                if before is None:
                    ship_results[str(ship_id)] = {
                        "ship_id": ship_id,
                        "tminus1_missing": True,
                    }
                    continue
                owner_id, raw = before
                projection = _normal_fuel_projection(
                    ship_id=ship_id,
                    owner_id=int(owner_id),
                    raw=raw,
                    race_id=races.get(int(owner_id)),
                    specs=specs,
                    inbound_transfer_targets=inbound_targets,
                )
                t_owner, t_raw = _owner_raw(ship_groups, battle_turn, ship_id)
                projection["t_state_owner_id"] = t_owner
                projection["t_state_attribution_only"] = _t_state_projection(t_raw)
                ship_results[str(ship_id)] = projection

            extra = ship_results.get(str(target["extra_target_ship_id"]), {})
            factual_target = ship_results.get(str(target["factual_target_ship_id"]), {})
            active = ship_results.get(str(target["active_ship_id"]), {})
            rows.append(
                {
                    **target,
                    "site": list(target["site"]),
                    "ships": ship_results,
                    "extra_target_postmove_fuel_zero": extra.get("postmove_fuel") == 0,
                    "factual_target_postmove_has_fuel": factual_target.get("postmove_has_fuel"),
                    "active_postmove_has_fuel": active.get("postmove_has_fuel"),
                }
            )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "target_sites": len(TARGETS),
            "rows_found": len(rows),
            "missing_archives": len(missing_archives),
            "extra_target_postmove_fuel_zero": sum(
                1 for row in rows if row["extra_target_postmove_fuel_zero"]
            ),
            "extra_target_postmove_fuel_nonzero": sum(
                1
                for row in rows
                if row["ships"].get(str(row["extra_target_ship_id"]), {}).get("postmove_fuel")
                not in (None, 0)
            ),
            "extra_target_postmove_fuel_unresolved": sum(
                1
                for row in rows
                if row["ships"].get(str(row["extra_target_ship_id"]), {}).get("postmove_fuel")
                is None
            ),
        },
        "missing_archive_game_ids": missing_archives,
        "rows": rows,
        "evidence_boundary": (
            "Focused attribution-only audit for the two broad-scope initial STANDARD target-order residuals. "
            "Post-movement fuel is reconstructed only from owner-current T-1 ordinary normal-movement inputs using "
            "the existing canonical movement planner and raw movement mass. T-state is printed only as attribution/control "
            "and is never used to choose the candidate or compute its T-1 movement fuel. No target-order rule is changed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit post-normal-movement fuel for the two initial STANDARD target-order residual sites."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD TARGET RESIDUAL AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("RESIDUAL ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: focused post-normal-movement fuel attribution; T state is control-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
