from __future__ import annotations

from typing import Any


SCHEMA = "planets-lab.combat-public-capture-side-postheldout-candidate.v1"
STATUS = "POST_HELDOUT_CANDIDATE_NOT_CANONICAL"

BRANCH_SECOND_OCCURRENCE = "second_occurrence_reversal"
BRANCH_REACHABLE_NUMERIC = "reachable_numeric_opponent_override"
BRANCH_REACHABLE_STICKY = "reachable_sticky"
BRANCH_NONREACHABLE_FRESH = "nonreachable_neutral_fresh_fc"
BRANCH_UNSUPPORTED_OCCURRENCE = "unsupported_same_pair_occurrence"
BRANCH_REACHABILITY_UNRESOLVED = "identity_anchored_reachability_unresolved"
BRANCH_PRIORITY_UNRESOLVED = "reachable_opponent_priority_unresolved"


def predict_postheldout_capture_side(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    neutral_fresh_fc_side: Any,
) -> str | None:
    """Return the frozen post-heldout capture-side candidate.

    Evidence status: research candidate only.

    This function intentionally lives under tools/diagnostics rather than
    planets_lab.rules because two of its branches were derived after opening the
    former held-out population.

    Branches:

    1. If this is the second occurrence of the same pair, use the already
       verified standard pair-side reversal. The prize takes the opponent's
       previous side.
    2. For an identity-anchored reachable original-order pair, keep the capture
       side except for numeric-priority opponent group 0, which places the prize
       on RIGHT.
    3. If the original-order pair is not reachable, use the neutral captured
       orders + fresh nonmatching symbolic FC side control.

    Unknown discriminator inputs fail closed. In particular, a reachable row
    with unknown opponent priority cannot safely take the sticky branch because
    group 0 is the candidate's explicit exception.
    """

    if isinstance(prior_same_pair_occurrences, bool):
        return None
    if prior_same_pair_occurrences == 1:
        return (
            next_opponent_previous_side
            if next_opponent_previous_side in {"left", "right"}
            else None
        )
    if prior_same_pair_occurrences != 0:
        return None

    if identity_anchored_o_pair_reachable is True:
        if capture_side not in {"left", "right"}:
            return None
        if (
            isinstance(opponent_priority_group, bool)
            or not isinstance(opponent_priority_group, int)
        ):
            return None
        if opponent_priority_group == 0:
            return "right"
        return str(capture_side)

    if identity_anchored_o_pair_reachable is False:
        return (
            neutral_fresh_fc_side
            if neutral_fresh_fc_side in {"left", "right"}
            else None
        )

    return None


def classify_postheldout_capture_side_branch(
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


def evaluate_postheldout_capture_side(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    neutral_fresh_fc_side: Any,
    factual_side: Any,
) -> dict[str, Any]:
    branch = classify_postheldout_capture_side_branch(
        prior_same_pair_occurrences=prior_same_pair_occurrences,
        identity_anchored_o_pair_reachable=identity_anchored_o_pair_reachable,
        opponent_priority_group=opponent_priority_group,
    )
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
