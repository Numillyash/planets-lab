from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_postheldout_candidate import (
    BRANCH_NONREACHABLE_FRESH,
    BRANCH_PRIORITY_UNRESOLVED,
    BRANCH_REACHABLE_NUMERIC,
    BRANCH_REACHABLE_STICKY,
    BRANCH_SECOND_OCCURRENCE,
    STATUS,
    evaluate_postheldout_capture_side,
    predict_postheldout_capture_side,
)


def test_postheldout_candidate_branches() -> None:
    assert STATUS == "POST_HELDOUT_CANDIDATE_NOT_CANONICAL"

    # Repeated same-pair capture: canonical second-occurrence reversal.
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=1,
            next_opponent_previous_side="left",
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            opponent_priority_group=None,
            neutral_fresh_fc_side=None,
        )
        == "left"
    )

    # Reachable ordinary continuation remains sticky.
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=3,
            neutral_fresh_fc_side="right",
        )
        == "left"
    )

    # The single currently observed numeric-priority discriminator.
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=0,
            neutral_fresh_fc_side="left",
        )
        == "right"
    )

    # Non-reachable original order uses neutral/fresh-FC side control.
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            opponent_priority_group=4,
            neutral_fresh_fc_side="left",
        )
        == "left"
    )


def test_postheldout_candidate_fails_closed() -> None:
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=2,
            next_opponent_previous_side="left",
            identity_anchored_o_pair_reachable=True,
            capture_side="right",
            opponent_priority_group=0,
            neutral_fresh_fc_side="left",
        )
        is None
    )
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=1,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            opponent_priority_group=None,
            neutral_fresh_fc_side="left",
        )
        is None
    )



def test_postheldout_candidate_reachable_unknown_priority_fails_closed() -> None:
    assert (
        predict_postheldout_capture_side(
            prior_same_pair_occurrences=0,
            next_opponent_previous_side=None,
            identity_anchored_o_pair_reachable=True,
            capture_side="left",
            opponent_priority_group=None,
            neutral_fresh_fc_side="right",
        )
        is None
    )

    result = evaluate_postheldout_capture_side(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="left",
        opponent_priority_group=None,
        neutral_fresh_fc_side="right",
        factual_side="left",
    )
    assert result["status"] == "unresolved"
    assert result["branch"] == BRANCH_PRIORITY_UNRESOLVED
    assert result["exact"] is None


def test_postheldout_candidate_evaluator_classifies_frozen_branches() -> None:
    repeated = evaluate_postheldout_capture_side(
        prior_same_pair_occurrences=1,
        next_opponent_previous_side="left",
        identity_anchored_o_pair_reachable=None,
        capture_side="right",
        opponent_priority_group=None,
        neutral_fresh_fc_side=None,
        factual_side="left",
    )
    assert repeated["branch"] == BRANCH_SECOND_OCCURRENCE
    assert repeated["exact"] is True

    numeric = evaluate_postheldout_capture_side(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="left",
        opponent_priority_group=0,
        neutral_fresh_fc_side="left",
        factual_side="right",
    )
    assert numeric["branch"] == BRANCH_REACHABLE_NUMERIC
    assert numeric["exact"] is True

    sticky = evaluate_postheldout_capture_side(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="right",
        opponent_priority_group=3,
        neutral_fresh_fc_side="left",
        factual_side="right",
    )
    assert sticky["branch"] == BRANCH_REACHABLE_STICKY
    assert sticky["exact"] is True

    nonreachable = evaluate_postheldout_capture_side(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=False,
        capture_side="right",
        opponent_priority_group=4,
        neutral_fresh_fc_side="left",
        factual_side="left",
    )
    assert nonreachable["branch"] == BRANCH_NONREACHABLE_FRESH
    assert nonreachable["exact"] is True
