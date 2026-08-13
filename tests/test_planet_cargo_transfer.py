import pytest

from planets_lab.core import Cargo, GameState, Planet, Player, Ship
from planets_lab.data.nu_specs import HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim.engine import HostEngine
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder,
    PlayerOrders,
    ShipOrder,
    TurnOrders,
)
from planets_lab.sim.planet_cargo_transfer_phase import (
    PlanetCargoTransferPhase,
    UnsupportedPlanetCargoTransfer,
)


def _specs() -> NuStaticSpecs:
    return NuStaticSpecs(
        hulls={
            1: HullSpec(
                id=1,
                name="Freighter",
                tech_level=1,
                mass=50,
                cargo_capacity=200,
                fuel_tank=100,
                crew=10,
                engine_count=2,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            )
        }
    )


def _state(*, owner_id: int | None = None) -> GameState:
    return GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1, race_id=1), 2: Player(id=2, race_id=2)},
        planets={
            10: Planet(
                id=10,
                x=100,
                y=100,
                owner_id=owner_id,
                cargo=Cargo(neutronium=80, supplies=40, clans=50, megacredits=100),
            )
        },
        ships={
            1: Ship(
                id=1,
                owner_id=1,
                hull_id=1,
                x=100,
                y=100,
                cargo=Cargo(neutronium=20, supplies=30, clans=20, megacredits=25),
            )
        },
    )


def _orders(transfer: PlanetCargoTransferOrder) -> TurnOrders:
    return TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(ShipOrder(ship_id=1, planet_transfer=transfer),),
            )
        }
    )


def test_clans_colonize_unowned_planet() -> None:
    state = _state(owner_id=None)
    orders = _orders(
        PlanetCargoTransferOrder(planet_id=10, clans=10, supplies=15, neutronium=5)
    )
    next_state, events = HostEngine((PlanetCargoTransferPhase(_specs()),)).step(state, orders)
    planet = next_state.planets[10]
    ship = next_state.ships[1]
    assert planet.owner_id == 1
    assert planet.cargo.clans == 60
    assert planet.cargo.supplies == 55
    assert planet.cargo.neutronium == 85
    assert ship.cargo.clans == 10
    assert events[0].kind == "planet_colonized"


def test_owned_planet_can_load_ship_with_resources_and_money() -> None:
    state = _state(owner_id=1)
    orders = _orders(
        PlanetCargoTransferOrder(
            planet_id=10,
            direction="planet_to_ship",
            neutronium=30,
            supplies=20,
            clans=10,
            megacredits=50,
        )
    )
    next_state, events = HostEngine((PlanetCargoTransferPhase(_specs()),)).step(state, orders)
    ship = next_state.ships[1]
    assert ship.cargo.neutronium == 50
    assert ship.cargo.supplies == 50
    assert ship.cargo.clans == 30
    assert ship.cargo.megacredits == 75
    assert events[0].kind == "planet_cargo_transferred"


def test_unowned_planet_rejects_megacredits_in_ordinary_transfer() -> None:
    state = _state(owner_id=None)
    orders = _orders(PlanetCargoTransferOrder(planet_id=10, megacredits=1))
    with pytest.raises(UnsupportedPlanetCargoTransfer):
        HostEngine((PlanetCargoTransferPhase(_specs()),)).step(state, orders)


def test_other_owner_planet_transfer_is_deferred() -> None:
    state = _state(owner_id=2)
    orders = _orders(PlanetCargoTransferOrder(planet_id=10, clans=1))
    with pytest.raises(UnsupportedPlanetCargoTransfer):
        HostEngine((PlanetCargoTransferPhase(_specs()),)).step(state, orders)


def test_ship_capacity_is_enforced_when_loading_from_planet() -> None:
    specs = _specs()
    hull = specs.hulls[1]
    specs.hulls[1] = HullSpec(
        id=hull.id,
        name=hull.name,
        tech_level=hull.tech_level,
        mass=hull.mass,
        cargo_capacity=45,
        fuel_tank=40,
        crew=hull.crew,
        engine_count=hull.engine_count,
        beam_count=hull.beam_count,
        torpedo_launcher_count=hull.torpedo_launcher_count,
        fighter_bay_count=hull.fighter_bay_count,
        can_cloak=hull.can_cloak,
        cost=hull.cost,
    )
    state = _state(owner_id=1)
    orders = _orders(
        PlanetCargoTransferOrder(planet_id=10, direction="planet_to_ship", supplies=1)
    )
    with pytest.raises(UnsupportedPlanetCargoTransfer):
        HostEngine((PlanetCargoTransferPhase(specs),)).step(state, orders)
