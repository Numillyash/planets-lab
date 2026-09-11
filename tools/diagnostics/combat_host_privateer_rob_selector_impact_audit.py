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

from planets_lab.rules.combat.effective_state import privateer_rob_ordinary_cloak_state

from combat_host_candidate_set_audit import _serialize
from combat_host_initial_standard_target_audit import run as run_initial_standard_target
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR
from combat_host_privateer_rob_effective_cloak_threshold_audit import (
    run as run_threshold,
)


SCHEMA = "planets-lab.combat-host-privateer-rob-selector-impact-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 100
PRIVATEER_RESIDUAL = (360690, 83, 98)
BIRD_RESIDUAL = (511506, 94, 202)


def _impact_classification(
    *,
    effective_cloak: bool | None,
    initial_classification: Any,
    factual_outcome: Any,
) -> str:
    """Classify first-selector consequence of the scoped overlay.

    Only ``effective_cloak=True`` removes a candidate pair.  The classification
    emitted by the queue-aware Rob audit is enough to distinguish rows that can
    affect the factual first pair from rows that cannot.
    """

    if effective_cloak is not True:
        return "no_overlay_block"
    if factual_outcome == "pair_vcr":
        return "blocked_factual_pair_regression"
    if initial_classification == "initial_pair_vcr":
        return "blocked_initial_pair_regression"
    if initial_classification == "initial_skip_target_outranks_factual":
        return "blocked_outranking_skip_candidate_fix"
    if initial_classification == "initial_skip_target_not_above_factual":
        return "blocked_lower_target_no_first_effect"
    if initial_classification == "noninitial_attacker_context":
        return "blocked_noninitial_attacker_no_first_effect"
    if initial_classification == "later_pair_vcr":
        return "blocked_later_pair_first_effect_unresolved"
    if initial_classification == "attacker_no_factual_vcr":
        return "blocked_phantom_attacker_first_effect_unresolved"
    return "blocked_first_effect_unresolved"


def _mismatch_projection(
    row: Mapping[str, Any],
) -> tuple[int | None, int | None, int | None, int | None]:
    analysis = row.get("analysis")
    analysis = analysis if isinstance(analysis, Mapping) else {}
    predicted = analysis.get("predicted_first")
    predicted = predicted if isinstance(predicted, Mapping) else {}
    factual = row.get("factual_first")
    factual = factual if isinstance(factual, Mapping) else {}
    return (
        int(predicted["target_ship_id"]) if predicted.get("target_ship_id") is not None else None,
        int(predicted["active_ship_id"]) if predicted.get("active_ship_id") is not None else None,
        int(analysis["factual_target_rank_within_top_active"])
        if analysis.get("factual_target_rank_within_top_active") is not None
        else None,
        int(factual["right_ship_id"]) if factual.get("right_ship_id") is not None else None,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline = run_initial_standard_target(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )
    threshold = run_threshold(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )

    totals: Counter[str] = Counter()
    impacts: Counter[str] = Counter()
    overlay_rows: list[dict[str, Any]] = []
    blocked_by_key: dict[tuple[int, int, int], dict[str, Any]] = {}

    for raw in threshold.get("rows", ()):
        if not isinstance(raw, Mapping):
            continue
        state = privateer_rob_ordinary_cloak_state(
            race_id=5,
            mission=9,
            hull_can_cloak=True,
            prior_iscloaked=raw.get("prior_iscloaked"),
            fuel=raw.get("fuel"),
            ordinary_cloak_reference_cost=raw.get("reference_cost"),
            advanced_cloak=raw.get("advanced_cloak"),
        )
        impact = _impact_classification(
            effective_cloak=state.effective_cloak,
            initial_classification=raw.get("initial_classification"),
            factual_outcome=raw.get("factual_outcome"),
        )
        totals["overlay_rows"] += 1
        totals[
            "overlay_blocked"
            if state.effective_cloak is True
            else "overlay_eligible"
            if state.effective_cloak is False
            else "overlay_unresolved"
        ] += 1
        impacts[impact] += 1

        projected = dict(raw)
        projected["helper_effective_cloak"] = state.effective_cloak
        projected["helper_reason"] = state.reason
        projected["selector_impact"] = impact
        overlay_rows.append(projected)

        if state.effective_cloak is True:
            key = (
                int(raw["game_id"]),
                int(raw["battle_turn"]),
                int(raw["target_ship_id"]),
            )
            blocked_by_key[key] = projected

    regression_impacts = {
        "blocked_factual_pair_regression",
        "blocked_initial_pair_regression",
        "blocked_later_pair_first_effect_unresolved",
        "blocked_phantom_attacker_first_effect_unresolved",
        "blocked_first_effect_unresolved",
    }
    potential_regressions = sum(impacts[key] for key in regression_impacts)
    totals["potential_first_selector_regression_rows"] = potential_regressions
    totals["blocked_factual_pair_rows"] = impacts["blocked_factual_pair_regression"]
    totals["safe_first_selector_block_rows"] = (
        impacts["blocked_outranking_skip_candidate_fix"]
        + impacts["blocked_lower_target_no_first_effect"]
        + impacts["blocked_noninitial_attacker_no_first_effect"]
    )

    mismatch_rows: list[dict[str, Any]] = []
    privateer_profiles = 0
    privateer_projected_fixed = 0
    bird_profiles = 0
    bird_overlay_affected = 0

    for raw in baseline.get("mismatch_examples", ()):
        if not isinstance(raw, Mapping):
            continue
        game_id = int(raw["game_id"])
        battle_turn = int(raw["battle_turn"])
        predicted_target, predicted_active, factual_target_rank, factual_right = _mismatch_projection(raw)

        target_key = (
            game_id,
            battle_turn,
            int(predicted_target) if predicted_target is not None else -1,
        )
        blocked = blocked_by_key.get(target_key)
        projected_fixed = bool(
            blocked is not None
            and blocked.get("selector_impact") == "blocked_outranking_skip_candidate_fix"
            and factual_target_rank == 2
            and predicted_active == factual_right
        )

        is_privateer = (
            game_id,
            battle_turn,
            predicted_target,
        ) == PRIVATEER_RESIDUAL
        is_bird = (
            game_id,
            battle_turn,
            predicted_target,
        ) == BIRD_RESIDUAL

        if is_privateer:
            privateer_profiles += 1
            if projected_fixed:
                privateer_projected_fixed += 1
        if is_bird:
            bird_profiles += 1
            if blocked is not None:
                bird_overlay_affected += 1

        item = {
            "game_id": game_id,
            "battle_turn": battle_turn,
            "profile": raw.get("profile"),
            "predicted_target_ship_id": predicted_target,
            "predicted_active_ship_id": predicted_active,
            "factual_target_rank_within_top_active": factual_target_rank,
            "factual_right_ship_id": factual_right,
            "overlay_blocks_predicted_target": blocked is not None,
            "projected_fixed_by_single_rank1_removal": projected_fixed,
            "is_privateer_residual": is_privateer,
            "is_bird_residual": is_bird,
        }
        mismatch_rows.append(item)

    totals["baseline_mismatch_examples"] = len(mismatch_rows)
    totals["privateer_residual_profiles"] = privateer_profiles
    totals["privateer_residual_profiles_projected_fixed"] = privateer_projected_fixed
    totals["bird_residual_profiles"] = bird_profiles
    totals["bird_residual_profiles_overlay_affected"] = bird_overlay_affected

    baseline_summary = baseline.get("summary")
    baseline_summary = baseline_summary if isinstance(baseline_summary, Mapping) else {}

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "impact_counts": _serialize(impacts),
            "baseline_initial_standard": baseline_summary,
            "threshold_summary": threshold.get("summary"),
            "acceptance": {
                "no_blocked_factual_pair": impacts["blocked_factual_pair_regression"] == 0,
                "no_potential_first_selector_regression": potential_regressions == 0,
                "privateer_residual_all_profiles_projected_fixed": (
                    privateer_profiles > 0 and privateer_projected_fixed == privateer_profiles
                ),
                "bird_residual_present_and_unaffected": (
                    bird_profiles > 0 and bird_overlay_affected == 0
                ),
            },
        },
        "mismatch_projection": mismatch_rows[: args.example_limit],
        "overlay_rows": overlay_rows[: args.example_limit],
        "evidence_boundary": (
            "Read-only first-selector impact differential for the tested Privateer Rob ordinary-cloak effective-state helper. "
            "The full baseline initial-STANDARD audit is rerun unchanged. The overlay support is independently bounded by all "
            "16 previously reconstructed Privateer Rob plain-STANDARD opportunities. A blocked factual pair or blocked factual "
            "initial pair is a regression. A blocked target that is lower priority than the factual first target cannot change "
            "that first pair; a noninitial attacker cannot change the factual first VCR through this scoped pair. For baseline "
            "mismatch rows, a blocked predicted rank-1 target with factual target rank 2 projects an exact first-target repair. "
            "This is a structural overlay differential, not canonical selector wiring and not a full mutable queue replay."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project the tested Privateer Rob effective-cloak helper onto the full initial STANDARD selector baseline."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB SELECTOR IMPACT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("MISMATCH PROJECTION:")
    for row in report["mismatch_projection"]:
        print(row)
    print()
    print("OVERLAY ROWS:")
    for row in report["overlay_rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: structural first-selector overlay only; selection.py remains unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
