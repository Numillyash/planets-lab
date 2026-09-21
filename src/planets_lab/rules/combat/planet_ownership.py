"""Pre-combat planet ownership primitives.

This module intentionally starts with the part of cargo-drop semantics that is
directly represented in historical Nu ship orders:

- a directed clan transfer targets one concrete planet;
- Host processes foreign-planet cargo drops in ascending Ship ID order.

Ground-combat casualty math is intentionally not encoded here yet. The
production boundary is therefore an ordered stream of validated clan-drop
orders that an ownership/ground-combat reducer can consume once its kill-ratio
inputs are independently reconstructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PLANET_TRANSFER_TARGET_TYPE = 1


@dataclass(frozen=True)
class PlanetClanDropOrder:
    ship_id: int
    owner_id: int
    planet_id: int
    clans: int


def directed_planet_clan_drop(
    *,
    ship_id: int,
    owner_id: int,
    transfer_clans: int | None,
    transfer_target_id: int | None,
    transfer_target_type: int | None,
) -> PlanetClanDropOrder | None:
    """Return a validated directed planet clan-drop order, or None."""

    for name, value in (("ship_id", ship_id), ("owner_id", owner_id)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    if transfer_clans is None or transfer_clans == 0:
        return None
    if (
        isinstance(transfer_clans, bool)
        or not isinstance(transfer_clans, int)
        or transfer_clans < 0
    ):
        raise ValueError("transfer_clans must be a non-negative integer or None")

    if transfer_target_type != PLANET_TRANSFER_TARGET_TYPE:
        return None
    if (
        isinstance(transfer_target_id, bool)
        or not isinstance(transfer_target_id, int)
        or transfer_target_id <= 0
    ):
        return None

    return PlanetClanDropOrder(
        ship_id=ship_id,
        owner_id=owner_id,
        planet_id=transfer_target_id,
        clans=transfer_clans,
    )


def ordered_planet_clan_drops(
    orders: Iterable[PlanetClanDropOrder],
    *,
    planet_id: int,
) -> tuple[PlanetClanDropOrder, ...]:
    """Return one planet clan-drop stream in Host Ship-ID order."""

    if isinstance(planet_id, bool) or not isinstance(planet_id, int) or planet_id <= 0:
        raise ValueError("planet_id must be a positive integer")

    filtered = [order for order in orders if order.planet_id == planet_id]
    ship_ids = [order.ship_id for order in filtered]
    if len(ship_ids) != len(set(ship_ids)):
        raise ValueError("duplicate clan-drop order for ship")

    return tuple(sorted(filtered, key=lambda order: order.ship_id))
