import pytest

from planets_lab.rules.proration import prorate_waypoint_distance


def test_matches_documented_60ly_11_of_12_example() -> None:
    result = prorate_waypoint_distance(
        requested_distance=60,
        fuel_available=11,
        fuel_required=12,
    )

    assert result.ratio == pytest.approx(11 / 12)
    assert result.distance == pytest.approx(55.0)


def test_zero_available_fuel_gives_zero_continuous_distance() -> None:
    result = prorate_waypoint_distance(
        requested_distance=81,
        fuel_available=0,
        fuel_required=10,
    )

    assert result.distance == 0


def test_exactly_required_fuel_keeps_full_distance() -> None:
    result = prorate_waypoint_distance(
        requested_distance=37.5,
        fuel_available=8,
        fuel_required=8,
    )

    assert result.ratio == 1
    assert result.distance == pytest.approx(37.5)


def test_rejects_more_available_than_required() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        prorate_waypoint_distance(
            requested_distance=10,
            fuel_available=11,
            fuel_required=10,
        )


def test_rejects_non_positive_required_fuel() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        prorate_waypoint_distance(
            requested_distance=10,
            fuel_available=0,
            fuel_required=0,
        )
