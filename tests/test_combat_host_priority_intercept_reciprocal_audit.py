from __future__ import annotations

from tools.diagnostics.combat_host_priority_intercept_reciprocal_audit import (
    _qualifies_reciprocal_only,
    _safe_side,
    _site_position,
    _target_aggression_shape,
)


def _ship(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "mission": 7,
        "mission1target": 80,
        "enemy": 0,
        "friendlycode": "abc",
        "neutronium": 20,
        "damage": 0,
        "iscloaked": False,
    }
    row.update(overrides)
    return row


def test_reciprocal_only_selector_matches_case1_shape() -> None:
    interceptor = _ship()
    target = _ship(mission=3, mission1target=0, enemy=5, friendlycode="027")
    assert _qualifies_reciprocal_only(
        interceptor_raw=interceptor,
        interceptor_owner_id=5,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_owner_id=6,
        target_raw=target,
    )


def test_reciprocal_only_selector_excludes_normal_pia() -> None:
    interceptor = _ship(enemy=6)
    target = _ship(mission=3, mission1target=0, enemy=5, friendlycode="027")
    assert not _qualifies_reciprocal_only(
        interceptor_raw=interceptor,
        interceptor_owner_id=5,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_owner_id=6,
        target_raw=target,
    )


def test_target_aggression_shape_distinguishes_kill_and_pe() -> None:
    assert _target_aggression_shape(
        target_raw={"mission": 3, "enemy": 5}, interceptor_owner_id=5
    ) == "kill_and_pe"
    assert _target_aggression_shape(
        target_raw={"mission": 3, "enemy": 0}, interceptor_owner_id=5
    ) == "kill_only"
    assert _target_aggression_shape(
        target_raw={"mission": 1, "enemy": 5}, interceptor_owner_id=5
    ) == "pe_only"


def test_site_position_is_one_based_and_marks_first() -> None:
    assert _site_position([13, 17, 15], 13) == {
        "site_ship_vcr_ids": [13, 15, 17],
        "site_ship_vcr_count": 3,
        "site_ship_vcr_index": 1,
        "site_first_ship_vcr": True,
        "site_prior_ship_vcr_count": 0,
    }


def test_safe_side_is_privacy_allowlisted() -> None:
    raw = _ship(name="PRIVATE", note="PRIVATE", messages=["PRIVATE"])
    row = _safe_side(
        ship_id=89,
        owner_id=5,
        race_id=5,
        hull_id=46,
        hull_can_cloak=True,
        raw=raw,
    )
    text = repr(row)
    assert "PRIVATE" not in text
    assert row["ship_id"] == 89
    assert row["friendly_code"]["text"] == "abc"
