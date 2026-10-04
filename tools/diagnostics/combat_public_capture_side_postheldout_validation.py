from __future__ import annotations

from typing import Any

from combat_public_capture_side_postheldout_candidate import (
    predict_postheldout_capture_side,
)


SCHEMA = "planets-lab.combat-public-capture-side-postheldout-validation-adapter.v1"

BRANCH_SECOND_OCCURRENCE = "second_occurrence_reversal"
BRANCH_REACHABLE_NUMERIC = "reachable_numeric_opponent_override"
BRANCH_REACHABLE_STICKY = "reachable_sticky"
BRANCH_NONREACHABLE_FRESH = "nonreachable_neutral_fresh_fc"
BRANCH_UNSUPPORTED_OCCURRENCE = "unsupported_same_pair_occurrence"
BRANCH_REACHABILITY_UNRESOLVED = "identity_anchored_reachability_unresolved"
BRANCH_PRIORITY_UNRESOLVED = "reachable_opponent_priority_unresolved"


def classify_branch(
    *,
    prior_same_pair_occurrences: int,
    identity_anchored_o_pair_reachable: bool | None,
    opponent_priority_group: int | None,
) -> str:
    if isinstance(prior_same_pair_occurrences, bool):
        return BRANCH_UNSUPPORTED_OCCURRENCE
    if prior_same_pair_occurrences == 1:
        return BRANCH_SECOND_OCCURRENCE
    if prior_same_pair_occurrences != 0:
        return BRANCH_UNSUPPORTED_OCCURRENCE

    if identity_anchored_o_pair_reachable is True:
        if (
            isinstance(opponent_priority_group, bool)
            or not isinstance(opponent_priority_group, int)
        ):
            return BRANCH_PRIORITY_UNRESOLVED
        if opponent_priority_group == 0:
            return BRANCH_REACHABLE_NUMERIC
        return BRANCH_REACHABLE_STICKY
    if identity_anchored_o_pair_reachable is False:
        return BRANCH_NONREACHABLE_FRESH
    return BRANCH_REACHABILITY_UNRESOLVED


def evaluate_frozen_postheldout_candidate(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    neutral_fresh_fc_side: Any,
    factual_side: Any,
) -> dict[str, Any]:
    """Evaluate the already-frozen candidate without fitting from validation data.

    The adapter may fail closed when a discriminator required to distinguish
    frozen branches is unknown. It never changes the predictor implementation.
    """

    branch = classify_branch(
        prior_same_pair_occurrences=prior_same_pair_occurrences,
        identity_anchored_o_pair_reachable=identity_anchored_o_pair_reachable,
        opponent_priority_group=opponent_priority_group,
    )
    if branch in {
        BRANCH_UNSUPPORTED_OCCURRENCE,
        BRANCH_REACHABILITY_UNRESOLVED,
        BRANCH_PRIORITY_UNRESOLVED,
    }:
        predicted = None
    else:
        predicted = predict_postheldout_capture_side(
            prior_same_pair_occurrences=prior_same_pair_occurrences,
            next_opponent_previous_side=next_opponent_previous_side,
            identity_anchored_o_pair_reachable=identity_anchored_o_pair_reachable,
            capture_side=capture_side,
            opponent_priority_group=opponent_priority_group,
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
        "inputs": {
            "prior_same_pair_occurrences": prior_same_pair_occurrences,
            "next_opponent_previous_side": next_opponent_previous_side,
            "identity_anchored_o_pair_reachable": (
                identity_anchored_o_pair_reachable
            ),
            "capture_side": capture_side,
            "opponent_priority_group": opponent_priority_group,
            "neutral_fresh_fc_side": neutral_fresh_fc_side,
        },
    }
