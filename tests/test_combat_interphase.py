from __future__ import annotations

import pytest

from planets_lab.rules.combat.interphase import repair_ship_with_supplies


def _ship(*, damage: int, supplies: int) -> dict[str, int | bool]:
    return {
        "hull_id": 20,
        "damage": damage,
        "supplies": supplies,
        "shield": 0,
        "crew": 100,
        "torpedoes": 7,
        "fighters": 0,
        "physical_beam_count": 6,
        "physical_launcher_count": 4,
        "physical_bay_count": 0,
        "beam_count": 6,
        "launcher_count": 4,
        "bay_count": 0,
        "federation_crew_bonus": False,
        "lizard_crew_bonus": False,
    }


@pytest.mark.parametrize(
    ("damage", "supplies", "expected_damage", "expected_supplies", "repaired"),
    [
        (88, 155, 57, 0, 31),
        (12, 45, 3, 0, 9),
        (82, 100, 62, 0, 20),
        (51, 58, 40, 3, 11),
        (2, 100, 0, 90, 2),
        (54, 41, 46, 1, 8),
        (60, 16, 57, 1, 3),
        (24, 36, 17, 1, 7),
    ],
)
def test_supply_repair_matches_interphase_runtime_examples(
    damage: int,
    supplies: int,
    expected_damage: int,
    expected_supplies: int,
    repaired: int,
) -> None:
    result, amount = repair_ship_with_supplies(
        _ship(damage=damage, supplies=supplies)
    )

    assert amount == repaired
    assert result["damage"] == expected_damage
    assert result["supplies"] == expected_supplies
    assert result["shield"] == 0
    assert result["crew"] == 100
    assert result["torpedoes"] == 7


def test_supply_repair_restores_damage_limited_weapon_slots() -> None:
    result, amount = repair_ship_with_supplies(
        _ship(damage=60, supplies=100)
    )

    assert amount == 20
    assert result["damage"] == 40
    assert result["beam_count"] == 6
    assert result["launcher_count"] == 4


def test_supply_repair_with_less_than_five_supplies_changes_nothing() -> None:
    result, amount = repair_ship_with_supplies(
        _ship(damage=25, supplies=4)
    )

    assert amount == 0
    assert result["damage"] == 25
    assert result["supplies"] == 4


@pytest.mark.parametrize(
    "field,value",
    [("damage", -1), ("supplies", -1), ("damage", True), ("supplies", False)],
)
def test_supply_repair_rejects_invalid_state(field: str, value: object) -> None:
    raw = _ship(damage=10, supplies=10)
    raw[field] = value  # type: ignore[assignment]

    with pytest.raises(ValueError):
        repair_ship_with_supplies(raw)
