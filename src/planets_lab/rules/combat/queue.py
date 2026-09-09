from __future__ import annotations


STANDARD_PAIR_MAX_OCCURRENCES = 2


def standard_pair_sides_for_occurrence(
    *,
    first_pass_left_ship_id: int,
    first_pass_right_ship_id: int,
    occurrence_index: int,
) -> tuple[int, int] | None:
    """Return queue-aware sides for an ordinary repeated standard pair.

    This helper does **not** decide whether a pair fights again. It only projects
    LEFT/RIGHT after a mutable queue has already selected the first or second
    occurrence of the same ordinary standard ship pair within one
    battle-turn/location.

    Evidence boundary:

    - occurrence 1 keeps the already resolved first-pass sides;
    - occurrence 2 reverses those sides;
    - later occurrences fail closed because the documented Host boundary is at
      most two combats per ship pair and the current ordinary corpus contains no
      third occurrence;
    - the exact second-pass reversal is corpus-observed and differentially
      verified only for the conservative plain-standard repeated-pair scope. It
      is intentionally not folded into the static battle-priority key.
    """

    for name, value in (
        ("first_pass_left_ship_id", first_pass_left_ship_id),
        ("first_pass_right_ship_id", first_pass_right_ship_id),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if first_pass_left_ship_id == first_pass_right_ship_id:
        raise ValueError("first-pass ship ids must be distinct")
    if (
        isinstance(occurrence_index, bool)
        or not isinstance(occurrence_index, int)
        or occurrence_index <= 0
    ):
        raise ValueError("occurrence_index must be a positive integer")

    if occurrence_index == 1:
        return first_pass_left_ship_id, first_pass_right_ship_id
    if occurrence_index == 2:
        return first_pass_right_ship_id, first_pass_left_ship_id
    return None
