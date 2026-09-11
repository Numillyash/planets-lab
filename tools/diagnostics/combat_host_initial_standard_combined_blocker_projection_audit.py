from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat_host_initial_standard_target_audit import run as run_initial_standard_target
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR
from combat_host_privateer_rob_selector_impact_audit import (
    BIRD_RESIDUAL,
    PRIVATEER_RESIDUAL,
    _mismatch_projection,
    run as run_privateer_impact,
)
from combat_host_bird_super_spy_cloak_context_audit import run as run_bird_context


SCHEMA = "planets-lab.combat-host-initial-standard-combined-blocker-projection-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _project_single_rank1_removal(
    *,
    predicted_target: int | None,
    predicted_active: int | None,
    factual_target_rank: int | None,
    factual_right: int | None,
    blocked_target_ship_id: int,
) -> bool:
    """Project one evidence-backed rank-1 target removal.

    This deliberately does not replay a mutable queue.  It is valid only for the
    known initial-target mismatch shape where the factual target is rank 2 for
    the same active ship and the rank-1 target is independently proven
    untargetable.
    """

    return bool(
        predicted_target == blocked_target_ship_id
        and predicted_active is not None
        and predicted_active == factual_right
        and factual_target_rank == 2
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    common = SimpleNamespace(
        archive_dir=args.archive_dir,
        prepared_dir=args.prepared_dir,
        example_limit=100000,
        output=None,
    )
    baseline = run_initial_standard_target(common)
    privateer = run_privateer_impact(common)
    bird = run_bird_context(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            output=None,
        )
    )

    privateer_summary = privateer.get("summary")
    privateer_summary = privateer_summary if isinstance(privateer_summary, Mapping) else {}
    privateer_acceptance = privateer_summary.get("acceptance")
    privateer_acceptance = privateer_acceptance if isinstance(privateer_acceptance, Mapping) else {}

    bird_summary = bird.get("summary")
    bird_summary = bird_summary if isinstance(bird_summary, Mapping) else {}
    bird_supported = (
        bird_summary.get("extra_ship_documented_effective_cloak_supported") is True
        and bird_summary.get("factual_ship_documented_effective_cloak_supported") is False
        and bird_summary.get("raw_prior_cloak_control_separates") is True
        and int(bird_summary.get("race_conflicts") or 0) == 0
    )

    rows: list[dict[str, Any]] = []
    privateer_profiles = 0
    privateer_fixed = 0
    bird_profiles = 0
    bird_fixed = 0
    unrelated_mismatches = 0

    privateer_projection_index: dict[tuple[int, int, str], Mapping[str, Any]] = {}
    for row in privateer.get("mismatch_projection", ()):
        if not isinstance(row, Mapping):
            continue
        key = (int(row["game_id"]), int(row["battle_turn"]), str(row.get("profile") or ""))
        privateer_projection_index[key] = row

    for raw in baseline.get("mismatch_examples", ()):
        if not isinstance(raw, Mapping):
            continue
        game_id = int(raw["game_id"])
        battle_turn = int(raw["battle_turn"])
        profile = str(raw.get("profile") or "")
        predicted_target, predicted_active, factual_target_rank, factual_right = _mismatch_projection(raw)
        residual_key = (game_id, battle_turn, predicted_target)

        privateer_row = privateer_projection_index.get((game_id, battle_turn, profile))
        privateer_projected_fixed = bool(
            residual_key == PRIVATEER_RESIDUAL
            and isinstance(privateer_row, Mapping)
            and privateer_row.get("projected_fixed_by_single_rank1_removal") is True
        )
        bird_projected_fixed = bool(
            residual_key == BIRD_RESIDUAL
            and bird_supported
            and _project_single_rank1_removal(
                predicted_target=predicted_target,
                predicted_active=predicted_active,
                factual_target_rank=factual_target_rank,
                factual_right=factual_right,
                blocked_target_ship_id=BIRD_RESIDUAL[2],
            )
        )

        if residual_key == PRIVATEER_RESIDUAL:
            privateer_profiles += 1
            if privateer_projected_fixed:
                privateer_fixed += 1
        elif residual_key == BIRD_RESIDUAL:
            bird_profiles += 1
            if bird_projected_fixed:
                bird_fixed += 1
        else:
            unrelated_mismatches += 1

        rows.append(
            {
                "game_id": game_id,
                "battle_turn": battle_turn,
                "profile": profile,
                "predicted_target_ship_id": predicted_target,
                "predicted_active_ship_id": predicted_active,
                "factual_target_rank_within_top_active": factual_target_rank,
                "factual_right_ship_id": factual_right,
                "is_privateer_residual": residual_key == PRIVATEER_RESIDUAL,
                "is_bird_residual": residual_key == BIRD_RESIDUAL,
                "privateer_projected_fixed": privateer_projected_fixed,
                "bird_projected_fixed": bird_projected_fixed,
                "combined_projected_fixed": privateer_projected_fixed or bird_projected_fixed,
            }
        )

    acceptance = {
        "privateer_gate_still_clean": all(
            privateer_acceptance.get(key) is True
            for key in (
                "no_blocked_factual_pair",
                "no_potential_first_selector_regression",
                "privateer_residual_all_profiles_projected_fixed",
                "bird_residual_present_and_unaffected",
            )
        ),
        "bird_context_gate_clean": bird_supported,
        "privateer_residual_all_profiles_projected_fixed": (
            privateer_profiles > 0 and privateer_fixed == privateer_profiles
        ),
        "bird_residual_all_profiles_projected_fixed": (
            bird_profiles > 0 and bird_fixed == bird_profiles
        ),
        "no_unrelated_baseline_mismatches": unrelated_mismatches == 0,
    }
    acceptance["all_original_broad_mismatches_projected_fixed"] = bool(
        acceptance["privateer_residual_all_profiles_projected_fixed"]
        and acceptance["bird_residual_all_profiles_projected_fixed"]
        and acceptance["no_unrelated_baseline_mismatches"]
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "baseline_initial_standard": baseline.get("summary"),
            "baseline_mismatch_examples": len(rows),
            "privateer_residual_profiles": privateer_profiles,
            "privateer_residual_profiles_projected_fixed": privateer_fixed,
            "bird_residual_profiles": bird_profiles,
            "bird_residual_profiles_projected_fixed": bird_fixed,
            "unrelated_baseline_mismatches": unrelated_mismatches,
            "privateer_selector_impact": privateer_summary,
            "bird_context": bird_summary,
            "acceptance": acceptance,
        },
        "mismatch_projection": rows[: args.example_limit],
        "evidence_boundary": (
            "Read-only structural composition of two independently accepted initial STANDARD target-blocker gates. "
            "Privateer results are reused from the corpus-wide Rob selector-impact differential; Bird support is reused "
            "from the documented Super Spy dynamic-context gate. The projection removes only an independently supported "
            "rank-1 target when the factual target is rank 2 for the same active ship. It does not replay the full candidate "
            "population, does not modify canonical selection, and is not sufficient by itself to promote a generic cloak "
            "targetability implementation. Its purpose is to prove that the two original broad mismatch profiles compose "
            "without contradiction before the next population-wide directional targetability gate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose accepted Privateer and Bird blockers over the original initial STANDARD mismatch profiles."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD COMBINED BLOCKER PROJECTION =====")
    print(f"summary: {report['summary']}")
    print()
    print("MISMATCH PROJECTION:")
    for row in report["mismatch_projection"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: structural composition gate only; canonical selection remains unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
