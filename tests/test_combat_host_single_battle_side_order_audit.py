from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_single_battle_side_order_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_single_battle_side_order_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _raw(*, mission: int = 0, enemy: int = 0, fc: str = "abc") -> dict[str, object]:
    return {"mission": mission, "enemy": enemy, "friendlycode": fc}


def test_fc_kind_keeps_only_exact_three_digit_001_999_as_standard_numeric() -> None:
    assert audit._fc_kind("001") == ("strict_numeric", 1)
    assert audit._fc_kind("999") == ("strict_numeric", 999)
    assert audit._fc_kind("000") == ("weird_numeric", None)
    assert audit._fc_kind("1") == ("weird_numeric", None)
    assert audit._fc_kind("12") == ("weird_numeric", None)
    assert audit._fc_kind("abc") == ("symbolic", None)


def test_standard_priority_key_matches_documented_class_order() -> None:
    numeric = audit._priority_key(_raw(fc="123"), 90)
    kill_pe = audit._priority_key(_raw(mission=3, enemy=2), 10)
    kill = audit._priority_key(_raw(mission=3), 10)
    pe = audit._priority_key(_raw(enemy=2), 10)
    neither = audit._priority_key(_raw(), 10)
    assert numeric < kill_pe < kill < pe < neither


def test_lower_ship_id_wins_inside_same_standard_group() -> None:
    assert audit._priority_key(_raw(mission=3, enemy=2), 10) < audit._priority_key(
        _raw(mission=3, enemy=7), 20
    )


def test_kill_or_matching_primary_enemy_can_initiate() -> None:
    assert audit._can_initiate(_raw(mission=3), 8)
    assert audit._can_initiate(_raw(enemy=8), 8)
    assert not audit._can_initiate(_raw(enemy=7), 8)


def test_priority_slice_distinguishes_numeric_and_standard_cases() -> None:
    assert audit._priority_slice(_raw(fc="001"), _raw(fc="999")) == "numeric_vs_numeric"
    assert audit._priority_slice(_raw(fc="001"), _raw(mission=3)) == "numeric_vs_standard"
    assert (
        audit._priority_slice(_raw(mission=3, enemy=2), _raw(mission=3, enemy=7))
        == "standard_same_group"
    )
    assert (
        audit._priority_slice(_raw(mission=3), _raw(enemy=7))
        == "standard_different_groups"
    )


def test_scope_reports_side_priority_and_single_initiator() -> None:
    rows = [
        {
            "game_id": 1,
            "turn": 2,
            "vcr_id": 3,
            "left_ship_id": 20,
            "right_ship_id": 10,
            "left_owner": 1,
            "right_owner": 2,
            "left_raw": _raw(),
            "right_raw": _raw(mission=3),
        }
    ]
    scope = audit._scope(rows, example_limit=5)
    assert scope["comparable"] == 1
    assert scope["side_priority"] == {"right_higher_priority": 1}
    assert scope["initiative"] == {"right_only": 1}
    assert scope["single_initiator_side"] == {"initiator_right": 1}
