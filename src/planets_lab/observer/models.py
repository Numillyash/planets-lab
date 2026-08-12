from __future__ import annotations

from dataclasses import dataclass, field

from planets_lab.core.models import Planet, Ship, Starbase


@dataclass(slots=True, frozen=True)
class ShipContact:
    """A confirmed enemy ship contact visible to the player.

    The observer layer deliberately does not infer visibility. Callers must
    provide confirmed visible enemy ship ids; later intel/memory layers can
    represent stale or inferred contacts separately.
    """

    id: int
    owner_id: int
    hull_id: int
    x: int
    y: int
    damage: int


@dataclass(slots=True)
class PlayerObservation:
    """Information exposed to one autonomous player for a single turn."""

    game_id: int | str
    turn: int
    player_id: int
    own_planets: dict[int, Planet] = field(default_factory=dict)
    own_ships: dict[int, Ship] = field(default_factory=dict)
    own_starbases: dict[int, Starbase] = field(default_factory=dict)
    visible_enemy_ships: dict[int, ShipContact] = field(default_factory=dict)
