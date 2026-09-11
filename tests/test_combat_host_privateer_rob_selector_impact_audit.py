import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_selector_impact_audit import _impact_classification  # noqa: E402


def test_effectively_cloaked_outranking_skip_is_candidate_fix() -> None:
    assert _impact_classification(
        effective_cloak=True,
        initial_classification="initial_skip_target_outranks_factual",
        factual_outcome="attacker_fought_other",
    ) == "blocked_outranking_skip_candidate_fix"


def test_effectively_cloaked_lower_target_has_no_first_effect() -> None:
    assert _impact_classification(
        effective_cloak=True,
        initial_classification="initial_skip_target_not_above_factual",
        factual_outcome="attacker_fought_other",
    ) == "blocked_lower_target_no_first_effect"


def test_blocking_factual_pair_is_regression() -> None:
    assert _impact_classification(
        effective_cloak=True,
        initial_classification="initial_pair_vcr",
        factual_outcome="pair_vcr",
    ) == "blocked_factual_pair_regression"


def test_nonblocked_state_has_no_overlay_effect() -> None:
    assert _impact_classification(
        effective_cloak=False,
        initial_classification="initial_pair_vcr",
        factual_outcome="pair_vcr",
    ) == "no_overlay_block"


def test_unresolved_state_does_not_block() -> None:
    assert _impact_classification(
        effective_cloak=None,
        initial_classification="initial_skip_target_outranks_factual",
        factual_outcome="attacker_fought_other",
    ) == "no_overlay_block"
