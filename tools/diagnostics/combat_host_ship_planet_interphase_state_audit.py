from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.interphase import (
    SUPPLIES_PER_DAMAGE_POINT,
    repair_ship_with_supplies,
)

import combat_ship_chain_audit as chain_module
import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_mixed_ship_planet_queue_batch_audit import _shape
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-ship-planet-interphase-state-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80
CARRY_FIELDS = ("damage", "crew", "torpedoes", "fighters")


def _direction(previous: Any, current: Any) -> str:
    if (
        isinstance(previous, bool)
        or not isinstance(previous, int)
        or isinstance(current, bool)
        or not isinstance(current, int)
    ):
        return "unknown"
    if current < previous:
        return "decrease"
    if current > previous:
        return "increase"
    return "same"


def _tminus1_context(
    ship_groups: Mapping[Any, Any],
    *,
    battle_turn: int,
    ship_id: int,
) -> dict[str, Any]:
    owner_id, raw = _owner_raw(ship_groups, battle_turn - 1, ship_id)
    if owner_id is None or not isinstance(raw, Mapping):
        return {"resolved": False, "reason": "ship_tminus1_unresolved"}

    def value(name: str) -> int | None:
        return _intish(raw.get(name))

    return {
        "resolved": True,
        "owner_id": owner_id,
        "mission": value("mission"),
        "mission1target": value("mission1target"),
        "enemy": value("enemy"),
        "friendlycode": (
            raw.get("friendlycode")
            if isinstance(raw.get("friendlycode"), str)
            else None
        ),
        "supplies": value("supplies"),
        "duranium": value("duranium"),
        "tritanium": value("tritanium"),
        "molybdenum": value("molybdenum"),
        "megacredits": value("megacredits"),
        "damage": value("damage"),
        "torps": value("torps"),
        "ammo": value("ammo"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    chain_report = chain_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            archive=[],
            output=None,
            detail_limit=200,
            sample_limit=20,
        )
    )
    transitions = chain_report.get("transitions")
    transitions = transitions if isinstance(transitions, list) else []

    vcrs, payload_conflicts = opponent_module._vcr_index(args.archive_dir)
    groups_by_game: dict[int, Mapping[Any, Any]] = {}

    counts: Counter[str] = Counter()
    field_directions: dict[str, Counter[str]] = {
        field: Counter() for field in CARRY_FIELDS
    }
    shield_models: Counter[str] = Counter()
    gap_counts: Counter[int] = Counter()
    examples: list[dict[str, Any]] = []
    changed_examples: list[dict[str, Any]] = []
    repair_compatibility: Counter[str] = Counter()

    for row in transitions:
        if not isinstance(row, Mapping):
            continue
        game_id = int(row["game_id"])
        if game_id == SPECIAL_GAME_ID:
            continue
        battle_turn = int(row["turn"])
        from_vcr = int(row["from_vcr"])
        to_vcr = int(row["to_vcr"])

        source = vcrs.get((game_id, battle_turn, from_vcr))
        target = vcrs.get((game_id, battle_turn, to_vcr))
        if not isinstance(source, Mapping) or not isinstance(target, Mapping):
            counts["required_unresolved:vcr_lookup"] += 1
            continue
        if _shape(source) != "ship_vs_ship" or _shape(target) != "ship_vs_planet":
            continue

        counts["ship_to_planet_transitions"] += 1
        gap_counts[to_vcr - from_vcr] += 1
        comparison = row.get("comparison")
        if not isinstance(comparison, Mapping):
            counts["required_unresolved:comparison"] += 1
            continue

        status = str(comparison.get("status", "unknown"))
        counts[f"status:{status}"] += 1
        if status == "reappearance_after_defeat":
            counts["defeated_predecessor_reappearance"] += 1
        elif status == "match":
            counts["ordinary_exact_transition"] += 1
        elif status == "mismatch":
            counts["ordinary_transition_with_change"] += 1
        elif status == "not_comparable":
            counts["ordinary_not_comparable"] += 1

        carry = comparison.get("carry")
        changed_fields: list[str] = []
        if isinstance(carry, Mapping):
            for field in CARRY_FIELDS:
                values = carry.get(field)
                if not isinstance(values, Mapping):
                    field_directions[field]["unknown"] += 1
                    continue
                terminal = values.get("terminal")
                next_start = values.get("next_start")
                direction = _direction(terminal, next_start)
                field_directions[field][direction] += 1
                if direction not in {"same", "unknown"}:
                    changed_fields.append(field)

        shield = comparison.get("shield")
        shield_model = "unknown"
        if isinstance(shield, Mapping):
            shield_model = str(shield.get("model", "unknown"))
        shield_models[shield_model] += 1

        ship_id = int(row["ship_id"])
        if game_id not in groups_by_game:
            archive_path = args.archive_dir / f"game-{game_id}.zip"
            prepared, _ = load_or_build_prepared_game_cache(
                archive_path.read_bytes(),
                game_id=game_id,
                cache_path=args.prepared_dir / f"game-{game_id}.pickle",
            )
            groups_by_game[game_id] = group_perspective_records(
                prepared.snapshots,
                "ship",
            )
        context = _tminus1_context(
            groups_by_game[game_id],
            battle_turn=battle_turn,
            ship_id=ship_id,
        )

        repair_projection: dict[str, Any] | None = None
        if status in {"match", "mismatch"}:
            carry = comparison.get("carry")
            damage_values = carry.get("damage") if isinstance(carry, Mapping) else None
            terminal_damage = (
                damage_values.get("terminal")
                if isinstance(damage_values, Mapping)
                else None
            )
            next_damage = (
                damage_values.get("next_start")
                if isinstance(damage_values, Mapping)
                else None
            )
            supplies = context.get("supplies") if isinstance(context, Mapping) else None
            if (
                isinstance(terminal_damage, int)
                and not isinstance(terminal_damage, bool)
                and isinstance(next_damage, int)
                and not isinstance(next_damage, bool)
                and isinstance(supplies, int)
                and not isinstance(supplies, bool)
                and supplies >= 0
            ):
                observed_repair = terminal_damage - next_damage
                max_from_tminus1 = min(
                    terminal_damage,
                    supplies // SUPPLIES_PER_DAMAGE_POINT,
                )
                if observed_repair < 0:
                    compatibility = "damage_increased"
                elif observed_repair > max_from_tminus1:
                    compatibility = "exceeds_tminus1_supply_budget"
                elif observed_repair == max_from_tminus1:
                    compatibility = "full_tminus1_budget_exact"
                else:
                    compatibility = "compatible_with_prior_supply_consumption"

                repair_compatibility[compatibility] += 1
                if observed_repair > 0:
                    counts["observed_supply_repair_transitions"] += 1
                    row_non_damage_preserved = True
                    if isinstance(carry, Mapping):
                        for field in ("crew", "torpedoes", "fighters"):
                            values = carry.get(field)
                            if (
                                not isinstance(values, Mapping)
                                or values.get("matches") is not True
                            ):
                                row_non_damage_preserved = False
                    else:
                        row_non_damage_preserved = False

                    if row_non_damage_preserved:
                        counts["repair_rows_non_damage_state_preserved"] += 1
                    else:
                        counts["repair_rows_non_damage_state_changed"] += 1

                    if shield_model in {"exact_carry", "both"}:
                        counts["repair_rows_without_shield_recharge"] += 1
                    else:
                        counts["repair_rows_with_other_shield_model"] += 1

                production_damage = None
                if compatibility == "full_tminus1_budget_exact":
                    raw = {
                        "hull_id": int(row["hull_id"]),
                        "damage": terminal_damage,
                        "supplies": supplies,
                        "physical_beam_count": 0,
                        "physical_launcher_count": 0,
                        "physical_bay_count": 0,
                        "beam_count": 0,
                        "launcher_count": 0,
                        "bay_count": 0,
                        "shield": 0,
                        "crew": 1,
                        "torpedoes": 0,
                        "fighters": 0,
                        "federation_crew_bonus": False,
                        "lizard_crew_bonus": False,
                    }
                    repaired_state, repaired = repair_ship_with_supplies(raw)
                    production_damage = repaired_state["damage"]
                    if production_damage == next_damage:
                        counts["production_supply_repair_exact"] += 1
                    else:
                        counts["production_supply_repair_mismatch"] += 1

                repair_projection = {
                    "terminal_damage": terminal_damage,
                    "next_damage": next_damage,
                    "observed_repair": observed_repair,
                    "tminus1_supplies": supplies,
                    "max_repair_from_tminus1_supplies": max_from_tminus1,
                    "compatibility": compatibility,
                    "production_damage_when_full_tminus1_budget": production_damage,
                }
            else:
                repair_compatibility["unresolved"] += 1

        projection = {
            "game_id": game_id,
            "battle_turn": battle_turn,
            "ship_id": ship_id,
            "from_vcr": from_vcr,
            "to_vcr": to_vcr,
            "vcr_gap": to_vcr - from_vcr,
            "status": status,
            "changed_fields": changed_fields,
            "shield_model": shield_model,
            "comparison": comparison,
            "tminus1": context,
            "repair_projection": repair_projection,
        }
        if len(examples) < args.example_limit:
            examples.append(projection)
        if (
            status in {"mismatch", "not_comparable"}
            or changed_fields
            or shield_model == "mismatch"
        ) and len(changed_examples) < args.example_limit:
            changed_examples.append(projection)

    population = int(counts["ship_to_planet_transitions"])
    required_unresolved = sum(
        value
        for key, value in counts.items()
        if key.startswith("required_unresolved:")
    )
    repair_contradictions = (
        int(repair_compatibility["damage_increased"])
        + int(repair_compatibility["exceeds_tminus1_supply_budget"])
    )
    acceptance = {
        "ship_to_planet_population_present": population > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "required_inputs_resolved": required_unresolved == 0,
        "supply_repair_population_present": int(counts["observed_supply_repair_transitions"]) > 0,
        "all_damage_changes_supply_repair_compatible": repair_contradictions == 0,
        "production_full_budget_rows_exact": int(counts["production_supply_repair_mismatch"]) == 0,
        "repair_rows_preserve_crew_and_ammunition": int(counts["repair_rows_non_damage_state_changed"]) == 0,
        "repair_rows_do_not_recharge_shields": int(counts["repair_rows_with_other_shield_model"]) == 0,
        "ordinary_transition_population_present": (
            int(counts["ordinary_exact_transition"])
            + int(counts["ordinary_transition_with_change"])
            + int(counts["ordinary_not_comparable"])
        ) > 0,
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "payload_conflicts": payload_conflicts,
            "chain_audit_summary": chain_report.get("summary"),
            "counts": dict(sorted(counts.items())),
            "field_directions": {
                field: dict(sorted(values.items()))
                for field, values in field_directions.items()
            },
            "shield_models": dict(sorted(shield_models.items())),
            "repair_compatibility": dict(sorted(repair_compatibility.items())),
            "vcr_gap_distribution": {
                str(key): value for key, value in sorted(gap_counts.items())
            },
            "acceptance": acceptance,
        },
        "changed_examples": changed_examples,
        "examples": examples,
        "evidence_boundary": (
            "Read-only phase-boundary differential. It selects ordinary "
            "same-turn/same-location appearances where one ship's previous VCR "
            "is ship-vs-ship and its next VCR is ship-vs-planet/base. The source "
            "ship terminal state comes from deterministic replay and is compared "
            "with the factual planet-combat start state. Changes are inventoried "
            "rather than explained. T-1 cargo/order state is context only. "
            "Captured/defeated predecessor reappearances remain separate from "
            "ordinary survivor transitions. The documented five-supplies-per-"
            "damage-point production repair primitive is checked where T-1 "
            "supplies are a sufficient current-budget proxy; rows requiring "
            "earlier Host supply consumption are classified separately. MKT "
            "torpedo construction remains outside this gate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit ship state changes across the Host ship-combat to "
            "planet-combat repair/MKT phase boundary."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT SHIP->PLANET INTERPHASE STATE AUDIT =====")
    print("summary:", report["summary"])
    if report["changed_examples"]:
        print()
        print("CHANGED / RESIDUAL EXAMPLES:")
        for row in report["changed_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: supply repair is production-checked; prior Host supply consumption "
        "and MKT torpedo construction remain separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
