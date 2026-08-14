import pytest

from planets_lab.core import GameState, Player, Ship
from planets_lab.data import import_loadturn
from planets_lab.observer import observe_player
from planets_lab.sim.engine import HostEngine
from planets_lab.sim.movement_classifier import classify_movement_intents
from planets_lab.sim.orders import PlayerOrders, ShipOrder, TurnOrders


def test_loadturn_imports_owner_zero_as_crewless_ghost_ship() -> None:
    state = import_loadturn(
        {
            "rst": {
                "game": {"id": 680910, "turn": 23},
                "player": {"id": 8, "raceid": 8},
                "players": [{"id": 8, "raceid": 8}],
                "planets": [],
                "ships": [
                    {
                        "id": 17,
                        "ownerid": 0,
                        "hullid": 16,
                        "engineid": 9,
                        "x": 2320,
                        "y": 2302,
                        "targetx": 2320,
                        "targety": 2302,
                        "warp": 0,
                        "crew": 0,
                        "neutronium": 250,
                        "clans": 79,
                    }
                ],
                "starbases": [],
            }
        }
    )

    ship = state.ships[17]
    assert ship.owner_id is None
    assert ship.crew == 0
    assert ship.is_ghost
    assert ship.warp == 0
    assert 0 not in state.players


def test_loadturn_maps_negative_owned_ship_crew_sentinel_to_unknown() -> None:
    state = import_loadturn(
        {
            "rst": {
                "game": {"id": 680910, "turn": 4},
                "player": {"id": 1, "raceid": 1},
                "players": [{"id": 1, "raceid": 1}],
                "planets": [],
                "ships": [
                    {
                        "id": 15,
                        "ownerid": 2,
                        "hullid": 16,
                        "x": 100,
                        "y": 200,
                        "warp": 0,
                        "crew": -1,
                    }
                ],
                "starbases": [],
            }
        }
    )

    ship = state.ships[15]
    assert ship.owner_id == 2
    assert ship.crew is None
    assert not ship.is_ghost


def test_loadturn_allows_hidden_crew_sentinel_on_unowned_ship() -> None:
    state = import_loadturn(
        {
            "rst": {
                "game": {"id": 680910, "turn": 23},
                "player": {"id": 8, "raceid": 8},
                "players": [{"id": 8, "raceid": 8}],
                "planets": [],
                "ships": [
                    {
                        "id": 17,
                        "ownerid": 0,
                        "hullid": 16,
                        "x": 2320,
                        "y": 2302,
                        "warp": 0,
                        "crew": -1,
                    }
                ],
                "starbases": [],
            }
        }
    )

    ship = state.ships[17]
    assert ship.owner_id is None
    assert ship.crew is None
    assert ship.is_ghost


def test_unowned_ship_rejects_nonzero_crew_or_warp() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        ships={
            1: Ship(id=1, owner_id=None, hull_id=1, x=0, y=0, crew=1, warp=0)
        },
    )
    with pytest.raises(ValueError, match="non-zero crew"):
        state.validate()

    state.ships[1].crew = 0
    state.ships[1].warp = 1
    with pytest.raises(ValueError, match="non-zero warp"):
        state.validate()


def test_canonical_state_still_rejects_negative_physical_crew() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1)},
        ships={
            1: Ship(id=1, owner_id=1, hull_id=1, x=0, y=0, crew=-1, warp=0)
        },
    )
    with pytest.raises(ValueError, match="negative crew"):
        state.validate()


def test_ghost_ship_ignores_stale_mission_classification() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        ships={
            1: Ship(
                id=1,
                owner_id=None,
                hull_id=1,
                x=0,
                y=0,
                crew=0,
                warp=0,
                mission="6",
                friendly_code="HYP",
            )
        },
    )
    state.validate()

    result = classify_movement_intents(state)
    assert result.move_most_candidate_ship_ids == frozenset({1})
    assert result.tow_attempt_ship_ids == frozenset()
    assert result.intercept_ship_ids == frozenset()
    assert result.special_move_most_ship_ids == frozenset()


def test_player_cannot_issue_orders_to_unowned_ghost_ship() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        players={8: Player(id=8)},
        ships={
            17: Ship(id=17, owner_id=None, hull_id=16, x=0, y=0, crew=0, warp=0)
        },
    )
    orders = TurnOrders(
        by_player={
            8: PlayerOrders(
                player_id=8,
                ship_orders=(ShipOrder(ship_id=17, warp=9),),
            )
        }
    )

    with pytest.raises(ValueError, match="cannot issue orders"):
        HostEngine().step(state, orders)


def test_visible_ghost_ship_contact_preserves_unowned_state() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        players={8: Player(id=8)},
        ships={
            17: Ship(id=17, owner_id=None, hull_id=16, x=10, y=20, crew=0, warp=0)
        },
    )

    observation = observe_player(state, 8, visible_enemy_ship_ids=(17,))
    assert observation.own_ships == {}
    assert observation.visible_enemy_ships[17].owner_id is None
