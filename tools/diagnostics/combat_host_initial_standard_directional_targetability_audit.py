from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat_host_bird_advanced_cloak_decisive_closure_audit import (
    run as run_advanced_closure,
)
from combat_host_bird_super_spy_attack_opportunity_audit import (
    run as run_bird_population,
)
from combat_host_initial_standard_target_audit import run as run_initial_standard_target
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR
from combat_host_privateer_rob_selector_impact_audit import (
    BIRD_RESIDUAL,
    PRIVATEER_RESIDUAL,
    _impact_classification,
    _mismatch_projection,
    run as run_privateer_impact,
)


SCHEMA = "planets-lab.combat-host-initial-standard-directional-targetability-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 160

REGRESSION_IMPACTS = frozenset(
    {
        "blocked_factual_pair_regression",
        "blocked_initial_pair_regression",
        "blocked_later_pair_first_effect_unresolved",
        "blocked_phantom_attacker_first_effect_unresolved",
        "blocked_first_effect_unresolved",
    }
)


def _opportunity_key(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(row["game_id"]),
        int(row["battle_turn"]),
        int(row["target_ship_id"]),
        int(row["attacker_ship_id"]),
    )


def _profile_exact(summary: Mapping[str, Any], profile: str) -> bool:
    raw_profile = summary.get(profile)
    raw_profile = raw_profile if isinstance(raw_profile, Mapping) else {}
    exact = raw_profile.get("exact_set")
    exact = exact if isinstance(exact, Mapping) else {}
    sites = int(exact.get("sites") or 0)
    return bool(
        sites > 0
        and int(exact.get("first_pair_exact") or 0) == sites
        and int(exact.get("first_pair_mismatch") or 0) == 0
        and int(exact.get("first_right_exact") or 0) == sites
        and int(exact.get("first_right_mismatch") or 0) == 0
    )


def _project_mismatch_repair(
    *,
    mismatch: Mapping[str, Any],
    blocked_keys: set[tuple[int, int, int, int]],
) -> dict[str, Any]:
    game_id = int(mismatch["game_id"])
    battle_turn = int(mismatch["battle_turn"])
    predicted_target, predicted_active, factual_target_rank, factual_right = _mismatch_projection(mismatch)
    key = None
    if predicted_target is not None and predicted_active is not None:
        key = (game_id, battle_turn, int(predicted_target), int(predicted_active))
    blocked = key in blocked_keys if key is not None else False
    fixed = bool(
        blocked
        and factual_target_rank == 2
        and predicted_active is not None
        and predicted_active == factual_right
    )
    residual = (game_id, battle_turn, predicted_target)
    return {
        "game_id": game_id,
        "battle_turn": battle_turn,
        "profile": mismatch.get("profile"),
        "predicted_target_ship_id": predicted_target,
        "predicted_active_ship_id": predicted_active,
        "factual_target_rank_within_top_active": factual_target_rank,
        "factual_right_ship_id": factual_right,
        "supported_block_matches_prediction": blocked,
        "projected_fixed_by_directional_targetability": fixed,
        "is_privateer_residual": residual == PRIVATEER_RESIDUAL,
        "is_bird_residual": residual == BIRD_RESIDUAL,
    }


def _supported_block_row(
    raw: Mapping[str, Any],
    *,
    source: str,
    effective_reason: str,
) -> dict[str, Any]:
    classification = raw.get("initial_classification")
    if classification is None:
        initial_context = raw.get("initial_context")
        if isinstance(initial_context, Mapping):
            classification = initial_context.get("classification")
    factual_outcome = raw.get("factual_outcome")
    impact = _impact_classification(
        effective_cloak=True,
        initial_classification=classification,
        factual_outcome=factual_outcome,
    )
    return {
        "game_id": int(raw["game_id"]),
        "before_turn": int(raw["before_turn"]),
        "battle_turn": int(raw["battle_turn"]),
        "target_ship_id": int(raw["target_ship_id"]),
        "attacker_ship_id": int(raw["attacker_ship_id"]),
        "source": source,
        "effective_reason": effective_reason,
        "factual_outcome": factual_outcome,
        "initial_classification": classification,
        "selector_impact": impact,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    common = SimpleNamespace(
        archive_dir=args.archive_dir,
        prepared_dir=args.prepared_dir,
        example_limit=100000,
        output=None,
    )
    baseline = run_initial_standard_target(common)
    privateer = run_privateer_impact(common)
    bird = run_bird_population(common)
    advanced = run_advanced_closure(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            output=None,
        )
    )

    privateer_summary = privateer.get("summary")
    privateer_summary = privateer_summary if isinstance(privateer_summary, Mapping) else {}
    privateer_acceptance = privateer_summary.get("acceptance")
    privateer_acceptance = privateer_acceptance if isinstance(privateer_acceptance, Mapping) else {}

    bird_summary = bird.get("summary")
    bird_summary = bird_summary if isinstance(bird_summary, Mapping) else {}
    bird_acceptance = bird_summary.get("acceptance")
    bird_acceptance = bird_acceptance if isinstance(bird_acceptance, Mapping) else {}

    advanced_acceptance = advanced.get("acceptance")
    advanced_acceptance = advanced_acceptance if isinstance(advanced_acceptance, Mapping) else {}

    supported_rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    # Privateer: only the already-tested helper=True rows become directional blocks.
    for raw in privateer.get("overlay_rows", ()):
        if not isinstance(raw, Mapping) or raw.get("helper_effective_cloak") is not True:
            continue
        supported_rows.append(
            _supported_block_row(
                raw,
                source="privateer_rob_ordinary",
                effective_reason=str(raw.get("helper_reason") or "privateer_helper_true"),
            )
        )

    bird_rows_by_key: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for raw in bird.get("rows", ()):
        if not isinstance(raw, Mapping):
            continue
        bird_rows_by_key[_opportunity_key(raw)] = raw
        state = raw.get("candidate_state")
        state = state if isinstance(state, Mapping) else {}
        if raw.get("candidate_blocked") is not True:
            continue
        if state.get("advanced_cloak") is True:
            # Advanced rows are admitted only by the dedicated closure below.
            continue
        supported_rows.append(
            _supported_block_row(
                raw,
                source="bird_super_spy_ordinary",
                effective_reason=str(state.get("reason") or "bird_ordinary_candidate_true"),
            )
        )

    advanced_eligible_controls: list[dict[str, Any]] = []
    for closure in advanced.get("rows", ()):
        if not isinstance(closure, Mapping) or closure.get("closure_match") is not True:
            continue
        key = _opportunity_key(closure)
        population_row = bird_rows_by_key.get(key)
        if closure.get("expected_blocked") is True:
            if population_row is None:
                conflicts.append({"key": list(key), "reason": "advanced_block_missing_population_row"})
                continue
            supported_rows.append(
                _supported_block_row(
                    population_row,
                    source="bird_super_spy_advanced_historical_control",
                    effective_reason=str(closure.get("closure_reason") or "advanced_control_closed"),
                )
            )
        else:
            advanced_eligible_controls.append(
                {
                    "key": list(key),
                    "closure_reason": closure.get("closure_reason"),
                    "population_row_found": population_row is not None,
                    "factual_outcome": (
                        population_row.get("factual_outcome") if population_row is not None else None
                    ),
                    "expected_blocked": (
                        population_row.get("expected_blocked") if population_row is not None else None
                    ),
                }
            )

    # Deduplicate exact directional opportunities and fail closed on contradictory sources.
    dedup: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for row in supported_rows:
        key = _opportunity_key(row)
        prior = dedup.get(key)
        if prior is None:
            dedup[key] = row
            continue
        if (
            prior.get("selector_impact") != row.get("selector_impact")
            or prior.get("factual_outcome") != row.get("factual_outcome")
            or prior.get("initial_classification") != row.get("initial_classification")
        ):
            conflicts.append(
                {
                    "key": list(key),
                    "reason": "supported_block_conflict",
                    "first": prior,
                    "second": row,
                }
            )
        else:
            sources = sorted({str(prior.get("source")), str(row.get("source"))})
            merged = dict(prior)
            merged["source"] = "+".join(sources)
            dedup[key] = merged

    supported_rows = [dedup[key] for key in sorted(dedup)]
    blocked_keys = set(dedup)
    impacts = Counter(str(row.get("selector_impact") or "unresolved") for row in supported_rows)
    sources = Counter(str(row.get("source") or "unknown") for row in supported_rows)

    potential_regression_rows = sum(impacts[name] for name in REGRESSION_IMPACTS)
    blocked_factual_pair_rows = impacts["blocked_factual_pair_regression"]

    baseline_summary = baseline.get("summary")
    baseline_summary = baseline_summary if isinstance(baseline_summary, Mapping) else {}
    strict_exact_clean = _profile_exact(baseline_summary, "strict")
    conditional_exact_clean = _profile_exact(baseline_summary, "conditional")

    mismatch_projection: list[dict[str, Any]] = []
    mismatch_total = 0
    mismatch_fixed = 0
    privateer_profiles = 0
    privateer_fixed = 0
    bird_profiles = 0
    bird_fixed = 0
    unrelated = 0
    for mismatch in baseline.get("mismatch_examples", ()):
        if not isinstance(mismatch, Mapping):
            continue
        item = _project_mismatch_repair(mismatch=mismatch, blocked_keys=blocked_keys)
        mismatch_projection.append(item)
        mismatch_total += 1
        if item["projected_fixed_by_directional_targetability"]:
            mismatch_fixed += 1
        if item["is_privateer_residual"]:
            privateer_profiles += 1
            if item["projected_fixed_by_directional_targetability"]:
                privateer_fixed += 1
        elif item["is_bird_residual"]:
            bird_profiles += 1
            if item["projected_fixed_by_directional_targetability"]:
                bird_fixed += 1
        else:
            unrelated += 1

    advanced_eligible_closed = bool(
        len(advanced_eligible_controls) == 1
        and advanced_eligible_controls[0].get("population_row_found") is True
        and advanced_eligible_controls[0].get("factual_outcome") == "pair_vcr"
        and advanced_eligible_controls[0].get("expected_blocked") is False
    )

    privateer_gate_clean = all(
        privateer_acceptance.get(name) is True
        for name in (
            "no_blocked_factual_pair",
            "no_potential_first_selector_regression",
            "privateer_residual_all_profiles_projected_fixed",
            "bird_residual_present_and_unaffected",
        )
    )
    bird_gate_clean = all(
        bird_acceptance.get(name) is True
        for name in (
            "no_race_conflicts",
            "no_payload_conflicts",
            "no_blocked_factual_pair_regressions",
            "no_decisive_mismatch",
            "target_residual_present",
            "target_residual_supported",
        )
    )
    advanced_gate_clean = advanced_acceptance.get("all_decisive_advanced_rows_explained") is True

    # If an exact-set site had a supported blocked pair, that pair would by definition
    # be factual. Therefore zero supported blocked factual pairs preserves every
    # already-exact candidate set without needing to pretend Host messages are inputs.
    exact_set_controls_preserved = bool(
        strict_exact_clean
        and conditional_exact_clean
        and blocked_factual_pair_rows == 0
        and potential_regression_rows == 0
    )

    acceptance = {
        "privateer_gate_clean": privateer_gate_clean,
        "bird_population_gate_clean": bird_gate_clean,
        "advanced_decisive_closure_clean": advanced_gate_clean,
        "no_supported_block_conflicts": len(conflicts) == 0,
        "no_supported_blocked_factual_pairs": blocked_factual_pair_rows == 0,
        "no_potential_first_selector_regressions": potential_regression_rows == 0,
        "strict_and_conditional_exact_set_controls_preserved": exact_set_controls_preserved,
        "all_baseline_mismatch_profiles_fixed": mismatch_total > 0 and mismatch_fixed == mismatch_total,
        "privateer_residual_all_profiles_fixed": privateer_profiles > 0 and privateer_fixed == privateer_profiles,
        "bird_residual_all_profiles_fixed": bird_profiles > 0 and bird_fixed == bird_profiles,
        "no_unrelated_baseline_mismatches": unrelated == 0,
        "advanced_mine_hit_eligible_control_preserved": advanced_eligible_closed,
    }
    acceptance["directional_targetability_population_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "supported_block_rows": len(supported_rows),
            "supported_block_sources": dict(sorted(sources.items())),
            "selector_impact_counts": dict(sorted(impacts.items())),
            "supported_block_conflicts": len(conflicts),
            "blocked_factual_pair_rows": blocked_factual_pair_rows,
            "potential_first_selector_regression_rows": potential_regression_rows,
            "baseline_mismatch_profiles": mismatch_total,
            "baseline_mismatch_profiles_fixed": mismatch_fixed,
            "privateer_residual_profiles": privateer_profiles,
            "privateer_residual_profiles_fixed": privateer_fixed,
            "bird_residual_profiles": bird_profiles,
            "bird_residual_profiles_fixed": bird_fixed,
            "unrelated_baseline_mismatches": unrelated,
            "baseline_initial_standard": baseline_summary,
            "privateer_selector_impact": privateer_summary,
            "bird_population": bird_summary,
            "advanced_closure": advanced.get("summary"),
            "acceptance": acceptance,
        },
        "supported_blocks": supported_rows[: args.example_limit],
        "advanced_eligible_controls": advanced_eligible_controls,
        "mismatch_projection": mismatch_projection[: args.example_limit],
        "conflicts": conflicts[: args.example_limit],
        "evidence_boundary": (
            "Read-only population composition gate for directional ordinary-STANDARD targetability. It combines only "
            "already-supported block rows: DIFF_VERIFIED Privateer Rob ordinary cloak, documented/corpus-tested Bird ordinary "
            "Super Spy cloak, and the two identity-safe historically closed Advanced-Cloak controls. The mine-hit ship68 row "
            "is retained only as an explicit eligible control. Host messages and T state are evidence labels, never production "
            "inputs. No generic predictive Advanced-Cloak resolver is claimed. Exact-set preservation follows from the already "
            "exact baseline plus zero supported blocked factual pairs; broad mismatch repair is projected only when the blocked "
            "direction exactly matches the baseline predicted rank-1 target/active pair and the factual target is rank 2. "
            "Canonical selection remains unchanged."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose supported directional cloak targetability over the full initial STANDARD selector baseline."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD DIRECTIONAL TARGETABILITY =====")
    print("summary:", report["summary"])
    print()
    print("MISMATCH PROJECTION:")
    for row in report["mismatch_projection"]:
        print(row)
    print()
    print("ADVANCED ELIGIBLE CONTROLS:")
    for row in report["advanced_eligible_controls"]:
        print(row)
    if report["conflicts"]:
        print()
        print("CONFLICTS:")
        for row in report["conflicts"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("output:", args.output)
    print("NOTE: population composition gate only; canonical selection remains unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
