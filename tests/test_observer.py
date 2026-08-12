from planets_lab.core.models import GameState, Planet, Player, Ship
from planets_lab.observer import observe_player


def make_state() -> GameState:
    return GameState(
        game_id=7,
        turn=12,
        players={1: Player(id=1), 2: Player(id=2)},
        planets={
            10: Planet(id=10, x=1000, y=1000, owner_id=1),
            20: Planet(id=20, x=1200, y=1000, owner_id=2),
        },
        ships={
            101: Ship(id=101, owner_id=1, hull_id=1, x=1000, y=1000),
            202: Ship(id=202, owner_id=2, hull_id=2, x=1100, y=1000),
        },
    )


def test_observer_does_not_leak_enemy_assets_by_default() -> None:
    state = make_state()

    obs = observe_player(state, 1)

    assert set(obs.own_planets) == {10}
    assert set(obs.own_ships) == {101}
    assert obs.visible_enemy_ships == {}
    assert 20 not in obs.own_planets
    assert 202 not in obs.own_ships


def test_observer_exposes_only_explicit_enemy_contacts() -> None:
    state = make_state()

    obs = observe_player(state, 1, visible_enemy_ship_ids=[202])

    contact = obs.visible_enemy_ships[202]
    assert contact.owner_id == 2
    assert (contact.x, contact.y) == (1100, 1000)


def test_observation_owns_copies_of_mutable_assets() -> None:
    state = make_state()

    obs = observe_player(state, 1)
    obs.own_ships[101].damage = 50

    assert state.ships[101].damage == 0
