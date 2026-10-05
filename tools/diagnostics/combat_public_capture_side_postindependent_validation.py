from __future__ import annotations

from typing import Any

from combat_public_capture_side_postindependent_candidate import (
    predict_postindependent_capture_side,
)
from planets_lab.rules.combat.order import KILL_MISSION_ID


SCHEMA = "planets-lab.combat-public-capture-side-postindependent-validation.v1"

BRANCH_SECOND_OCCURRENCE = "second_occurrence_reversal"
BRANCH_REACHABLE_NUMERIC_KILL_LEFT = "reachable_numeric_kill_left"
BRANCH_REACHABLE_NUMERIC_NONKILL_LEFT = "reachable_numeric_nonkill_left"
BRANCH_REACHABLE_STICKY = "reachable_sticky"
BRANCH_NONREACHABLE_FRESH = "nonreachable_neutral_fresh_fc"
BRANCH_UNSUPPORTED_OCCURRENCE = "unsupported_same_pair_occurrence"
BRANCH_REACHABILITY_UNRESOLVED = "identity_anchored_reachability_unresolved"
BRANCH_PRIORITY_UNRESOLVED = "reachable_opponent_priority_unresolved"
BRANCH_MISSION_UNRESOLVED = "reachable_numeric_opponent_mission_unresolved"


def classify_branch(
    *,
    prior_same_pair_occurrences: int,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    opponent_mission: int | None,
) -> str:
    if isinstance(prior_same_pair_occurrences, bool):
        return BRANCH_UNSUPPORTED_OCCURRENCE
    if prior_same_pair_occurrences == 1:
        return BRANCH_SECOND_OCCURRENCE
    if prior_same_pair_occurrences != 0:
        return BRANCH_UNSUPPORTED_OCCURRENCE

    if identity_anchored_o_pair_reachable is False:
        return BRANCH_NONREACHABLE_FRESH
    if identity_anchored_o_pair_reachable is not True:
        return BRANCH_REACHABILITY_UNRESOLVED

    if capture_side not in {"left", "right"}:
        return BRANCH_REACHABILITY_UNRESOLVED
    if capture_side == "right":
        return BRANCH_REACHABLE_STICKY

    if (
        isinstance(opponent_priority_group, bool)
        or not isinstance(opponent_priority_group, int)
    ):
        return BRANCH_PRIORITY_UNRESOLVED
    if opponent_priority_group != 0:
        return BRANCH_REACHABLE_STICKY

    if isinstance(opponent_mission, bool) or not isinstance(opponent_mission, int):
        return BRANCH_MISSION_UNRESOLVED
    if opponent_mission == KILL_MISSION_ID:
        return BRANCH_REACHABLE_NUMERIC_KILL_LEFT
    return BRANCH_REACHABLE_NUMERIC_NONKILL_LEFT


def evaluate_frozen_postindependent_candidate(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    opponent_mission: int | None,
    neutral_fresh_fc_side: Any,
    factual_side: Any,
) -> dict[str, Any]:
    branch = classify_branch(
        prior_same_pair_occurrences=prior_same_pair_occurrences,
        identity_anchored_o_pair_reachable=identity_anchored_o_pair_reachable,
        capture_side=capture_side,
        opponent_priority_group=opponent_priority_group,
        opponent_mission=opponent_mission,
    )
    unresolved = {
        BRANCH_UNSUPPORTED_OCCURRENCE,
        BRANCH_REACHABILITY_UNRESOLVED,
        BRANCH_PRIORITY_UNRESOLVED,
        BRANCH_MISSION_UNRESOLVED,
    }
    if branch in unresolved:
        predicted = None
    else:
        predicted = predict_postindependent_capture_side(
            prior_same_pair_occurrences=prior_same_pair_occurrences,
            next_opponent_previous_side=next_opponent_previous_side,
            identity_anchored_o_pair_reachable=identity_anchored_o_pair_reachable,
            capture_side=capture_side,
            opponent_priority_group=opponent_priority_group,
            opponent_mission=opponent_mission,
            neutral_fresh_fc_side=neutral_fresh_fc_side,
        )

    exact = (
        predicted == factual_side
        if predicted in {"left", "right"} and factual_side in {"left", "right"}
        else None
    )
    return {
        "schema": SCHEMA,
        "status": "resolved" if exact is not None else "unresolved",
        "branch": branch,
        "predicted_side": predicted,
        "factual_side": factual_side,
        "exact": exact,
    }
