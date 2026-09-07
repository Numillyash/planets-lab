from __future__ import annotations

import pytest

from planets_lab.rules.combat import (
    apply_terminal_state,
    carry_ship_to_next_engagement,
    federation_recover_shields,
    functional_weapon_limit,
    prepare_sequence_ship,
)


def _ship(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "hull_id": 10,
        "damage": 0,
        "shield": 100,
        "crew": 100,
        "torpedoes": 10,
        "fighters": 20,
        "beam_count": 8,
        "launcher_count": 4,
        "bay_count": 6,
        "physical_beam_count": 8,
        "physical_launcher_count": 4,
        "physical_bay_count": 6,
        "federation_crew_bonus": False,
        "lizard_crew_bonus": False,
    }
    base.update(overrides)
    return base


def test_terminal_dynamic_state_carries_exactly() -> None:
    carried = apply_terminal_state(
        _ship(),
        {
            "shield": 61,
            "damage": 23,
            "crew": 77,
            "torpedoes": 3,
            "fighters": 9,
        },
    )
    assert carried["shield"] == 61
    assert carried["damage"] == 23
    assert carried["crew"] == 77
    assert carried["torpedoes"] == 3
    assert carried["fighters"] == 9


def test_damage_limits_functional_weapons_for_ordinary_ship() -> None:
    assert functional_weapon_limit(_ship(damage=29)) == 8
    prepared = prepare_sequence_ship(_ship(damage=29))
    assert prepared["beam_count"] == 8
    assert prepared["launcher_count"] == 4
    assert prepared["bay_count"] == 6

    prepared = prepare_sequence_ship(_ship(damage=63))
    assert prepared["beam_count"] == 4
    assert prepared["launcher_count"] == 4
    assert prepared["bay_count"] == 4


def test_lizard_bonus_extends_functional_weapon_limit() -> None:
    assert functional_weapon_limit(_ship(damage=120, lizard_crew_bonus=True)) == 3
    prepared = prepare_sequence_ship(_ship(damage=120, lizard_crew_bonus=True))
    assert prepared["beam_count"] == 3
    assert prepared["launcher_count"] == 3
    assert prepared["bay_count"] == 3


def test_federation_explicit_bonus_keeps_weapons_and_adds_three_bays() -> None:
    prepared = prepare_sequence_ship(_ship(damage=80, federation_crew_bonus=True))
    assert prepared["beam_count"] == 8
    assert prepared["launcher_count"] == 4
    assert prepared["bay_count"] == 9


def test_federation_shield_recovery_is_explicit_and_damage_capped() -> None:
    recovered, amount = federation_recover_shields(
        _ship(shield=60, damage=10, federation_crew_bonus=True)
    )
    assert recovered["shield"] == 70
    assert amount == 10

    capped, amount = federation_recover_shields(
        _ship(shield=95, damage=20, federation_crew_bonus=True)
    )
    assert capped["shield"] == 80
    assert amount == 0

    unchanged, amount = federation_recover_shields(
        _ship(shield=60, damage=10, federation_crew_bonus=False)
    )
    assert unchanged["shield"] == 60
    assert amount == 0


def test_carry_ship_to_next_engagement_recalculates_effective_weapons() -> None:
    carried = carry_ship_to_next_engagement(
        _ship(),
        {
            "shield": 50,
            "damage": 61,
            "crew": 80,
            "torpedoes": 2,
            "fighters": 7,
            "destroyed": False,
            "captured": False,
        },
    )
    assert carried["shield"] == 50
    assert carried["damage"] == 61
    assert carried["crew"] == 80
    assert carried["torpedoes"] == 2
    assert carried["fighters"] == 7
    assert carried["beam_count"] == 4
    assert carried["launcher_count"] == 4
    assert carried["bay_count"] == 4


def test_defeated_ship_cannot_be_carried_forward() -> None:
    with pytest.raises(ValueError, match="defeated ship"):
        carry_ship_to_next_engagement(
            _ship(),
            {"destroyed": True, "captured": False},
        )


def test_planet_is_rejected_by_ship_sequence_preparation() -> None:
    with pytest.raises(ValueError, match="positive hull_id"):
        prepare_sequence_ship({"hull_id": 0})
