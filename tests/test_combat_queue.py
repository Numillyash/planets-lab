from __future__ import annotations

import pytest

from planets_lab.rules.combat.queue import (
    STANDARD_PAIR_MAX_OCCURRENCES,
    standard_pair_sides_for_occurrence,
)


def test_standard_pair_first_occurrence_keeps_resolved_sides() -> None:
    assert standard_pair_sides_for_occurrence(
        first_pass_left_ship_id=14,
        first_pass_right_ship_id=13,
        occurrence_index=1,
    ) == (14, 13)


def test_standard_pair_second_occurrence_reverses_resolved_sides() -> None:
    assert standard_pair_sides_for_occurrence(
        first_pass_left_ship_id=14,
        first_pass_right_ship_id=13,
        occurrence_index=2,
    ) == (13, 14)
    assert standard_pair_sides_for_occurrence(
        first_pass_left_ship_id=67,
        first_pass_right_ship_id=34,
        occurrence_index=2,
    ) == (34, 67)


def test_standard_pair_later_occurrence_fails_closed() -> None:
    assert STANDARD_PAIR_MAX_OCCURRENCES == 2
    assert standard_pair_sides_for_occurrence(
        first_pass_left_ship_id=14,
        first_pass_right_ship_id=13,
        occurrence_index=3,
    ) is None


@pytest.mark.parametrize(
    ("left_ship_id", "right_ship_id", "occurrence_index"),
    [
        (0, 2, 1),
        (1, 0, 1),
        (True, 2, 1),
        (1, False, 1),
        (1, 1, 1),
        (1, 2, 0),
        (1, 2, True),
    ],
)
def test_standard_pair_side_primitive_rejects_invalid_inputs(
    left_ship_id: int,
    right_ship_id: int,
    occurrence_index: int,
) -> None:
    with pytest.raises(ValueError):
        standard_pair_sides_for_occurrence(
            first_pass_left_ship_id=left_ship_id,
            first_pass_right_ship_id=right_ship_id,
            occurrence_index=occurrence_index,
        )
