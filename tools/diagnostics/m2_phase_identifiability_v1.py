"""Aggregate-only offline identifiability audit using FIXED synthetic fixtures.

No credential, game ID, HAR, corpus path or external input accepted.
Outputs only model equivalence-class sizes and experiment parameters
constructed from the built-in fake fixture; not a NuHost parity result.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "diagnostics"))

from planetary_order_aware_scenarios_v1 import fixture, specs
from planets_lab.sim.planetary_phase_identifiability import (
    SyntheticCandidateResult, search_synthetic_phase_discrimination,
)


def describe(label: str, chosen: SyntheticCandidateResult | None) -> None:
    if chosen is None:
        print(f"{label}_available: false")
        return
    evaluation = chosen.analysis
    print(f"{label}_available: true")
    print(f"{label}_supported_placements: {evaluation.supported_placements}")
    print(f"{label}_distinct_supported_endstates: {evaluation.distinct_supported_endstates}")
    print(f"{label}_unsupported_placements_not_server_rejections: {evaluation.unsupported_placements}")
    print(f"{label}_equivalence_class_sizes: {[len(c.placements) for c in evaluation.classes]}")
    print(f"{label}_fictional_recipe: {chosen.recipe!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect 3! synthetic M2 phase hypotheses; no historical or private data"
    )
    parser.add_argument(
        "--max-cases", type=int, default=96,
        help="number of fixed synthetic fixtures in 1..96 (default 96)",
    )
    args = parser.parse_args(argv)
    report = search_synthetic_phase_discrimination(
        fixture(), specs(), standard_tech_level_caps={1: 10},
        max_cases=args.max_cases,
    )
    print("===== M2 SYNTHETIC PHASE IDENTIFIABILITY =====")
    print(f"status: {report.status}")
    print(f"candidates_evaluated: {report.candidates_evaluated}")
    print(f"all_six_supported_candidates: {report.all_six_supported_candidates}")
    print(f"all_six_supported_multiple_distinct_endstates: {report.distinguishable_supported_candidates}")
    print(f"candidates_with_unsupported_models: {report.candidates_with_unsupported_models}")
    describe("best_all_supported", report.best_all_supported)
    describe("best_partial", report.best_partial)
    print("nuhost_order_execution_verified: false")
    print("host_phase_order_verified: false")
    print("partial_model_abstention_is_server_rejection: false")
    print("corpus_read: false")
    print("heldout_entity_records_read: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
