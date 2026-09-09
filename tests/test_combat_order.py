from __future__ import annotations

import pytest

from planets_lab.rules.combat.order import (
    BIRD_RACE_ID,
    CLOAK_INTERCEPT_MISSION_ID,
    EVIL_EMPIRE_RACE_ID,
    GORBIE_HULL_ID,
    INTERCEPT_MISSION_ID,
    FriendlyCodePriorityKind,
    classify_battle_friendly_code,
    cloak_intercept_order_signature,
    galactic_power_forces_left,
    orders_request_ship_combat,
    priority_intercept_order_signature,
    priority_intercept_reciprocal_target_signature,
    standard_battle_priority_key,
)


def test_documented_numeric_friendly_code_priority() -> None:
    value = classify_battle_friendly_code("125")
    assert value.kind is FriendlyCodePriorityKind.NUMERIC
    assert value.numeric_value == 125
    assert value.evidence == "documented_001_999"


def test_signed_three_character_friendly_codes_are_numeric() -> None:
    minus = classify_battle_friendly_code("-54")
    plus = classify_battle_friendly_code("+07")
    assert (minus.kind, minus.numeric_value, minus.evidence) == (
        FriendlyCodePriorityKind.NUMERIC,
        -54,
        "corpus_signed_three_character",
    )
    assert (plus.kind, plus.numeric_value) == (FriendlyCodePriorityKind.NUMERIC, 7)


def test_erratic_numeric_shapes_fail_closed() -> None:
    for value in ("000", "1", "12", "1234", "-5", "-123", "+1", "+123"):
        assert classify_battle_friendly_code(value).kind is FriendlyCodePriorityKind.UNSUPPORTED


def test_symbolic_friendly_code_uses_standard_groups() -> None:
    value = classify_battle_friendly_code("mkt")
    assert value.kind is FriendlyCodePriorityKind.SYMBOLIC
    assert value.numeric_value is None


def test_standard_priority_key_matches_documented_group_order() -> None:
    assert standard_battle_priority_key(
        ship_id=500, mission=0, primary_enemy=0, friendly_code="054"
    ) == (0, 54, 500)
    assert standard_battle_priority_key(
        ship_id=500, mission=3, primary_enemy=4, friendly_code="abc"
    ) == (1, 500, 0)
    assert standard_battle_priority_key(
        ship_id=500, mission=3, primary_enemy=0, friendly_code="abc"
    ) == (2, 500, 0)
    assert standard_battle_priority_key(
        ship_id=500, mission=0, primary_enemy=4, friendly_code="abc"
    ) == (3, 500, 0)
    assert standard_battle_priority_key(
        ship_id=500, mission=0, primary_enemy=0, friendly_code="abc"
    ) == (4, 500, 0)


def test_signed_numeric_priority_precedes_documented_positive_numeric() -> None:
    right = standard_battle_priority_key(
        ship_id=108, mission=3, primary_enemy=0, friendly_code="-54"
    )
    left = standard_battle_priority_key(
        ship_id=105, mission=8, primary_enemy=0, friendly_code="125"
    )
    assert right is not None and left is not None
    assert right < left


def test_standard_priority_fails_closed_for_unsupported_numeric_shape() -> None:
    assert standard_battle_priority_key(
        ship_id=1, mission=3, primary_enemy=0, friendly_code="000"
    ) is None


def test_standard_priority_rejects_invalid_ship_id() -> None:
    with pytest.raises(ValueError):
        standard_battle_priority_key(
            ship_id=0, mission=3, primary_enemy=0, friendly_code="abc"
        )


def test_orders_request_ship_combat_is_not_full_eligibility() -> None:
    assert orders_request_ship_combat(mission=3, primary_enemy=0, opponent_owner_id=9)
    assert orders_request_ship_combat(mission=0, primary_enemy=9, opponent_owner_id=9)
    assert not orders_request_ship_combat(mission=0, primary_enemy=8, opponent_owner_id=9)


def test_priority_intercept_signature_requires_documented_order_fields() -> None:
    assert priority_intercept_order_signature(
        mission=INTERCEPT_MISSION_ID,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is True


def test_priority_intercept_signature_does_not_require_current_cloak_state() -> None:
    assert priority_intercept_order_signature(
        mission=7,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    )


def test_priority_intercept_signature_rejects_known_nonqualifying_orders() -> None:
    assert priority_intercept_order_signature(
        mission=7,
        mission_target_id=50,
        primary_enemy=5,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is False
    assert priority_intercept_order_signature(
        mission=7,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=False,
    ) is False
    assert priority_intercept_order_signature(
        mission=7,
        mission_target_id=0,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is False


def test_priority_intercept_signature_fails_closed_when_fact_missing() -> None:
    assert priority_intercept_order_signature(
        mission=7,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=None,
        hull_can_cloak=True,
    ) is None


def test_non_intercept_mission_is_not_priority_intercept() -> None:
    assert priority_intercept_order_signature(
        mission=20,
        mission_target_id=None,
        primary_enemy=None,
        target_owner_id=None,
        hull_can_cloak=None,
    ) is False


def test_reciprocal_priority_intercept_does_not_require_interceptor_pe() -> None:
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=INTERCEPT_MISSION_ID,
        interceptor_target_id=80,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_would_combat_interceptor=True,
    ) is True


def test_reciprocal_priority_intercept_requires_cloakable_targeted_intercept() -> None:
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=INTERCEPT_MISSION_ID,
        interceptor_target_id=80,
        interceptor_hull_can_cloak=False,
        target_ship_id=80,
        target_would_combat_interceptor=True,
    ) is False
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=INTERCEPT_MISSION_ID,
        interceptor_target_id=81,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_would_combat_interceptor=True,
    ) is False
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=0,
        interceptor_target_id=80,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_would_combat_interceptor=True,
    ) is False


def test_reciprocal_priority_intercept_requires_target_hostility() -> None:
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=INTERCEPT_MISSION_ID,
        interceptor_target_id=80,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_would_combat_interceptor=False,
    ) is False


def test_reciprocal_priority_intercept_fails_closed_on_missing_dynamic_fact() -> None:
    assert priority_intercept_reciprocal_target_signature(
        interceptor_mission=INTERCEPT_MISSION_ID,
        interceptor_target_id=80,
        interceptor_hull_can_cloak=True,
        target_ship_id=80,
        target_would_combat_interceptor=None,
    ) is None


def test_cloak_intercept_signature_matches_residual() -> None:
    assert cloak_intercept_order_signature(
        mission=CLOAK_INTERCEPT_MISSION_ID,
        owner_race_id=BIRD_RACE_ID,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is True


def test_cloak_intercept_signature_does_not_require_current_iscloaked_state() -> None:
    assert cloak_intercept_order_signature(
        mission=20,
        owner_race_id=3,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    )


def test_cloak_intercept_signature_fails_when_known_requirement_is_false() -> None:
    assert cloak_intercept_order_signature(
        mission=20,
        owner_race_id=4,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is False
    assert cloak_intercept_order_signature(
        mission=20,
        owner_race_id=3,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=4,
        hull_can_cloak=False,
    ) is False
    assert cloak_intercept_order_signature(
        mission=20,
        owner_race_id=3,
        mission_target_id=50,
        primary_enemy=5,
        target_owner_id=4,
        hull_can_cloak=True,
    ) is False


def test_cloak_intercept_signature_is_unknown_when_required_fact_missing() -> None:
    assert cloak_intercept_order_signature(
        mission=20,
        owner_race_id=3,
        mission_target_id=50,
        primary_enemy=4,
        target_owner_id=None,
        hull_can_cloak=True,
    ) is None


def test_non_cloak_intercept_mission_is_not_c_and_i() -> None:
    assert cloak_intercept_order_signature(
        mission=7,
        owner_race_id=None,
        mission_target_id=None,
        primary_enemy=None,
        target_owner_id=None,
        hull_can_cloak=None,
    ) is False


def test_galactic_power_forces_enabled_evil_empire_gorbie_left() -> None:
    assert galactic_power_forces_left(
        owner_race_id=EVIL_EMPIRE_RACE_ID,
        hull_id=GORBIE_HULL_ID,
        galactic_power_enabled=True,
    ) is True


def test_galactic_power_does_not_apply_to_captured_or_other_hulls() -> None:
    assert galactic_power_forces_left(
        owner_race_id=5,
        hull_id=GORBIE_HULL_ID,
        galactic_power_enabled=True,
    ) is False
    assert galactic_power_forces_left(
        owner_race_id=EVIL_EMPIRE_RACE_ID,
        hull_id=75,
        galactic_power_enabled=True,
    ) is False


def test_galactic_power_respects_known_disabled_advantage() -> None:
    assert galactic_power_forces_left(
        owner_race_id=EVIL_EMPIRE_RACE_ID,
        hull_id=GORBIE_HULL_ID,
        galactic_power_enabled=False,
    ) is False


def test_galactic_power_fails_closed_when_effective_advantage_unknown() -> None:
    assert galactic_power_forces_left(
        owner_race_id=EVIL_EMPIRE_RACE_ID,
        hull_id=GORBIE_HULL_ID,
        galactic_power_enabled=None,
    ) is None
    assert galactic_power_forces_left(
        owner_race_id=None,
        hull_id=GORBIE_HULL_ID,
        galactic_power_enabled=True,
    ) is None
