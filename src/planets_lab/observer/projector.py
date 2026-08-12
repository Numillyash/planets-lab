from __future__ import annotations

from copy import deepcopy
from collections.abc import Iterable

from planets_lab.core.models import GameState
from planets_lab.observer.models import PlayerObservation, ShipContact


def observe_player(
    state: GameState,
    player_id: int,
    *,
    visible_enemy_ship_ids: Iterable[int] = (),
) -> PlayerObservation:
    """Project omniscient state into a player-limited observation.

    Visibility rules are intentionally outside this function for now. Enemy
    ships are exposed only when their ids are explicitly supplied as confirmed
    visible contacts. This keeps incomplete NuHost visibility mechanics from
    leaking omniscient state into agents.
    """

    state.validate()
    if player_id not in state.players:
        raise ValueError(f"unknown player {player_id}")

    own_planets = {
        planet_id: deepcopy(planet)
        for planet_id, planet in state.planets.items()
        if planet.owner_id == player_id
    }
    own_ships = {
        ship_id: deepcopy(ship)
        for ship_id, ship in state.ships.items()
        if ship.owner_id == player_id
    }
    own_starbases = {
        planet_id: deepcopy(starbase)
        for planet_id, starbase in state.starbases.items()
        if starbase.owner_id == player_id
    }

    contacts: dict[int, ShipContact] = {}
    for ship_id in visible_enemy_ship_ids:
        ship = state.ships.get(ship_id)
        if ship is None:
            raise ValueError(f"visible enemy ship {ship_id} does not exist")
        if ship.owner_id == player_id:
            continue
        contacts[ship_id] = ShipContact(
            id=ship.id,
            owner_id=ship.owner_id,
            hull_id=ship.hull_id,
            x=ship.x,
            y=ship.y,
            damage=ship.damage,
        )

    return PlayerObservation(
        game_id=state.game_id,
        turn=state.turn,
        player_id=player_id,
        own_planets=own_planets,
        own_ships=own_ships,
        own_starbases=own_starbases,
        visible_enemy_ships=contacts,
    )
