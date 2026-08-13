import pytest

from planets_lab.core import Cargo, GameState, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim import HostEngine, PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.normal_movement_phase import (
    NormalMovementPhase,
    UnsupportedNormalMovement,
)


def _specs(*, fuel_factor: int = 10_000) -> NuStaticSpecs:
    hull = HullSpec(
        id=16,
        name="Medium Deep Space Freighter",
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
    engine = EngineSpec(
        id=9,
        name="Transwarp Drive",
        tech_level=9,
        cost=ResourceCost(),
        warp_fuel_factors=(0,) + (fuel_factor,) * 9,
    )
    return NuStaticSpecs(hulls={16: hull}, engines={9: engine})


def _ship(
    ship_id: int,
    *,
    x: int = 100,
    y: int = 100,
    fuel: int = 40,
) -> Ship:
    return Ship(
        id=ship_id,
        owner_id=1,
        hull_id=16,
        x=x,
        y=y,
        engine_id=9,
        cargo=Cargo(neutronium=fuel, supplies=10),
    )


def _state(*ships: Ship) -> GameState:
    return GameState(
        game_id="movement-phase",
        turn=7,
        players={1: Player(id=1, name="Alpha")},
        ships={ship.id: ship for ship in ships},
    )


def test_phase_executes_reachable_order_inside_host_engine() -> None:
    state = _state(_ship(1))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(
                        ship_id=1,
                        waypoint_x=110,
                        waypoint_y=100,
                        warp=9,
                    ),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
    )

    next_state, events = HostEngine((phase,)).step(state, orders)

    assert state.turn == 7
    assert (state.ships[1].x, state.ships[1].y) == (100, 100)
    assert state.ships[1].cargo.neutronium == 40

    assert next_state.turn == 8
    assert (next_state.ships[1].x, next_state.ships[1].y) == (110, 100)
    assert next_state.ships[1].cargo.neutronium == 39
    assert next_state.ships[1].waypoint_x == 110
    assert next_state.ships[1].warp == 9

    assert len(events) == 1
    event = events[0]
    assert event.phase == "normal_movement"
    assert event.kind == "ship_moved"
    assert event.entity_type == "ship"
    assert event.entity_id == 1
    assert ("fuel_used", "1") in event.details
    assert ("movement_mass", "110") in event.details


def test_phase_processes_eligible_ships_in_ascending_ship_id_order() -> None:
    state = _state(_ship(9), _ship(2))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=9, waypoint_x=109, waypoint_y=100, warp=9),
                    ShipOrder(ship_id=2, waypoint_x=102, waypoint_y=100, warp=9),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({9, 2}),
    )

    _, events = HostEngine((phase,)).step(state, orders)

    assert [event.entity_id for event in events] == [2, 9]
    assert [event.kind for event in events] == ["ship_moved", "ship_moved"]


def test_phase_fails_closed_for_partial_waypoint() -> None:
    state = _state(_ship(1))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=1, waypoint_x=200, waypoint_y=100, warp=9),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
    )

    with pytest.raises(UnsupportedNormalMovement) as exc_info:
        HostEngine((phase,)).step(state, orders)

    assert exc_info.value.plan.reason == "partial_waypoint_required"
    assert (state.ships[1].x, state.ships[1].y) == (100, 100)


def test_research_mode_can_emit_explicit_deferred_event() -> None:
    state = _state(_ship(1))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=1, waypoint_x=200, waypoint_y=100, warp=9),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
        allow_deferred=True,
    )

    next_state, events = HostEngine((phase,)).step(state, orders)

    assert next_state.turn == 8
    assert (next_state.ships[1].x, next_state.ships[1].y) == (100, 100)
    assert next_state.ships[1].waypoint_x == 200
    assert next_state.ships[1].warp == 9
    assert events[0].kind == "ship_deferred"
    assert events[0].entity_id == 1
    assert ("reason", "partial_waypoint_required") in events[0].details


def test_warp_zero_is_a_valid_noop() -> None:
    state = _state(_ship(1))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=1, waypoint_x=110, waypoint_y=100, warp=0),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
    )

    next_state, events = HostEngine((phase,)).step(state, orders)

    assert (next_state.ships[1].x, next_state.ships[1].y) == (100, 100)
    assert next_state.ships[1].waypoint_x == 110
    assert next_state.ships[1].warp == 0
    assert events[0].kind == "ship_noop"
    assert ("reason", "warp_zero") in events[0].details


def test_phase_rejects_unknown_eligibility_ids() -> None:
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({99}),
    )

    with pytest.raises(ValueError, match="unknown ships: 99"):
        HostEngine((phase,)).step(_state(_ship(1)), TurnOrders.empty())
