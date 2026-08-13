import pytest

from planets_lab.core import Cargo, GameState, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim import HostEngine, InterceptMovementPhase, NormalMovementPhase, TurnOrders, UnsupportedInterceptMovement


def specs():
    return NuStaticSpecs(
        hulls={16: HullSpec(id=16, name="Ship", tech_level=1, mass=100, cargo_capacity=100, fuel_tank=300, crew=10, engine_count=2, beam_count=0, torpedo_launcher_count=0, fighter_bay_count=0, can_cloak=False, cost=ResourceCost())},
        engines={9: EngineSpec(id=9, name="Engine", tech_level=9, cost=ResourceCost(), warp_fuel_factors=(0,) + (10000,) * 9)},
    )


def ship(ship_id, x, waypoint_x, mission=None, target_id=None):
    return Ship(id=ship_id, owner_id=1, hull_id=16, x=x, y=100, engine_id=9, waypoint_x=waypoint_x, waypoint_y=100, warp=9, mission=mission, mission1_target_id=target_id, cargo=Cargo(neutronium=100))


def state(*ships):
    return GameState(game_id=1, turn=5, players={1: Player(id=1)}, ships={s.id: s for s in ships})


def test_intercept_uses_position_after_move_most():
    interceptor = ship(1, 90, 90, mission="7", target_id=2)
    target = ship(2, 100, 110)
    engine = HostEngine((NormalMovementPhase(specs=specs(), enable_expanded_movement=True), InterceptMovementPhase(specs=specs(), enable_expanded_movement=True)))
    next_state, events = engine.step(state(interceptor, target), TurnOrders.empty())
    assert next_state.ships[2].x == 110
    assert next_state.ships[1].x == 110
    event = next(e for e in events if e.kind == "intercept_moved")
    assert ("target_x", "110") in event.details


def test_reserved_interceptor_is_skipped():
    interceptor = ship(1, 90, 90, mission="7", target_id=2)
    target = ship(2, 110, 110)
    current = state(interceptor, target)
    current.metadata["movement.reserved_ship_ids"] = (1,)
    next_state, events = HostEngine((InterceptMovementPhase(specs=specs()),)).step(current, TurnOrders.empty())
    assert next_state.ships[1].x == 90
    assert events[0].kind == "intercept_skipped"


def test_invalid_target_is_fail_closed():
    interceptor = ship(1, 90, 90, mission="7", target_id=999)
    with pytest.raises(UnsupportedInterceptMovement, match="invalid_target"):
        HostEngine((InterceptMovementPhase(specs=specs()),)).step(state(interceptor), TurnOrders.empty())


def test_invalid_target_can_be_deferred():
    interceptor = ship(1, 90, 90, mission="7", target_id=None)
    next_state, events = HostEngine((InterceptMovementPhase(specs=specs(), allow_deferred=True),)).step(state(interceptor), TurnOrders.empty())
    assert next_state.ships[1].x == 90
    assert events[0].kind == "intercept_deferred"
