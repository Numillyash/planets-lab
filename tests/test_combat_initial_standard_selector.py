from __future__ import annotations

from planets_lab.rules.combat.queue import (
    InitialStandardPairInput,
    select_initial_plain_standard,
)
from planets_lab.rules.combat.selection import (
    ShipCombatPairPhase,
    ShipCombatSideInput,
    decide_ship_combat_pair,
)


def _ship(ship_id: int, owner_id: int, **overrides: object) -> ShipCombatSideInput:
    values: dict[str, object] = {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": 1 if owner_id == 1 else 2,
        "hull_id": 20,
        "mission": 0,
        "mission_target_id": 0,
        "primary_enemy": 0,
        "friendly_code": "abc",
        "hull_can_cloak": False,
        "has_fuel": True,
        "diplomacy_allows_attack": True,
        "harmonic_weapon_modulation_enabled": False,
        "cloak_and_intercept_enabled": False,
        "cloak_and_intercept_hull_eligible": True,
        "active_cloak_at_intercept": False,
        "intercept_interference_protected": False,
        "galactic_power_enabled": False,
        "standard_targetable_by_opponent": True,
    }
    values.update(overrides)
    return ShipCombatSideInput(**values)


def _pair(
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
) -> InitialStandardPairInput:
    return InitialStandardPairInput(
        left=left,
        right=right,
        decision=decide_ship_combat_pair(
            left=left,
            right=right,
            same_location=True,
        ),
    )


def test_selector_chooses_highest_priority_active_ship_first() -> None:
    lower_priority_active = _pair(
        _ship(30, 1, mission=3),
        _ship(80, 2),
    )
    higher_priority_active = _pair(
        _ship(20, 3, mission=3),
        _ship(90, 4),
    )

    selected = select_initial_plain_standard(
        [lower_priority_active, higher_priority_active]
    )

    assert selected.engagement_available is True
    assert selected.active_ship_id == 20
    assert selected.target_ship_id == 90
    assert selected.right_ship_id == 20
    assert selected.left_ship_id == 90


def test_selector_chooses_highest_priority_target_for_top_active_ship() -> None:
    active = _ship(20, 1, mission=3)
    lower_priority_target = _pair(active, _ship(80, 2))
    higher_priority_target = _pair(active, _ship(40, 3))

    selected = select_initial_plain_standard(
        [lower_priority_target, higher_priority_target]
    )

    assert selected.engagement_available is True
    assert selected.eligible_pair_count == 2
    assert selected.active_ship_id == 20
    assert selected.target_ship_id == 40


def test_directional_targetability_removes_top_target_and_selects_next() -> None:
    active = _ship(20, 1, mission=3)
    blocked_top_target = _pair(
        active,
        _ship(40, 2, standard_targetable_by_opponent=False),
    )
    eligible_next_target = _pair(active, _ship(80, 3))

    assert blocked_top_target.decision.engagement_eligible is False

    selected = select_initial_plain_standard(
        [blocked_top_target, eligible_next_target]
    )

    assert selected.engagement_available is True
    assert selected.eligible_pair_count == 1
    assert selected.active_ship_id == 20
    assert selected.target_ship_id == 80


def test_reciprocal_request_keeps_pair_after_one_direction_is_suppressed() -> None:
    higher_priority_side = _ship(20, 1, mission=3)
    reciprocal_aggressor = _ship(
        40,
        2,
        mission=3,
        standard_targetable_by_opponent=False,
    )
    pair = _pair(higher_priority_side, reciprocal_aggressor)

    assert pair.decision.engagement_eligible is True
    assert pair.decision.phase is ShipCombatPairPhase.STANDARD

    selected = select_initial_plain_standard([pair])

    assert selected.engagement_available is True
    assert selected.active_ship_id == 20
    assert selected.target_ship_id == 40


def test_unresolved_pair_fails_whole_initial_selection_closed() -> None:
    unresolved = _pair(
        _ship(10, 1, mission=3),
        _ship(30, 2, standard_targetable_by_opponent=None),
    )
    resolved = _pair(
        _ship(20, 3, mission=3),
        _ship(40, 4),
    )

    assert unresolved.decision.engagement_eligible is None

    selected = select_initial_plain_standard([resolved, unresolved])

    assert selected.engagement_available is None
    assert selected.pair is None
    assert any("pair_engagement_unresolved" in reason for reason in selected.unresolved_reasons)


def test_eligible_prestandard_pair_is_not_silently_dropped() -> None:
    pia = _pair(
        _ship(
            89,
            1,
            mission=7,
            mission_target_id=80,
            primary_enemy=2,
            hull_can_cloak=True,
        ),
        _ship(80, 2),
    )
    standard = _pair(
        _ship(20, 3, mission=3),
        _ship(40, 4),
    )

    assert pia.decision.phase is ShipCombatPairPhase.PRIORITY_INTERCEPT

    selected = select_initial_plain_standard([pia, standard])

    assert selected.engagement_available is None
    assert any("eligible_pair_not_plain_standard" in reason for reason in selected.unresolved_reasons)


def test_standard_side_override_is_outside_plain_selector_scope() -> None:
    ordinary = _ship(10, 1, mission=0, primary_enemy=0, friendly_code="abc")
    gorbie = _ship(
        62,
        2,
        race_id=8,
        hull_id=70,
        mission=3,
        primary_enemy=1,
        friendly_code="eqe",
        galactic_power_enabled=True,
    )
    pair = _pair(ordinary, gorbie)

    assert pair.decision.phase is ShipCombatPairPhase.STANDARD
    assert pair.decision.left_ship_id == 62
    assert pair.decision.right_ship_id == 10

    selected = select_initial_plain_standard([pair])

    assert selected.engagement_available is None
    assert any("standard_side_override_or_unresolved" in reason for reason in selected.unresolved_reasons)


def test_all_known_blocked_pairs_return_no_engagement() -> None:
    blocked = _pair(
        _ship(20, 1, mission=3),
        _ship(40, 2, standard_targetable_by_opponent=False),
    )

    selected = select_initial_plain_standard([blocked])

    assert selected.engagement_available is False
    assert selected.eligible_pair_count == 0
    assert selected.pair is None


def test_duplicate_pair_input_fails_closed() -> None:
    pair = _pair(_ship(20, 1, mission=3), _ship(40, 2))

    selected = select_initial_plain_standard([pair, pair])

    assert selected.engagement_available is None
    assert any("duplicate_pair_input" in reason for reason in selected.unresolved_reasons)
