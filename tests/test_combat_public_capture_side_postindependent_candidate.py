from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_postindependent_candidate import (
    STATUS,
    predict_postindependent_capture_side,
)


def test_postindependent_candidate_status_and_repeated_pair() -> None:
    assert STATUS == "POST_INDEPENDENT_CANDIDATE_NOT_CANONICAL"
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=1,
            next_opponent_previous_side="left",
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            opponent_priority_group=None,
            opponent_mission=None,
            neutral_fresh_fc_side=None,
        )
        == "left"
    )


def test_postindependent_candidate_reachable_numeric_kill_split() -> None:
    # New independent counterexample: numeric opponent + Kill preserves LEFT.
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=0,
            opponent_mission=3,
            neutral_fresh_fc_side="left",
        )
        == "left"
    )

    # Previously observed numeric non-Kill discriminator flips LEFT -> RIGHT.
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=0,
            opponent_mission=1,
            neutral_fresh_fc_side="left",
        )
        == "right"
    )


def test_postindependent_candidate_reachable_sticky_controls() -> None:
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=3,
            opponent_mission=1,
            neutral_fresh_fc_side="right",
        )
        == "left"
    )
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="right",
            opponent_priority_group=0,
            opponent_mission=7,
            neutral_fresh_fc_side="left",
        )
        == "right"
    )


def test_postindependent_candidate_nonreachable_and_fail_closed() -> None:
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            opponent_priority_group=0,
            opponent_mission=1,
            neutral_fresh_fc_side="left",
        )
        == "left"
    )
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=None,
            opponent_mission=1,
            neutral_fresh_fc_side="left",
        )
        is None
    )
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=0,
            opponent_mission=None,
            neutral_fresh_fc_side="left",
        )
        is None
    )
    assert (
        predict_postindependent_capture_side(
            prior_same_pair_occurrences=2,
            next_opponent_previous_side="right",
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=0,
            opponent_mission=3,
            neutral_fresh_fc_side="left",
        )
        is None
    )
