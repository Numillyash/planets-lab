from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_postheldout_validation import (
    BRANCH_NONREACHABLE_FRESH,
    BRANCH_PRIORITY_UNRESOLVED,
    BRANCH_REACHABLE_NUMERIC,
    BRANCH_REACHABLE_STICKY,
    BRANCH_SECOND_OCCURRENCE,
    evaluate_frozen_postheldout_candidate,
)


def test_validation_adapter_classifies_all_frozen_branches() -> None:
    repeated = evaluate_frozen_postheldout_candidate(
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

    numeric = evaluate_frozen_postheldout_candidate(
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

    sticky = evaluate_frozen_postheldout_candidate(
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

    nonreachable = evaluate_frozen_postheldout_candidate(
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


def test_validation_adapter_fails_closed_on_unknown_reachable_priority() -> None:
    result = evaluate_frozen_postheldout_candidate(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="left",
        opponent_priority_group=None,
        neutral_fresh_fc_side="right",
        factual_side="left",
    )
    assert result["branch"] == BRANCH_PRIORITY_UNRESOLVED
    assert result["status"] == "unresolved"
    assert result["predicted_side"] is None
    assert result["exact"] is None
