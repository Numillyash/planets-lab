from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_effective_cloak_threshold_audit import (  # noqa: E402
    _candidate_effective_cloak,
    _expected_blocked_from_initial_classification,
)


def test_candidate_effective_cloak_prior_false_is_eligible() -> None:
    state, reason = _candidate_effective_cloak(
        prior_iscloaked=False,
        fuel=100,
        reference_cost=5,
        advanced_cloak=False,
    )
    assert state is False
    assert reason == "prior_false"


def test_candidate_effective_cloak_requires_strictly_more_than_reference_cost() -> None:
    below, _ = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=4,
        reference_cost=5,
        advanced_cloak=False,
    )
    equal, _ = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=5,
        reference_cost=5,
        advanced_cloak=False,
    )
    above, _ = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=6,
        reference_cost=5,
        advanced_cloak=False,
    )
    assert below is False
    assert equal is False
    assert above is True


def test_candidate_effective_cloak_advanced_cloak_fails_closed() -> None:
    state, reason = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=100,
        reference_cost=5,
        advanced_cloak=True,
    )
    assert state is None
    assert reason == "advanced_cloak_unresolved"


def test_candidate_effective_cloak_unresolved_inputs_fail_closed() -> None:
    unknown_prior, _ = _candidate_effective_cloak(
        prior_iscloaked=None,
        fuel=10,
        reference_cost=5,
        advanced_cloak=False,
    )
    missing_fuel, _ = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=None,
        reference_cost=5,
        advanced_cloak=False,
    )
    missing_cost, _ = _candidate_effective_cloak(
        prior_iscloaked=True,
        fuel=10,
        reference_cost=None,
        advanced_cloak=False,
    )
    assert unknown_prior is None
    assert missing_fuel is None
    assert missing_cost is None


def test_expected_blocked_uses_only_queue_decisive_initial_shapes() -> None:
    assert _expected_blocked_from_initial_classification("initial_skip_target_outranks_factual") is True
    assert _expected_blocked_from_initial_classification("initial_pair_vcr") is False
    assert _expected_blocked_from_initial_classification("initial_skip_target_not_above_factual") is None
    assert _expected_blocked_from_initial_classification("later_pair_vcr") is None
    assert _expected_blocked_from_initial_classification("noninitial_attacker_context") is None
