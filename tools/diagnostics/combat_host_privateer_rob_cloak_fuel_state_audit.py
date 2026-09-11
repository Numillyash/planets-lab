from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat_host_candidate_set_audit import _serialize
from combat_host_privateer_rob_cloak_population_audit import run as run_population
from combat_host_privateer_rob_initial_cloak_context_audit import run as run_initial_context
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-privateer-rob-cloak-fuel-state-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _same_position(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool | None:
    bx = _int_value(before.get("x"))
    by = _int_value(before.get("y"))
    ax = _int_value(after.get("x"))
    ay = _int_value(after.get("y"))
    if None in (bx, by, ax, ay):
        return None
    return (bx, by) == (ax, ay)


def _classify_fuel_debit(
    *,
    before_fuel: int | None,
    after_fuel: int | None,
    reference_cost: int | None,
) -> tuple[int | None, str]:
    if before_fuel is None or after_fuel is None:
        return None, "fuel_unresolved"
    debit = before_fuel - after_fuel
    if reference_cost is None:
        return debit, "reference_cost_unresolved"
    if debit == reference_cost:
        return debit, "exact_reference_debit"
    if debit == 0:
        return debit, "zero_debit"
    return debit, "other_debit"


def _fuel_threshold(before_fuel: int | None, reference_cost: int | None) -> str:
    if before_fuel is None or reference_cost is None:
        return "unresolved"
    if before_fuel < reference_cost:
        return "below_reference_cost"
    if before_fuel == reference_cost:
        return "equals_reference_cost"
    return "above_reference_cost"


def _focus_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    target = row.get("target")
    target = target if isinstance(target, Mapping) else {}
    before_fuel = _int_value(target.get("fuel"))
    reference_cost = _int_value(target.get("basic_cloak_fuel_cost"))
    after_state = row.get("target_t_state_attribution_only")
    after_state = after_state if isinstance(after_state, Mapping) else None
    after_fuel = _int_value(after_state.get("fuel")) if after_state is not None else None
    observed_debit, observed_relation = _classify_fuel_debit(
        before_fuel=before_fuel,
        after_fuel=after_fuel,
        reference_cost=reference_cost,
    )
    hypothetical_after = (
        before_fuel - reference_cost
        if before_fuel is not None and reference_cost is not None
        else None
    )
    return {
        "game_id": int(row["game_id"]),
        "battle_turn": int(row["battle_turn"]),
        "classification": row.get("classification"),
        "target_ship_id": int(row["target_ship_id"]),
        "attacker_ship_id": int(row["attacker_ship_id"]),
        "before_fuel": before_fuel,
        "reference_cost": reference_cost,
        "fuel_threshold": _fuel_threshold(before_fuel, reference_cost),
        "stable_t_identity": row.get("target_t_identity_stable") is True,
        "observed_t_fuel": after_fuel,
        "observed_fuel_debit": observed_debit,
        "observed_debit_relation": observed_relation,
        "hypothetical_after_reference_debit": hypothetical_after,
        "reference_debit_exhausts_fuel": hypothetical_after == 0 if hypothetical_after is not None else None,
        "damage": _int_value(target.get("damage")),
        "prior_iscloaked": target.get("iscloaked"),
        "t_iscloaked_attribution_only": (
            after_state.get("iscloaked") if after_state is not None else None
        ),
        "loki_start": bool(
            isinstance(row.get("loki_context"), Mapping)
            and row["loki_context"].get("any_active_start_within_10") is True
        ),
        "foreign_origin_count": (
            _int_value(row.get("rob_origin", {}).get("foreign_colocated_count"))
            if isinstance(row.get("rob_origin"), Mapping)
            else None
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    population = run_population(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )
    context = run_initial_context(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )

    totals: Counter[str] = Counter()
    by_relation: Counter[str] = Counter()
    by_transition: Counter[str] = Counter()
    by_context: Counter[str] = Counter()
    by_game: Counter[str] = Counter()
    by_hull: Counter[str] = Counter()
    exact_examples: list[dict[str, Any]] = []

    for raw_row in population.get("examples", ()):
        if not isinstance(raw_row, Mapping):
            continue
        if raw_row.get("stable_identity") is not True:
            continue
        before = raw_row.get("before")
        after = raw_row.get("after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            continue
        if before.get("iscloaked") is not True:
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
        transition = str(raw_row.get("cloak_transition") or "unknown")
        pe_zero = raw_row.get("primary_enemy_zero") is True
        vcr = raw_row.get("vcr_participant") is True
        same_position = _same_position(before, after)
        damage_zero = _int_value(before.get("damage")) == 0
        game_id = str(raw_row.get("game_id"))
        hull_id = str(before.get("hullid"))

        if before_fuel is not None and after_fuel is not None:
            totals["fuel_delta_resolved"] += 1
        totals[relation] += 1
        totals[f"threshold:{threshold}"] += 1
        totals["same_position" if same_position is True else "position_changed" if same_position is False else "position_unresolved"] += 1
        totals["damage_zero" if damage_zero else "damage_nonzero_or_unknown"] += 1

        by_relation[f"{relation}:{transition}"] += 1
        by_relation[f"{relation}:pe0={pe_zero}"] += 1
        by_relation[f"{relation}:vcr={vcr}"] += 1
        by_transition[transition] += 1
        by_context[
            f"{relation}|same_position={same_position}|damage_zero={damage_zero}|pe0={pe_zero}|vcr={vcr}"
        ] += 1
        by_game[f"{game_id}:{relation}"] += 1
        by_hull[f"{hull_id}:{relation}"] += 1

        if relation == "exact_reference_debit" and len(exact_examples) < args.example_limit:
            exact_examples.append(
                {
                    "game_id": raw_row.get("game_id"),
                    "before_turn": raw_row.get("before_turn"),
                    "battle_turn": raw_row.get("battle_turn"),
                    "ship_id": raw_row.get("ship_id"),
                    "hull_id": before.get("hullid"),
                    "before_fuel": before_fuel,
                    "after_fuel": after_fuel,
                    "fuel_debit": debit,
                    "reference_cost": reference_cost,
                    "fuel_threshold": threshold,
                    "same_position": same_position,
                    "damage_zero": damage_zero,
                    "cloak_transition": transition,
                    "primary_enemy_zero": pe_zero,
                    "vcr_participant": vcr,
                }
            )

    focus_rows = [
        _focus_projection(row)
        for row in context.get("rows", ())
        if isinstance(row, Mapping)
    ]
    focus_rows.sort(
        key=lambda row: (
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
            "by_relation": _serialize(by_relation),
            "by_transition": _serialize(by_transition),
            "by_context": _serialize(by_context),
            "by_game": _serialize(by_game),
            "by_hull": _serialize(by_hull),
            "base_population_summary": population.get("summary"),
            "base_focus_summary": context.get("summary"),
            "focus_rows": len(focus_rows),
        },
        "focus_rows": focus_rows,
        "exact_reference_debit_examples": exact_examples,
        "evidence_boundary": (
            "Population-level attribution audit for stable physical Privateer race5 mission9 cloak-capable rows whose "
            "archived T-1 iscloaked bit is true. An exact fuel debit equal to the ordinary cloak reference cost is an "
            "observed transition shape only: mission9 is Rob Ship, not the documented ordinary Cloak mission, and T is "
            "post-Host. This diagnostic therefore measures prevalence and correlation; it does not assert that Rob Ship "
            "causes the debit or that the debit reconstructs combat-effective cloak. The four clean initial target rows "
            "are projected separately; ship118 receives only a labelled hypothetical reference debit because its T "
            "physical identity is not stable. No combat rule is changed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure Privateer Rob prior-cloak fuel-state deltas and exact ordinary-cloak-cost correlations."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB CLOAK/FUEL STATE AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("FOCUS ROWS:")
    for row in report["focus_rows"]:
        print(row)
    print()
    print("EXACT REFERENCE-DEBIT EXAMPLES:")
    for row in report["exact_reference_debit_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: population correlation only; mission9/Rob is not promoted as a cloak-fuel mechanic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
