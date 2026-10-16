"""Shared dependency-free deterministic fixtures for the M2 research slice.

These are synthetic input states/orders, not NuHost archival observations.
The server diagnostic and CI tests intentionally use the same fixtures.
"""
from __future__ import annotations

from planets_lab.core import Cargo, GameState, MineralDeposit, Planet, Player, Ship
from planets_lab.data.nu_specs import HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim.orders import PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders

def specs(capacity=200, fuel=100):
    return NuStaticSpecs(hulls={1: HullSpec(
        id=1, name="Test freighter", tech_level=1, mass=50,
        cargo_capacity=capacity, fuel_tank=fuel, crew=10, engine_count=2,
        beam_count=0, torpedo_launcher_count=0, fighter_bay_count=0,
        can_cloak=False, cost=ResourceCost(),
    )})


def fixture():
    return GameState(
        game_id="research-slice", turn=7,
        players={1: Player(id=1, race_id=1), 2: Player(id=2, race_id=2)},
        planets={10: Planet(
            id=10, x=100, y=100, owner_id=1, temperature=50,
            cargo=Cargo(clans=100, supplies=40, megacredits=20, neutronium=80),
            ground_duranium=MineralDeposit(amount=1000, density=100),
            factories=10, mines=10, happiness=100, tax_rate=10,
        )},
        ships={1: Ship(id=1, owner_id=1, hull_id=1, x=100, y=100,
                       cargo=Cargo(supplies=20, neutronium=10, clans=10))},
    )


def order(direction="planet_to_ship", **kwargs):
    return TurnOrders(by_player={1: PlayerOrders(player_id=1, ship_orders=(
        ShipOrder(ship_id=1, planet_transfer=PlanetCargoTransferOrder(
            planet_id=10, direction=direction, **kwargs,
        )),
    ))})




def orders_sequence() -> tuple[TurnOrders, ...]:
    return (
        order(supplies=10, neutronium=10, clans=5),
        order("ship_to_planet", supplies=4, neutronium=5, clans=3),
        TurnOrders.empty(),
    )


def unsupported_scenarios() -> tuple[tuple[str, GameState, NuStaticSpecs, TurnOrders], ...]:
    """Independent unsupported-input controls for fail-closed runtime verification."""
    cases = []
    for kind in ("cargo", "fuel", "owner", "orbit", "funds",
                 "unowned_money", "unknown_hull", "movement"):
        state = fixture()
        static = specs(capacity=45 if kind == "cargo" else 200,
                       fuel=12 if kind == "fuel" else 100)
        request = order(
            supplies=40 if kind == "cargo" else 0,
            neutronium=5 if kind == "fuel" else 0,
            megacredits=100000 if kind == "funds" else 0,
        )
        if kind == "owner":
            state.planets[10].owner_id = 2
            request = order(supplies=1)
        elif kind == "orbit":
            state.ships[1].x = 101
            request = order(supplies=1)
        elif kind == "unowned_money":
            state.planets[10].owner_id = None
            request = order("ship_to_planet", megacredits=1)
        elif kind == "unknown_hull":
            state.ships[1].hull_id = 200
            request = order(supplies=1)
        elif kind == "movement":
            request = TurnOrders(by_player={1: PlayerOrders(
                player_id=1, ship_orders=(ShipOrder(
                    ship_id=1, warp=9,
                    planet_transfer=PlanetCargoTransferOrder(
                        planet_id=10, supplies=1, direction="planet_to_ship"
                    ),
                ),)
            )})
        cases.append((kind, state, static, request))
    return tuple(cases)
