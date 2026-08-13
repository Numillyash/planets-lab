import pytest

from planets_lab.rules import movement_fuel_use


def test_movement_fuel_use_applies_documented_truncations() -> None:
    assert movement_fuel_use(
        fuel_factor=10_000,
        total_mass=129,
        distance_traveled=40.9,
        max_distance_per_turn=81,
    ) == 5


def test_movement_fuel_use_handles_full_nominal_turn() -> None:
    assert movement_fuel_use(
        fuel_factor=100,
        total_mass=1000,
        distance_traveled=81,
        max_distance_per_turn=81,
    ) == 1


def test_movement_fuel_use_can_truncate_to_zero() -> None:
    assert movement_fuel_use(
        fuel_factor=100,
        total_mass=99,
        distance_traveled=1,
        max_distance_per_turn=81,
    ) == 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"fuel_factor": -1}, "fuel_factor"),
        ({"total_mass": -1}, "total_mass"),
        ({"distance_traveled": -1}, "distance_traveled"),
        ({"max_distance_per_turn": 0}, "max_distance_per_turn"),
    ],
)
def test_movement_fuel_use_rejects_invalid_inputs(kwargs: dict[str, int], message: str) -> None:
    values = {
        "fuel_factor": 100,
        "total_mass": 100,
        "distance_traveled": 10,
        "max_distance_per_turn": 81,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        movement_fuel_use(**values)
