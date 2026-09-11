from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from math import hypot
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import StormRecord, _storm_consensus_by_turn
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from combat_host_candidate_set_audit import _owner_rows_for_turn, _serialize
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _effective_requested_warp,
    _inbound_transfer_targets,
    _nonzero_transfer_amount,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _static_specs,
)
from combat_host_privateer_rob_cloak_fuel_state_audit import (
    _classify_fuel_debit,
    _fuel_threshold,
    _int_value,
    _same_position,
    run as run_fuel_state,
)
from combat_host_privateer_rob_cloak_population_audit import run as run_population
from combat_host_privateer_rob_initial_cloak_context_audit import (
    LOKI_HULL_ID,
    LOKI_MAX_ACTIVE_DAMAGE,
    LOKI_RANGE_LY,
    _foreign_origin_rows,
    _xy,
)


SCHEMA = "planets-lab.combat-host-privateer-rob-cloak-fuel-attribution-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80
ACTIVE_GLORY_CODES = frozenset({"pop", "trg"})


def _inside_any_ion_disturbance(
    storms: Sequence[StormRecord],
    *,
    position: tuple[int, int] | None,
) -> bool | None:
    if position is None:
        return None
    for storm in storms:
        if storm.radius <= 0:
            continue
        if hypot(position[0] - storm.x, position[1] - storm.y) < storm.radius:
            return True
    return False


def _loki_start_exposure(
    *,
    rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    target_owner_id: int,
    target_position: tuple[int, int] | None,
) -> tuple[bool | None, list[int]]:
    if target_position is None:
        return None, []
    ids: list[int] = []
    for ship_id, (owner_id, raw) in rows.items():
        if owner_id == target_owner_id:
            continue
        hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
        if hull_id != LOKI_HULL_ID:
            continue
        damage = _intish(raw.get("damage"))
        if damage is None or damage < 0 or damage > LOKI_MAX_ACTIVE_DAMAGE:
            continue
        position = _xy(raw)
        if position is None:
            continue
        if hypot(position[0] - target_position[0], position[1] - target_position[1]) <= LOKI_RANGE_LY + 1e-9:
            ids.append(int(ship_id))
    return bool(ids), sorted(ids)


def _glory_start_context(
    *,
    rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    target_owner_id: int,
    target_position: tuple[int, int] | None,
    specs: Any,
) -> list[dict[str, Any]]:
    if target_position is None:
        return []
    result: list[dict[str, Any]] = []
    for ship_id, (owner_id, raw) in sorted(rows.items()):
        if owner_id == target_owner_id:
            continue
        position = _xy(raw)
        if position != target_position:
            continue
        hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
        hull = specs.hulls.get(hull_id) if hull_id is not None else None
        special = str(getattr(hull, "special", "") or "")
        if "glory" not in special.lower():
            continue
        fc_raw = raw.get("friendlycode")
        fc = fc_raw.strip().lower() if isinstance(fc_raw, str) else None
        result.append(
            {
                "ship_id": int(ship_id),
                "owner_id": int(owner_id),
                "hull_id": hull_id,
                "hull_name": getattr(hull, "name", None),
                "special": special,
                "friendly_code": fc_raw,
                "active_code": fc in ACTIVE_GLORY_CODES,
            }
        )
    return result


def _clean_stationary_fuel_context(
    *,
    damage_zero: bool,
    effective_warp: int | None,
    same_position: bool | None,
    outbound_transfer: bool,
    inbound_transfer: bool,
    foreign_origin_count: int,
) -> bool:
    return (
        damage_zero
        and effective_warp == 0
        and same_position is True
        and not outbound_transfer
        and not inbound_transfer
        and foreign_origin_count == 0
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    population = run_population(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )
    fuel_state = run_fuel_state(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )

    rows_by_game: dict[int, list[Mapping[str, Any]]] = {}
    for row in population.get("examples", ()):
        if not isinstance(row, Mapping):
            continue
        if row.get("stable_identity") is not True:
            continue
        before = row.get("before")
        after = row.get("after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            continue
        if before.get("iscloaked") is not True:
            continue
        rows_by_game.setdefault(int(row["game_id"]), []).append(row)

    totals: Counter[str] = Counter()
    clean_relation: Counter[str] = Counter()
    clean_transition: Counter[str] = Counter()
    threshold_relation: Counter[str] = Counter()
    threshold_transition: Counter[str] = Counter()
    threshold_context: Counter[str] = Counter()
    exposure_counts: Counter[str] = Counter()
    threshold_rows: list[dict[str, Any]] = []
    clean_examples: list[dict[str, Any]] = []

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
        storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(prepared.snapshots)
        owner_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}

        for row in game_rows:
            before_turn = int(row["before_turn"])
            battle_turn = int(row["battle_turn"])
            ship_id = int(row["ship_id"])
            owner_id = int(row["owner_id"])
            before = row["before"]
            after = row["after"]
            if before_turn not in owner_cache:
                owner_cache[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            owner_rows = owner_cache[before_turn]
            raw_entry = owner_rows.get(ship_id)
            if raw_entry is None:
                totals["owner_current_missing"] += 1
                continue
            raw_owner_id, raw = raw_entry
            if raw_owner_id != owner_id:
                totals["owner_mismatch"] += 1
                continue

            totals["stable_prior_true_rows"] += 1
            before_fuel = _int_value(before.get("fuel"))
            after_fuel = _int_value(after.get("fuel"))
            reference_cost = _int_value(before.get("cloak_reference_cost"))
            debit, relation = _classify_fuel_debit(
                before_fuel=before_fuel,
                after_fuel=after_fuel,
                reference_cost=reference_cost,
            )
            threshold = _fuel_threshold(before_fuel, reference_cost)
            transition = str(row.get("cloak_transition") or "unknown")
            same_position = _same_position(before, after)
            damage_zero = _int_value(before.get("damage")) == 0
            vcr = row.get("vcr_participant") is True
            target_position = _xy(raw)

            race_id = races.get(owner_id)
            effective_warp, warp_issue = _effective_requested_warp(raw, race_id=race_id)
            outbound_transfer = _nonzero_transfer_amount(raw)
            inbound_transfer = ship_id in _inbound_transfer_targets(owner_rows)
            foreign_origin = _foreign_origin_rows(
                owner_rows=owner_rows,
                target_ship_id=ship_id,
                target_owner_id=owner_id,
                origin=target_position,
                races=races,
            )
            loki_exposed, loki_ids = _loki_start_exposure(
                rows=owner_rows,
                target_owner_id=owner_id,
                target_position=target_position,
            )
            glory_rows = _glory_start_context(
                rows=owner_rows,
                target_owner_id=owner_id,
                target_position=target_position,
                specs=specs,
            )
            active_glory = any(item["active_code"] is True for item in glory_rows)

            if before_turn in storm_conflict_turns:
                ion_inside: bool | None = None
                storm_status = "conflict"
            elif before_turn in storm_invalid_turns:
                ion_inside = None
                storm_status = "invalid"
            else:
                ion_inside = _inside_any_ion_disturbance(
                    storms_by_turn.get(before_turn, ()),
                    position=target_position,
                )
                storm_status = "resolved"

            hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
            hull = specs.hulls.get(hull_id) if hull_id is not None else None
            special = str(getattr(hull, "special", "") or "")
            advanced_cloak = "advanced cloak" in special.lower()

            clean = _clean_stationary_fuel_context(
                damage_zero=damage_zero,
                effective_warp=effective_warp,
                same_position=same_position,
                outbound_transfer=outbound_transfer,
                inbound_transfer=inbound_transfer,
                foreign_origin_count=len(foreign_origin),
            )

            exposure_counts["requested_warp_zero" if effective_warp == 0 else "requested_warp_nonzero_or_unknown"] += 1
            exposure_counts["outbound_transfer" if outbound_transfer else "no_outbound_transfer"] += 1
            exposure_counts["inbound_transfer" if inbound_transfer else "no_inbound_transfer"] += 1
            exposure_counts["foreign_at_rob_origin" if foreign_origin else "no_foreign_at_rob_origin"] += 1
            exposure_counts["ion_start_inside" if ion_inside is True else "ion_start_clear" if ion_inside is False else "ion_start_unknown"] += 1
            exposure_counts["loki_start_exposed" if loki_exposed is True else "loki_start_clear" if loki_exposed is False else "loki_start_unknown"] += 1
            exposure_counts["active_glory_colocated" if active_glory else "no_active_glory_colocated"] += 1
            exposure_counts["advanced_cloak_hull" if advanced_cloak else "ordinary_cloak_hull"] += 1

            if clean:
                totals["clean_stationary_no_visible_fuel_mutation"] += 1
                clean_relation[relation] += 1
                clean_transition[transition] += 1
                if relation == "exact_reference_debit":
                    totals["clean_exact_reference_debit"] += 1
                    if len(clean_examples) < args.example_limit:
                        clean_examples.append(
                            {
                                "game_id": game_id,
                                "before_turn": before_turn,
                                "battle_turn": battle_turn,
                                "ship_id": ship_id,
                                "hull_id": hull_id,
                                "before_fuel": before_fuel,
                                "after_fuel": after_fuel,
                                "reference_cost": reference_cost,
                                "fuel_debit": debit,
                                "cloak_transition": transition,
                                "vcr_participant": vcr,
                                "ion_start_inside": ion_inside,
                                "loki_start_exposed": loki_exposed,
                                "active_glory_colocated": active_glory,
                            }
                        )

            at_or_below = threshold in {"equals_reference_cost", "below_reference_cost"}
            if at_or_below:
                totals["threshold_at_or_below_rows"] += 1
                threshold_relation[f"{threshold}:{relation}"] += 1
                threshold_transition[f"{threshold}:{transition}"] += 1
                threshold_context[
                    f"{threshold}|{relation}|{transition}|clean={clean}|vcr={vcr}|ion={ion_inside}|loki={loki_exposed}|glory={active_glory}"
                ] += 1
                threshold_rows.append(
                    {
                        "game_id": game_id,
                        "before_turn": before_turn,
                        "battle_turn": battle_turn,
                        "ship_id": ship_id,
                        "owner_id": owner_id,
                        "hull_id": hull_id,
                        "before_fuel": before_fuel,
                        "after_fuel": after_fuel,
                        "reference_cost": reference_cost,
                        "fuel_threshold": threshold,
                        "fuel_debit": debit,
                        "debit_relation": relation,
                        "cloak_transition": transition,
                        "vcr_participant": vcr,
                        "effective_warp": effective_warp,
                        "warp_issue": warp_issue,
                        "same_position": same_position,
                        "damage_zero": damage_zero,
                        "outbound_transfer": outbound_transfer,
                        "inbound_transfer": inbound_transfer,
                        "foreign_origin_count": len(foreign_origin),
                        "clean_stationary_no_visible_fuel_mutation": clean,
                        "storm_status": storm_status,
                        "ion_start_inside": ion_inside,
                        "loki_start_exposed": loki_exposed,
                        "loki_ship_ids": loki_ids,
                        "active_glory_colocated": active_glory,
                        "glory_rows": glory_rows,
                        "advanced_cloak_hull": advanced_cloak,
                    }
                )

    threshold_rows.sort(
        key=lambda item: (
            int(item["before_fuel"] if item["before_fuel"] is not None else 10**9),
            int(item["game_id"]),
            int(item["before_turn"]),
            int(item["ship_id"]),
        )
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "clean_relation": _serialize(clean_relation),
            "clean_transition": _serialize(clean_transition),
            "threshold_relation": _serialize(threshold_relation),
            "threshold_transition": _serialize(threshold_transition),
            "threshold_context": _serialize(threshold_context),
            "exposure_counts": _serialize(exposure_counts),
            "base_fuel_state_summary": fuel_state.get("summary"),
        },
        "focus_rows": fuel_state.get("focus_rows", ()),
        "threshold_rows": threshold_rows,
        "clean_exact_reference_debit_examples": clean_examples,
        "evidence_boundary": (
            "Attribution-only follow-up for stable prior-true Privateer mission9 cloak-capable rows. The clean subset "
            "requires damage0, effective requested Warp0, unchanged T position, no visible submitted inbound/outbound "
            "transfer and no foreign owner-current ship at the T-1 Rob origin. That removes major visible movement/Rob/"
            "transfer net-fuel confounders but does not prove causality: hidden diplomacy/visibility, starbase refuel, web "
            "drain and other Host phases can still mutate fuel. T-1 ion/Loki/Glory exposure is context only. Mission9 is "
            "still Rob Ship rather than documented ordinary Cloak, and no combat eligibility rule is changed here."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attribute Privateer Rob prior-cloak reference fuel debit and inspect low-fuel threshold controls."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB CLOAK/FUEL ATTRIBUTION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("FOCUS ROWS:")
    for row in report["focus_rows"]:
        print(row)
    print()
    print("THRESHOLD ROWS (FUEL <= REFERENCE COST):")
    for row in report["threshold_rows"]:
        print(row)
    print()
    print("CLEAN EXACT-REFERENCE-DEBIT EXAMPLES:")
    for row in report["clean_exact_reference_debit_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: attribution gate only; no Rob-cloak or combat blocker mechanic is promoted by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
