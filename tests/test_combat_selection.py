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


def test_pair_is_blocked_when_not_colocated() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(1, 1, mission=3),
        right=_ship(2, 2),
        same_location=False,
    )
    assert decision.engagement_eligible is False
    assert decision.phase is None
    assert "different_location" in decision.unresolved_reasons


def test_pair_is_blocked_when_either_ship_has_zero_fuel() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(1, 1, mission=3, has_fuel=False),
        right=_ship(2, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is False
    assert "left_fuel_absent" in decision.unresolved_reasons


def test_ordinary_exact_matching_fc_blocks_combat() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(1, 1, mission=3, friendly_code="xyz"),
        right=_ship(2, 2, friendly_code="xyz"),
        same_location=True,
    )
    assert decision.matching_fc_blocks is True
    assert decision.engagement_eligible is False
    assert "matching_friendly_code" in decision.unresolved_reasons


def test_documented_mkt_exception_reaches_standard_combat() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(10, 1, mission=3, friendly_code="mkt"),
        right=_ship(20, 2, friendly_code="mkt"),
        same_location=True,
    )
    assert decision.matching_fc_blocks is False
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD


def test_active_bird_hwm_overrides_matching_fc_block_and_reports_effect() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            10,
            1,
            race_id=3,
            mission=3,
            friendly_code="xyz",
            harmonic_weapon_modulation_enabled=True,
        ),
        right=_ship(20, 2, friendly_code="xyz"),
        same_location=True,
    )
    assert decision.matching_fc_blocks is False
    assert decision.left_hwm_applies is True
    assert decision.right_hwm_applies is False
    assert decision.engagement_eligible is True


def test_unknown_bird_hwm_state_fails_closed_for_matching_fc() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            10,
            1,
            race_id=3,
            mission=3,
            friendly_code="xyz",
            harmonic_weapon_modulation_enabled=None,
        ),
        right=_ship(20, 2, friendly_code="xyz"),
        same_location=True,
    )
    assert decision.matching_fc_blocks is None
    assert decision.engagement_eligible is None
    assert "matching_friendly_code_state_unknown" in decision.unresolved_reasons


def test_one_sided_safe_passage_can_block_the_only_aggressor() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            10,
            1,
            primary_enemy=2,
            diplomacy_allows_attack=False,
        ),
        right=_ship(20, 2, diplomacy_allows_attack=True),
        same_location=True,
    )
    assert decision.engagement_eligible is False
    assert "no_combat_request" in decision.unresolved_reasons


def test_known_aggressor_allows_standard_phase_with_unknown_opposite_diplomacy() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            10,
            1,
            mission=3,
            diplomacy_allows_attack=True,
        ),
        right=_ship(
            20,
            2,
            primary_enemy=1,
            diplomacy_allows_attack=None,
        ),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.unresolved_reasons == ()


def test_normal_priority_intercept_is_prestandard_and_attacker_is_right() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            89,
            1,
            mission=7,
            mission_target_id=80,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        right=_ship(80, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.PRIORITY_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT
    assert decision.phase_attacker_ship_id == 89
    assert decision.left_ship_id == 80
    assert decision.right_ship_id == 89


def test_normal_pia_does_not_apply_to_other_ship_of_same_target_owner() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            40,
            1,
            mission=7,
            mission_target_id=15,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        right=_ship(72, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.prestandard_kind is None


def test_intercept_interference_demotes_normal_pia_to_standard() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            89,
            1,
            mission=7,
            mission_target_id=80,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        right=_ship(80, 2, intercept_interference_protected=True),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.prestandard_kind is None


def test_reciprocal_priority_intercept_phase_is_known_but_side_is_not_generalized() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            89,
            1,
            mission=7,
            mission_target_id=80,
            primary_enemy=0,
            hull_can_cloak=True,
        ),
        right=_ship(80, 2, mission=3, primary_enemy=1),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.PRIORITY_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.RECIPROCAL_PRIORITY_INTERCEPT
    assert decision.phase_attacker_ship_id == 89
    assert decision.left_ship_id is None
    assert decision.right_ship_id is None
    assert "reciprocal_priority_intercept_side_unverified" in decision.unresolved_reasons


def test_cloak_and_intercept_requires_effective_advantage_active_cloak_and_hull_eligibility() -> None:
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
        right=_ship(70, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.CLOAK_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.CLOAK_AND_INTERCEPT
    assert decision.phase_attacker_ship_id == 50
    assert decision.right_ship_id == 50


def test_unknown_c_and_i_hull_eligibility_keeps_phase_unresolved() -> None:
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
            cloak_and_intercept_hull_eligible=None,
            active_cloak_at_intercept=True,
        ),
        right=_ship(70, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is None
    assert "cloak_intercept_hull_eligibility_unknown" in decision.unresolved_reasons


def test_ineligible_c_and_i_hull_falls_back_to_standard() -> None:
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
            cloak_and_intercept_hull_eligible=False,
            active_cloak_at_intercept=True,
        ),
        right=_ship(70, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD


def test_unknown_active_cloak_keeps_c_and_i_phase_unresolved() -> None:
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
            active_cloak_at_intercept=None,
        ),
        right=_ship(70, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is None
    assert "cloak_intercept_active_cloak_unknown" in decision.unresolved_reasons


def test_intercept_interference_breaks_c_and_i_prestandard_lock() -> None:
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
            active_cloak_at_intercept=True,
        ),
        right=_ship(70, 2, intercept_interference_protected=True),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD


def test_standard_higher_priority_ship_is_assigned_right() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(40, 1, mission=3, primary_enemy=2),
        right=_ship(10, 2, primary_enemy=1),
        same_location=True,
    )
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.left_ship_id == 10
    assert decision.right_ship_id == 40


def test_galactic_power_forces_empire_gorbie_left_over_standard_priority() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            10,
            1,
            mission=3,
            primary_enemy=2,
            friendly_code="001",
        ),
        right=_ship(
            62,
            2,
            race_id=8,
            hull_id=70,
            primary_enemy=1,
            friendly_code="eqe",
            galactic_power_enabled=True,
        ),
        same_location=True,
    )
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.left_ship_id == 62
    assert decision.right_ship_id == 10


def test_unknown_galactic_power_state_keeps_side_assignment_unresolved() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(10, 1, mission=3, primary_enemy=2),
        right=_ship(
            62,
            2,
            race_id=8,
            hull_id=70,
            primary_enemy=1,
            galactic_power_enabled=None,
        ),
        same_location=True,
    )
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.left_ship_id is None
    assert decision.right_ship_id is None
    assert "galactic_power_state_unknown" in decision.unresolved_reasons


def test_two_normal_pia_attackers_use_documented_reverse_ship_id_order() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(
            20,
            1,
            mission=7,
            mission_target_id=30,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        right=_ship(
            30,
            2,
            mission=7,
            mission_target_id=20,
            primary_enemy=1,
            hull_can_cloak=True,
        ),
        same_location=True,
    )
    assert decision.phase is ShipCombatPairPhase.PRIORITY_INTERCEPT
    assert decision.prestandard_kind is ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT
    assert decision.phase_attacker_ship_id == 30
    assert decision.right_ship_id == 30
    assert decision.left_ship_id == 20


def test_unsupported_standard_numeric_fc_keeps_side_unknown() -> None:
    decision = decide_ship_combat_pair(
        left=_ship(10, 1, mission=3, friendly_code="000"),
        right=_ship(20, 2),
        same_location=True,
    )
    assert decision.engagement_eligible is True
    assert decision.phase is ShipCombatPairPhase.STANDARD
    assert decision.left_ship_id is None
    assert decision.right_ship_id is None
    assert "standard_priority_unsupported_friendly_code" in decision.unresolved_reasons
