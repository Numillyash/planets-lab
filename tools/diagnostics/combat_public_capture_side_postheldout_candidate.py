from __future__ import annotations

from typing import Any


SCHEMA = "planets-lab.combat-public-capture-side-postheldout-candidate.v1"
STATUS = "POST_HELDOUT_CANDIDATE_NOT_CANONICAL"


def predict_postheldout_capture_side(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    neutral_fresh_fc_side: Any,
) -> str | None:
    """Return the post-heldout capture-side candidate.

    Evidence status: research candidate only.

    This function intentionally lives under tools/diagnostics rather than
    planets_lab.rules because two of its branches were derived after opening the
    former held-out population.

    Branches:

    1. If this is the second occurrence of the same pair, use the already
       verified standard pair-side reversal. The prize takes the opponent's
       previous side.
    2. For an identity-anchored reachable original-order pair, keep the capture
       side except for the currently observed numeric-priority-opponent
       discriminator: priority group 0 places the prize on RIGHT.
    3. If the original-order pair is not reachable, use the neutral captured
       orders + fresh nonmatching symbolic FC side control.

    Any unsupported state fails closed.
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
