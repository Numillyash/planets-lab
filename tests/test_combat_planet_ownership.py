from __future__ import annotations

import pytest

from planets_lab.rules.combat.planet_ownership import (
    PLANET_TRANSFER_TARGET_TYPE,
    PlanetClanDropOrder,
    directed_planet_clan_drop,
    ordered_planet_clan_drops,
)


def test_directed_planet_clan_drop_accepts_targeted_positive_order() -> None:
    result = directed_planet_clan_drop(
        ship_id=54,
        owner_id=4,
        transfer_clans=87,
        transfer_target_id=192,
        transfer_target_type=PLANET_TRANSFER_TARGET_TYPE,
    )

    assert result == PlanetClanDropOrder(
        ship_id=54, owner_id=4, planet_id=192, clans=87
    )


@pytest.mark.parametrize(
    ("clans", "target_id", "target_type"),
    [
        (0, 192, PLANET_TRANSFER_TARGET_TYPE),
        (None, 192, PLANET_TRANSFER_TARGET_TYPE),
        (10, 0, PLANET_TRANSFER_TARGET_TYPE),
        (10, 192, 0),
    ],
)
def test_directed_planet_clan_drop_ignores_nonorders(
    clans: int | None, target_id: int, target_type: int
) -> None:
    result = directed_planet_clan_drop(
        ship_id=7,
        owner_id=3,
        transfer_clans=clans,
        transfer_target_id=target_id,
        transfer_target_type=target_type,
    )
    assert result is None


def test_ordered_planet_clan_drops_uses_ship_id_order() -> None:
    orders = [
        PlanetClanDropOrder(ship_id=200, owner_id=3, planet_id=10, clans=5),
        PlanetClanDropOrder(ship_id=20, owner_id=4, planet_id=10, clans=7),
        PlanetClanDropOrder(ship_id=5, owner_id=8, planet_id=11, clans=9),
    ]

    result = ordered_planet_clan_drops(orders, planet_id=10)

    assert [row.ship_id for row in result] == [20, 200]


def test_ordered_planet_clan_drops_rejects_duplicate_ship() -> None:
    orders = [
        PlanetClanDropOrder(ship_id=20, owner_id=3, planet_id=10, clans=5),
        PlanetClanDropOrder(ship_id=20, owner_id=3, planet_id=10, clans=7),
    ]

    with pytest.raises(ValueError):
        ordered_planet_clan_drops(orders, planet_id=10)
