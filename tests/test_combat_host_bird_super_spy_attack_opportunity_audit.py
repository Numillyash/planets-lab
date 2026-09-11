from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_super_spy_attack_opportunity_audit import (  # noqa: E402
    _bird_super_spy_target,
)
from combat_host_privateer_rob_effective_cloak_threshold_audit import (  # noqa: E402
    _expected_blocked_from_initial_classification,
)


def test_bird_super_spy_target_requires_bird_mission9_and_cloak_hull() -> None:
    raw = {"mission": 9, "enemy": 0}
    assert _bird_super_spy_target(race_id=3, raw=raw, hull_can_cloak=True) is True
    assert _bird_super_spy_target(race_id=5, raw=raw, hull_can_cloak=True) is False
    assert _bird_super_spy_target(race_id=3, raw={"mission": 2}, hull_can_cloak=True) is False
    assert _bird_super_spy_target(race_id=3, raw=raw, hull_can_cloak=False) is False
    assert _bird_super_spy_target(race_id=3, raw=raw, hull_can_cloak=None) is False


def test_queue_decisive_labels_have_directional_block_expectations() -> None:
    assert _expected_blocked_from_initial_classification("initial_pair_vcr") is False
    assert (
        _expected_blocked_from_initial_classification(
            "initial_skip_target_outranks_factual"
        )
        is True
    )
    assert (
        _expected_blocked_from_initial_classification(
            "initial_skip_target_not_above_factual"
        )
        is None
    )
    assert _expected_blocked_from_initial_classification("later_pair_vcr") is None
