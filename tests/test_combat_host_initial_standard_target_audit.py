from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_target_audit import (  # noqa: E402
    PlainStandardCandidate,
    _plain_standard_candidate,
    _select_first_low_target_control,
    _select_first_plain_standard,
)


def _candidate(
    pair: tuple[int, int],
    *,
    active: int,
    target: int,
    active_priority: tuple[int, int, int],
    target_priority: tuple[int, int, int],
) -> PlainStandardCandidate:
    return PlainStandardCandidate(
        pair=tuple(sorted(pair)),
        active_ship_id=active,
        target_ship_id=target,
        active_priority=active_priority,
        target_priority=target_priority,
    )


def test_selector_chooses_highest_priority_active_ship_first() -> None:
    lower_active = _candidate(
        (20, 30),
        active=20,
        target=30,
        active_priority=(3, 20, 0),
        target_priority=(4, 30, 0),
    )
    higher_active = _candidate(
        (10, 40),
        active=10,
        target=40,
        active_priority=(0, 200, 10),
        target_priority=(4, 40, 0),
    )
    assert _select_first_plain_standard((lower_active, higher_active)) == higher_active


def test_selector_chooses_highest_priority_target_within_first_active() -> None:
    first_target = _candidate(
        (10, 20),
        active=10,
        target=20,
        active_priority=(0, 100, 10),
        target_priority=(3, 20, 0),
    )
    second_target = _candidate(
        (10, 30),
        active=10,
        target=30,
        active_priority=(0, 100, 10),
        target_priority=(4, 30, 0),
    )
    assert _select_first_plain_standard((second_target, first_target)) == first_target
    assert _select_first_low_target_control((second_target, first_target)) == second_target


def test_plain_standard_candidate_uses_static_higher_priority_as_active() -> None:
    row = {
        "pair": [10, 20],
        "left": {
            "ship_id": 10,
            "mission": 1,
            "enemy": 0,
            "friendlycode": "abc",
        },
        "right": {
            "ship_id": 20,
            "mission": 3,
            "enemy": 0,
            "friendlycode": "200",
        },
        "conditional": {
            "engagement_eligible": True,
            "phase": "standard",
            "left_ship_id": 10,
            "right_ship_id": 20,
        },
    }
    candidate, issue = _plain_standard_candidate(row, profile="conditional")
    assert issue is None
    assert candidate is not None
    assert candidate.active_ship_id == 20
    assert candidate.target_ship_id == 10
    assert candidate.active_priority == (0, 200, 20)


def test_plain_standard_candidate_rejects_prestandard_phase() -> None:
    row = {
        "pair": [10, 20],
        "left": {
            "ship_id": 10,
            "mission": 1,
            "enemy": 0,
            "friendlycode": "abc",
        },
        "right": {
            "ship_id": 20,
            "mission": 7,
            "enemy": 5,
            "friendlycode": "def",
        },
        "conditional": {
            "engagement_eligible": True,
            "phase": "priority_intercept",
            "left_ship_id": 10,
            "right_ship_id": 20,
        },
    }
    candidate, issue = _plain_standard_candidate(row, profile="conditional")
    assert candidate is None
    assert issue == "eligible_nonstandard_phase"


def test_plain_standard_candidate_rejects_side_override() -> None:
    row = {
        "pair": [10, 20],
        "left": {
            "ship_id": 10,
            "mission": 3,
            "enemy": 5,
            "friendlycode": "100",
        },
        "right": {
            "ship_id": 20,
            "mission": 1,
            "enemy": 0,
            "friendlycode": "abc",
        },
        "conditional": {
            "engagement_eligible": True,
            "phase": "standard",
            "left_ship_id": 10,
            "right_ship_id": 20,
        },
    }
    candidate, issue = _plain_standard_candidate(row, profile="conditional")
    assert candidate is None
    assert issue == "nonplain_standard_side_override"


def test_plain_standard_candidate_rejects_unsupported_priority_shape() -> None:
    row = {
        "pair": [10, 20],
        "left": {
            "ship_id": 10,
            "mission": 1,
            "enemy": 0,
            "friendlycode": "000",
        },
        "right": {
            "ship_id": 20,
            "mission": 3,
            "enemy": 0,
            "friendlycode": "abc",
        },
        "conditional": {
            "engagement_eligible": True,
            "phase": "standard",
            "left_ship_id": 20,
            "right_ship_id": 10,
        },
    }
    candidate, issue = _plain_standard_candidate(row, profile="conditional")
    assert candidate is None
    assert issue == "static_priority_unresolved"
