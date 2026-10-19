"""No real account/game data: six-way model identifiability regressions."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.sim.planetary_phase_identifiability import (
    PHASE_HYPOTHESES,
    SyntheticCandidate,
    evaluate_six_phase_signatures,
    materialize_synthetic_case,
    search_synthetic_phase_discrimination,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs


def test_exact_six_hypothesis_partition_and_noncausal_flags():
    source = fixture()
    untouched = deepcopy(source)
    case = SyntheticCandidate(4000, 800, 0, "ship_to_planet", 0, 0)
    before, orders = materialize_synthetic_case(source, case)
    outcome = evaluate_six_phase_signatures(
        before, orders, specs(), standard_tech_level_caps={1: 10},
    )
    assert source == untouched
    assert outcome.status == "DESCRIPTIVE_SYNTHETIC_PHASE_IDENTIFIABILITY_NOT_CAUSAL"
    assert len(PHASE_HYPOTHESES) == 6
    assert outcome.supported_placements == 6
    assert outcome.distinct_supported_endstates == 1
    assert len(outcome.classes) == 1
    assert len(outcome.classes[0].placements) == 6
    assert not outcome.uniquely_identifiable_from_successful_endstate
    assert not outcome.nuhost_order_execution_verified
    assert not outcome.independent_phase_order_verified


def test_transfer_funding_boundary_separates_supported_and_abstaining_models():
    before, orders = materialize_synthetic_case(
        fixture(), SyntheticCandidate(2000, 600, 600, "ship_to_planet", 0, 0),
    )
    outcome = evaluate_six_phase_signatures(
        before, orders, specs(), standard_tech_level_caps={1: 10},
    )
    assert 0 < outcome.supported_placements < 6
    assert outcome.unsupported_placements == 6 - outcome.supported_placements
    assert any(x.status.startswith("ABSTAIN_") for x in outcome.classes)
    labels = [
        name for group in outcome.classes for name in group.placements
    ]
    assert len(labels) == len(set(labels)) == 6
    assert not outcome.uniquely_identifiable_from_successful_endstate
    assert not outcome.nuhost_order_execution_verified


def test_missing_tech_order_and_unasserted_cap_abstain_before_search():
    before, orders = materialize_synthetic_case(
        fixture(), SyntheticCandidate(4000, 800, 0, "ship_to_planet", 0, 0),
    )
    missing_cap = evaluate_six_phase_signatures(
        before, orders, specs(), standard_tech_level_caps=None,
    )
    assert missing_cap.status == "ABSTAIN_STANDARD_TECH_CAPS_UNASSERTED"
    assert missing_cap.classes == ()
    from planets_lab.sim.orders import TurnOrders
    absent = evaluate_six_phase_signatures(
        before, TurnOrders.empty(), specs(),
        standard_tech_level_caps={1: 10},
    )
    assert absent.status == "ABSTAIN_NO_EXPLICIT_TECH_ORDER"
    assert absent.classes == ()


def test_bounded_search_is_deterministic_and_never_reveals_source_state():
    base = fixture()
    original = deepcopy(base)
    first = search_synthetic_phase_discrimination(
        base, specs(), standard_tech_level_caps={1: 10},
    )
    second = search_synthetic_phase_discrimination(
        base, specs(), standard_tech_level_caps={1: 10},
    )
    assert first == second
    assert base == original
    assert first.candidates_evaluated == 96
    assert (first.all_six_supported_candidates
            + first.candidates_with_unsupported_models == 96)
    assert first.all_six_supported_candidates > 0
    assert first.candidates_with_unsupported_models > 0
    assert first.best_all_supported is not None
    assert first.best_partial is not None
    assert not first.nuhost_order_execution_verified
    assert not first.observed_host_phase_order_verified
    assert not first.historical_corpus_sampled
    # Neither the repr nor any rendered result includes actual state data,
    # order signatures, player names, game IDs or sensitive hashes.
    result_repr = repr(first)
    assert base.game_id not in result_repr
    assert "sha256" not in result_repr.lower()


@pytest.mark.parametrize("max_cases", [0, -1, 97, True, 1.5])
def test_invalid_search_bounds_rejected(max_cases):
    with pytest.raises(ValueError):
        search_synthetic_phase_discrimination(
            fixture(), specs(), standard_tech_level_caps={1: 10},
            max_cases=max_cases,
        )


def test_prefix_budget_is_respected():
    result = search_synthetic_phase_discrimination(
        fixture(), specs(), standard_tech_level_caps={1: 10}, max_cases=5,
    )
    assert result.candidates_evaluated == 5
