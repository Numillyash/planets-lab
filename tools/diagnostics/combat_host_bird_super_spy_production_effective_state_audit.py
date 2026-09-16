from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.rules.combat.effective_state import (
    bird_super_spy_ordinary_cloak_state,
    standard_targetability_from_effective_cloak,
)

import combat_host_bird_super_spy_attack_opportunity_audit as population_module
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-bird-super-spy-production-effective-state-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 120


def _production_candidate(
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
    state = bird_super_spy_ordinary_cloak_state(
        race_id=race_id,
        mission=mission,
        hull_can_cloak=hull_can_cloak,
        advanced_cloak=advanced_cloak,
        damage=damage,
        fuel_before=fuel_before,
        ordinary_cloak_reference_cost=reference_cost,
        reference_move_resolved=reference_move_resolved,
        reference_remaining_fuel=reference_remaining_fuel,
        prior_iscloaked=prior_iscloaked,
        ion_start_inside=ion_start_inside,
        planet_ion_pulse_possible=planet_ion_pulse_possible,
        loki_start_exposed=loki_start_exposed,
        active_glory_colocated=active_glory_colocated,
    )
    return state.effective_cloak, state.reason


def run(args: argparse.Namespace) -> dict[str, Any]:
    original_candidate = population_module._documented_super_spy_effective_cloak_candidate
    population_module._documented_super_spy_effective_cloak_candidate = _production_candidate
    try:
        population = population_module.run(
            argparse.Namespace(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                example_limit=args.example_limit,
                output=None,
            )
        )
    finally:
        population_module._documented_super_spy_effective_cloak_candidate = original_candidate

    summary_raw = population.get("summary")
    summary = summary_raw if isinstance(summary_raw, Mapping) else {}
    population_acceptance_raw = summary.get("acceptance")
    population_acceptance = (
        population_acceptance_raw if isinstance(population_acceptance_raw, Mapping) else {}
    )

    target_rows_raw = population.get("target_residual")
    target_rows = target_rows_raw if isinstance(target_rows_raw, list) else []
    target_targetability: list[dict[str, Any]] = []
    for row in target_rows:
        if not isinstance(row, Mapping):
            continue
        state_raw = row.get("candidate_state")
        state = state_raw if isinstance(state_raw, Mapping) else {}
        effective_cloak = state.get("effective_cloak")
        if effective_cloak not in (True, False, None):
            effective_cloak = None
        # Reconstruct only the already-produced state value here; the population
        # mechanics above used the production helper itself.
        from planets_lab.rules.combat.effective_state import EffectiveCloakState

        projected = standard_targetability_from_effective_cloak(
            EffectiveCloakState(
                effective_cloak=effective_cloak,
                reason=str(state.get("reason") or "population_state"),
            )
        )
        target_targetability.append(
            {
                "game_id": row.get("game_id"),
                "battle_turn": row.get("battle_turn"),
                "target_ship_id": row.get("target_ship_id"),
                "attacker_ship_id": row.get("attacker_ship_id"),
                "effective_cloak": effective_cloak,
                "standard_targetable_by_opponent": projected.targetable_by_opponent,
                "reason": projected.reason,
            }
        )

    target_residual_blocked = any(
        row.get("effective_cloak") is True
        and row.get("standard_targetable_by_opponent") is False
        for row in target_targetability
    )

    acceptance = {
        "population_no_race_conflicts": population_acceptance.get("no_race_conflicts") is True,
        "population_no_payload_conflicts": population_acceptance.get("no_payload_conflicts") is True,
        "population_no_blocked_factual_pair_regressions": population_acceptance.get(
            "no_blocked_factual_pair_regressions"
        )
        is True,
        "population_no_decisive_mismatch": population_acceptance.get("no_decisive_mismatch")
        is True,
        "population_target_residual_present": population_acceptance.get("target_residual_present")
        is True,
        "population_target_residual_supported": population_acceptance.get(
            "target_residual_supported"
        )
        is True,
        "production_targetability_blocks_target_residual": target_residual_blocked,
        "advanced_rows_remain_unresolved": int(summary.get("decisive_unresolved") or 0) == 3,
    }
    acceptance["production_effective_state_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "population": summary,
            "target_residual_targetability": target_targetability,
            "acceptance": acceptance,
        },
        "evidence_boundary": (
            "Production-effective-state differential for the ordinary Bird Super Spy branch only. The existing population "
            "audit constructs positions, one-way hostile plain-STANDARD opportunities and factual labels exactly as before, "
            "but its effective-cloak candidate is temporarily replaced by planets_lab.rules.combat.effective_state." 
            "bird_super_spy_ordinary_cloak_state. The targetability projection is the production "
            "standard_targetability_from_effective_cloak mapping. Advanced Cloak is required to remain unresolved; historical "
            "T/messages/VCR outcomes are not production state inputs."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate production Bird ordinary Super Spy effective-state reconstruction against the historical population gate."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT BIRD SUPER SPY PRODUCTION EFFECTIVE STATE =====")
    print("summary:", report["summary"])
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("output:", args.output)
    print("NOTE: ordinary Bird Super Spy production effective-state gate; Advanced Cloak remains unresolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
