from __future__ import annotations

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_postindependent_validation import (
    BRANCH_REACHABLE_NUMERIC_KILL_LEFT,
    BRANCH_REACHABLE_NUMERIC_NONKILL_LEFT,
    evaluate_frozen_postindependent_candidate,
)


def test_postindependent_validation_discriminates_kill_and_nonkill() -> None:
    kill = evaluate_frozen_postindependent_candidate(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="left",
        opponent_priority_group=0,
        opponent_mission=3,
        neutral_fresh_fc_side="right",
        factual_side="left",
    )
    assert kill["branch"] == BRANCH_REACHABLE_NUMERIC_KILL_LEFT
    assert kill["exact"] is True

    nonkill = evaluate_frozen_postindependent_candidate(
        prior_same_pair_occurrences=0,
        next_opponent_previous_side=None,
        identity_anchored_o_pair_reachable=True,
        capture_side="left",
        opponent_priority_group=0,
        opponent_mission=1,
        neutral_fresh_fc_side="left",
        factual_side="right",
    )
    assert nonkill["branch"] == BRANCH_REACHABLE_NUMERIC_NONKILL_LEFT
    assert nonkill["exact"] is True
