from __future__ import annotations

from typing import Any

from planets_lab.rules.combat.order import KILL_MISSION_ID


SCHEMA = "planets-lab.combat-public-capture-side-postprospective-candidate.v1"
STATUS = "POST_PROSPECTIVE_CANDIDATE_NOT_CANONICAL"


def predict_postprospective_capture_side(
    *,
    prior_same_pair_occurrences: int,
    next_opponent_previous_side: Any,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    opponent_priority_group: int | None,
    opponent_mission: int | None,
) -> str | None:
    """Return the post-prospective capture-side research candidate.

    Evidence status: research candidate only.

    This candidate was derived only after the frozen post-independent candidate
    failed on the fresh public100 prospective population. It therefore must not
    be treated as independently validated.

    Bounded branch order:

    1. A second occurrence of the same pair uses the already verified ordinary
       pair-side reversal: the prize takes the opponent's previous side.
    2. For a first-occurrence identity-anchored O-reachable pair:
       - a prize already on RIGHT stays RIGHT;
       - a prize on LEFT with a non-numeric STANDARD opponent stays LEFT;
       - a prize on LEFT with numeric group-0 priority stays LEFT when the
         opponent has Kill mission;
       - the observed non-Kill numeric branch flips the prize to RIGHT.
    3. If the existing O-order pair is not reachable, the captured ship enters
       the post-capture C-order on the opposite side from its capture VCR.

    The C-order side flip replaces the earlier neutral+fresh-FC proxy. The
    proxy fit every earlier O-not-reachable observation only because all such
    rows had capture_side=RIGHT. The fresh public100 counterexample
    597079/T19/VCR17->18 supplies the first LEFT->RIGHT C-order discriminator.
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

    if capture_side not in {"left", "right"}:
        return None

    if identity_anchored_o_pair_reachable is False:
        return "right" if capture_side == "left" else "left"

    if identity_anchored_o_pair_reachable is not True:
        return None

    if capture_side == "right":
        return "right"

    if (
        isinstance(opponent_priority_group, bool)
        or not isinstance(opponent_priority_group, int)
    ):
        return None
    if opponent_priority_group != 0:
        return "left"

    if isinstance(opponent_mission, bool) or not isinstance(opponent_mission, int):
        return None
    if opponent_mission == KILL_MISSION_ID:
        return "left"
    return "right"
