from __future__ import annotations

from planets_lab.corpus.movement_fuel_context import (
    FUEL_PRORATION_CATEGORY,
    strict_fuel_proration_endpoint,
)
from planets_lab.validation.movement_geometry import MovementSample


def _sample(*, observed_x: int = 55, target_x: int = 60, gravitonic: bool = False, hull_id: int = 17) -> MovementSample:
    return MovementSample(
        turn=10,
        ship_id=4,
        x=0,
        y=0,
        target_x=target_x,
        target_y=0,
        warp=9,
        next_x=observed_x,
        next_y=0,
        gravitonic=gravitonic,
        game_id=7,
        hull_id=hull_id,
    )


def test_documented_waypoint_proration_matches_60ly_11_of_12_example() -> None:
    endpoint = strict_fuel_proration_endpoint(
        _sample(),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    )
    assert endpoint == (55, 0)


def test_strict_fuel_proration_requires_exact_host_endpoint() -> None:
    assert strict_fuel_proration_endpoint(
        _sample(observed_x=56),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    ) is None


def test_strict_fuel_proration_rejects_sufficient_fuel() -> None:
    assert strict_fuel_proration_endpoint(
        _sample(observed_x=60),
        fuel_available=12,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    ) is None


def test_strict_fuel_proration_rejects_partial_waypoint_first_pass() -> None:
    assert strict_fuel_proration_endpoint(
        _sample(observed_x=55, target_x=100),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    ) is None


def test_strict_fuel_proration_rejects_damage_limited_requested_warp() -> None:
    assert strict_fuel_proration_endpoint(
        _sample(),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=30,
    ) is None


def test_strict_fuel_proration_rejects_gravitonic_and_horwasp() -> None:
    assert strict_fuel_proration_endpoint(
        _sample(gravitonic=True),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    ) is None
    assert strict_fuel_proration_endpoint(
        _sample(hull_id=205),
        fuel_available=11,
        total_mass=200,
        fuel_factor=8100,
        race_id=1,
        damage=0,
    ) is None


def test_fuel_proration_category_is_stable() -> None:
    assert FUEL_PRORATION_CATEGORY == "fuel_proration_waypoint_match"
