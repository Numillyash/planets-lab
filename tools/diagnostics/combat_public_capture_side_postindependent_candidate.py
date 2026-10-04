from __future__ import annotations

from typing import Any

from planets_lab.rules.combat.order import KILL_MISSION_ID


SCHEMA = "planets-lab.combat-public-capture-side-postindependent-candidate.v1"
STATUS = "POST_INDEPENDENT_CANDIDATE_NOT_CANONICAL"


def predict_postindependent_capture_side(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    opponent_mission: int | None,
    neutral_fresh_fc_side: Any,
) -> str | None:
    """Return the post-independent capture-side research candidate.

    Evidence status: research candidate only.

    This candidate was derived only after the previously frozen post-heldout
    candidate failed on the independent short32 population. It therefore must
    not be treated as independently validated.

    Bounded branch order:

    1. A second occurrence of the same pair uses the already verified ordinary
       pair-side reversal: the prize takes the opponent's previous side.
    2. For a first-occurrence identity-anchored reachable pair:
       - a prize already on RIGHT stays RIGHT;
       - a prize on LEFT with a non-numeric STANDARD opponent stays LEFT;
       - a prize on LEFT with numeric group-0 priority stays LEFT when the
         opponent has Kill mission;
       - the observed non-Kill numeric branch flips the prize to RIGHT.
       Unknown discriminator state fails closed.
    3. If the original-order pair is not reachable, use neutral captured orders
       plus a fresh nonmatching symbolic FC.

    The Kill-sensitive group-0 split fits the currently open 82 adjacent rows,
    but the independent short32 rows contributed directly to this formulation.
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

        # RIGHT is invariant under both sticky and the observed numeric flip.
        if capture_side == "right":
            return "right"

        if (
            isinstance(opponent_priority_group, bool)
            or not isinstance(opponent_priority_group, int)
        ):
            return None
        if opponent_priority_group != 0:
            return "left"

        if (
            isinstance(opponent_mission, bool)
            or not isinstance(opponent_mission, int)
        ):
            return None
        if opponent_mission == KILL_MISSION_ID:
            return "left"
        return "right"

    if identity_anchored_o_pair_reachable is False:
        return (
            neutral_fresh_fc_side
            if neutral_fresh_fc_side in {"left", "right"}
            else None
        )

    return None
