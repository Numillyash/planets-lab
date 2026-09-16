from __future__ import annotations

from planets_lab.rules.combat.selection import (
    ShipCombatPairPhase,
    ShipCombatPrestandardKind,
    ShipCombatSideInput,
    decide_ship_combat_pair,
)


def _ship(ship_id: int, owner_id: int, **overrides: object) -> ShipCombatSideInput:
    values: dict[str, object] = {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": 1 if owner_id == 1 else 2,
        "hull_id": 20 if owner_id == 1 else 23,
        "mission": 0,
        "mission_target_id": 0,
        "primary_enemy": 0,
        "friendly_code": "abc" if owner_id == 1 else "def",
        "hull_can_cloak": False,
        "has_fuel": True,
        "diplomacy_allows_attack": True,
        "harmonic_weapon_modulation_enabled": False,
        "cloak_and_intercept_enabled": False,
        "cloak_and_intercept_hull_eligible": True,
        "active_cloak_at_intercept": False,
        "intercept_interference_protected": False,
        "galactic_power_enabled": False,
    }
    values.update(overrides)
    return ShipCombatSideInput(**values)


def test_standard_only_aggressor_cannot_attack_non_targetable_opponent() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(40, 1, mission=3, primary_enemy=2),
        right=_ship(10, 2, standard_targetable_by_opponent=False),
        same_location=True,
    )

    assert decision.engagement_eligible is False
    assert decision.phase is None
    assert decision.prestandard_kind is None
    assert decision.unresolved_reasons == ("no_standard_combat_request_after_targetability",)


def test_standard_targetability_is_directional_and_preserves_reciprocal_request() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(40, 1, mission=3, primary_enemy=2),
        right=_ship(
            10,
            2,
            mission=3,
            primary_enemy=1,
            standard_targetable_by_opponent=False,
        ),
        same_location=True,
    )

    # Left -> right is suppressed because right is not targetable. Right -> left
    # remains a valid request, so the pair still reaches ordinary STANDARD combat.
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.prestandard_kind is None
    assert decision.unresolved_reasons == ()


def test_unknown_standard_targetability_fails_closed_for_only_request() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(40, 1, mission=3, primary_enemy=2),
        right=_ship(10, 2, standard_targetable_by_opponent=None),
        same_location=True,
    )

    assert decision.engagement_eligible is None
    assert decision.phase is None
    assert decision.prestandard_kind is None
    assert decision.unresolved_reasons == ("right_standard_targetability_unknown",)


def test_non_targetable_target_does_not_suppress_priority_intercept() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            89,
            1,
            mission=7,
            mission_target_id=80,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        right=_ship(80, 2, standard_targetable_by_opponent=False),
        same_location=True,
    )

    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.PRIORITY_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT
    assert decision.phase_attacker_ship_id == 89


def test_non_targetable_target_does_not_suppress_cloak_and_intercept() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            50,
            1,
            race_id=3,
            mission=20,
            mission_target_id=70,
            primary_enemy=2,
            hull_can_cloak=True,
            cloak_and_intercept_enabled=True,
            cloak_and_intercept_hull_eligible=True,
            active_cloak_at_intercept=True,
        ),
        right=_ship(70, 2, standard_targetable_by_opponent=False),
        same_location=True,
    )

    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.CLOAK_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.CLOAK_AND_INTERCEPT
    assert decision.phase_attacker_ship_id == 50


def test_default_targetability_keeps_existing_standard_behavior() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(40, 1, mission=3, primary_enemy=2),
        right=_ship(10, 2),
        same_location=True,
    )

    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.left_ship_id == 10
    assert decision.right_ship_id == 40
