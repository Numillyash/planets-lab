import pytest

from planets_lab.core import Cargo, GameState, Planet, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.sim import HostEngine, PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.normal_movement_phase import NormalMovementPhase


def _specs() -> NuStaticSpecs:
    return NuStaticSpecs(
        hulls={
            16: HullSpec(
                id=16,
                name="MDSF",
                tech_level=3,
                mass=60,
                cargo_capacity=200,
                fuel_tank=250,
                crew=6,
                engine_count=1,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            )
        },
        engines={
            9: EngineSpec(
                id=9,
                name="Transwarp",
                tech_level=9,
                cost=ResourceCost(),
                warp_fuel_factors=(0,) + (10_000,) * 9,
            )
        },
    )


def _ship(*, x: int = 100, y: int = 100) -> Ship:
    return Ship(
        id=1,
        owner_id=1,
        hull_id=16,
        x=x,
        y=y,
        engine_id=9,
        cargo=Cargo(neutronium=100),
    )


def _orders(*, x: int, y: int, warp: int) -> TurnOrders:
    return TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(ShipOrder(ship_id=1, waypoint_x=x, waypoint_y=y, warp=warp),),
            )
        }
    )


def test_warp_well_boundary_is_three_light_years() -> None:
    planets = ((7, 100, 100),)

    assert warp_well_planet_id(
        origin_x=90, origin_y=100,
        end_x=103, end_y=100,
        movement_warp=9,
        planets=planets,
    ) == 7

    assert warp_well_planet_id(
        origin_x=90, origin_y=100,
        end_x=103, end_y=101,
        movement_warp=9,
        planets=planets,
    ) is None


def test_warp_one_and_nonmoving_ship_are_not_affected() -> None:
    planets = ((7, 100, 100),)

    assert warp_well_planet_id(
        origin_x=99, origin_y=100,
        end_x=100, end_y=100,
        movement_warp=1,
        planets=planets,
    ) is None

    assert warp_well_planet_id(
        origin_x=103, origin_y=100,
        end_x=103, end_y=100,
        movement_warp=9,
        planets=planets,
    ) is None


def test_excluded_planetoid_has_no_warp_well() -> None:
    assert warp_well_planet_id(
        origin_x=90, origin_y=100,
        end_x=103, end_y=100,
        movement_warp=9,
        planets=((7, 100, 100),),
        excluded_planet_ids=frozenset({7}),
    ) is None


def test_overlapping_wells_fail_closed() -> None:
    with pytest.raises(WarpWellAmbiguityError):
        warp_well_planet_id(
            origin_x=90, origin_y=100,
            end_x=102, end_y=100,
            movement_warp=9,
            planets=((7, 100, 100), (8, 104, 100)),
        )


def test_phase_pulls_endpoint_to_planet_and_preserves_waypoint() -> None:
    state = GameState(
        game_id="warp-well",
        turn=1,
        players={1: Player(id=1)},
        planets={7: Planet(id=7, x=110, y=100)},
        ships={1: _ship()},
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
        enable_warp_wells=True,
    )

    next_state, events = HostEngine((phase,)).step(
        state,
        _orders(x=107, y=100, warp=9),
    )

    ship = next_state.ships[1]
    assert (ship.x, ship.y) == (110, 100)
    assert (ship.waypoint_x, ship.waypoint_y) == (107, 100)
    assert ("warp_well_planet_id", "7") in events[0].details


def test_partial_move_can_end_in_warp_well() -> None:
    state = GameState(
        game_id="warp-well-partial",
        turn=1,
        players={1: Player(id=1)},
        planets={7: Planet(id=7, x=184, y=100)},
        ships={1: _ship()},
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
        enable_expanded_movement=True,
        enable_warp_wells=True,
    )

    next_state, events = HostEngine((phase,)).step(
        state,
        _orders(x=300, y=100, warp=9),
    )

    ship = next_state.ships[1]
    assert (ship.x, ship.y) == (184, 100)
    assert (ship.waypoint_x, ship.waypoint_y) == (300, 100)
    assert ("partial", "true") in events[0].details
    assert ("warp_well_planet_id", "7") in events[0].details
