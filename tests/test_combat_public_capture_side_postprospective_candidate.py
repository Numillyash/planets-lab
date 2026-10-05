from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_postprospective_candidate import (
    STATUS,
    predict_postprospective_capture_side,
)


def predict(**kwargs):
    defaults = {
        "prior_same_pair_occurrences": 0,
        "next_opponent_previous_side": None,
        "identity_anchored_o_pair_reachable": True,
        "capture_side": "left",
        "opponent_priority_group": 3,
        "opponent_mission": 1,
    }
    defaults.update(kwargs)
    return predict_postprospective_capture_side(**defaults)


def test_status_is_explicitly_noncanonical() -> None:
    assert STATUS == "POST_PROSPECTIVE_CANDIDATE_NOT_CANONICAL"


def test_c_order_flips_capture_side_both_directions() -> None:
    assert predict(
        identity_anchored_o_pair_reachable=False,
        capture_side="right",
    ) == "left"
    assert predict(
        identity_anchored_o_pair_reachable=False,
        capture_side="left",
    ) == "right"


def test_o_reachable_numeric_kill_split_is_preserved() -> None:
    assert predict(
        capture_side="left",
        opponent_priority_group=0,
        opponent_mission=3,
    ) == "left"
    assert predict(
        capture_side="left",
        opponent_priority_group=0,
        opponent_mission=1,
    ) == "right"


def test_o_reachable_sticky_controls() -> None:
    assert predict(capture_side="right", opponent_priority_group=0) == "right"
    assert predict(capture_side="left", opponent_priority_group=2) == "left"


def test_second_occurrence_reversal_precedes_o_c_split() -> None:
    assert predict(
        prior_same_pair_occurrences=1,
        next_opponent_previous_side="right",
        identity_anchored_o_pair_reachable=False,
        capture_side="right",
    ) == "right"


def test_unknown_dependencies_fail_closed() -> None:
    assert predict(identity_anchored_o_pair_reachable=None) is None
    assert predict(opponent_priority_group=None) is None
    assert predict(opponent_priority_group=0, opponent_mission=None) is None
    assert predict(prior_same_pair_occurrences=2) is None
