from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOL = (
    Path(__file__).parents[1]
    / "tools"
    / "diagnostics"
    / "combat_host_factual_queue_selection_audit.py"
)
spec = importlib.util.spec_from_file_location("combat_host_factual_queue_selection_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def _signature():
    return (((1, 1, 0),), ((1, 1, 0),))


def test_request_direction_is_owner_order_stable() -> None:
    assert audit._request_direction(2, 5) == "low_to_high"
    assert audit._request_direction(5, 2) == "high_to_low"


def test_independent_diplomacy_control_requires_other_one_sided_vcr() -> None:
    rows = [
        {
            "battle_turn": 10,
            "row_id": (10, 1, 20),
            "relation_signature_raw": _signature(),
            "left_request": True,
            "right_request": False,
            "left_owner_id": 2,
            "right_owner_id": 5,
        },
        {
            "battle_turn": 11,
            "row_id": (11, 2, 30),
            "relation_signature_raw": _signature(),
            "left_request": True,
            "right_request": False,
            "left_owner_id": 2,
            "right_owner_id": 5,
        },
    ]
    game_controls, turn_controls = audit._build_independent_diplomacy_controls(rows)

    allowed, same_turn = audit._independent_permission(
        row=rows[0],
        side_name="left",
        game_controls=game_controls,
        turn_controls=turn_controls,
    )
    assert allowed is True
    assert same_turn is False

    no_request, same_turn = audit._independent_permission(
        row=rows[0],
        side_name="right",
        game_controls=game_controls,
        turn_controls=turn_controls,
    )
    assert no_request is False
    assert same_turn is False


def test_independent_diplomacy_does_not_self_validate() -> None:
    row = {
        "battle_turn": 10,
        "row_id": (10, 1, 20),
        "relation_signature_raw": _signature(),
        "left_request": True,
        "right_request": False,
        "left_owner_id": 2,
        "right_owner_id": 5,
    }
    game_controls, turn_controls = audit._build_independent_diplomacy_controls([row])
    allowed, same_turn = audit._independent_permission(
        row=row,
        side_name="left",
        game_controls=game_controls,
        turn_controls=turn_controls,
    )
    assert allowed is None
    assert same_turn is False


def test_two_sided_factual_combat_is_not_used_as_directed_control() -> None:
    row = {
        "battle_turn": 10,
        "row_id": (10, 1, 20),
        "relation_signature_raw": _signature(),
        "left_request": True,
        "right_request": True,
        "left_owner_id": 2,
        "right_owner_id": 5,
    }
    game_controls, turn_controls = audit._build_independent_diplomacy_controls([row])
    assert not game_controls
    assert not turn_controls


def test_interference_absence_is_decisively_false() -> None:
    state = audit._interference_state(
        game_id=621896,
        before_turn=27,
        owner_id=5,
        raw={"x": 10, "y": 20},
        start_stacks={(27, 5, 10, 20): ((62, 70),)},
    )
    assert state is False


def test_interference_source_uses_verified_standard_context() -> None:
    stack = {(27, 5, 10, 20): ((74, 74), (62, 70))}
    assert audit._interference_state(
        game_id=621896,
        before_turn=27,
        owner_id=5,
        raw={"x": 10, "y": 20},
        start_stacks=stack,
    ) is True
    assert audit._interference_state(
        game_id=511506,
        before_turn=27,
        owner_id=5,
        raw={"x": 10, "y": 20},
        start_stacks=stack,
    ) is False
    assert audit._interference_state(
        game_id=999999,
        before_turn=27,
        owner_id=5,
        raw={"x": 10, "y": 20},
        start_stacks=stack,
    ) is None


def test_phase_prefix_detects_known_prestandard_after_standard() -> None:
    rows = [
        {"vcr_id": 1, "conditional": {"phase": "standard"}},
        {"vcr_id": 2, "conditional": {"phase": "priority_intercept"}},
    ]
    summary = audit._phase_prefix_summary(rows, "conditional")
    assert summary["fully_resolved"] is True
    assert summary["known_prefix_violation"] is True


def test_phase_prefix_ignores_unknown_without_claiming_full_resolution() -> None:
    rows = [
        {"vcr_id": 1, "conditional": {"phase": None}},
        {"vcr_id": 2, "conditional": {"phase": "standard"}},
    ]
    summary = audit._phase_prefix_summary(rows, "conditional")
    assert summary["fully_resolved"] is False
    assert summary["known_prefix_violation"] is False


def test_normal_pia_order_uses_first_vcr_per_attacker() -> None:
    rows = [
        {
            "vcr_id": 2,
            "conditional": {
                "prestandard_kind": "normal_priority_intercept",
                "phase_attacker_ship_id": 20,
            },
        },
        {
            "vcr_id": 1,
            "conditional": {
                "prestandard_kind": "normal_priority_intercept",
                "phase_attacker_ship_id": 30,
            },
        },
        {
            "vcr_id": 3,
            "conditional": {
                "prestandard_kind": "normal_priority_intercept",
                "phase_attacker_ship_id": 30,
            },
        },
    ]
    summary = audit._normal_pia_order_summary(rows, "conditional")
    assert summary["comparable"] is True
    assert summary["factual_attacker_order"] == [30, 20]
    assert summary["expected_reverse_ship_id_order"] == [30, 20]
    assert summary["exact"] is True


def test_galactic_power_state_is_only_known_for_verified_empire_gorbie_games() -> None:
    assert audit._galactic_power_state(game_id=621896, race_id=8, hull_id=70) is True
    assert audit._galactic_power_state(game_id=511506, race_id=8, hull_id=70) is False
    assert audit._galactic_power_state(game_id=999999, race_id=8, hull_id=70) is None
    assert audit._galactic_power_state(game_id=999999, race_id=5, hull_id=70) is False
