import pytest

from planets_lab.core import Cargo, GameState, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.tow import UnsupportedTowTopology, resolve_tow_locks
from planets_lab.sim.tow_movement_phase import TowMovementPhase


def _specs(*, tower_engines: int = 2) -> NuStaticSpecs:
    return NuStaticSpecs(
        hulls={
            16: HullSpec(id=16, name="Tower", tech_level=1, mass=100, cargo_capacity=100, fuel_tank=300, crew=10, engine_count=tower_engines, beam_count=0, torpedo_launcher_count=0, fighter_bay_count=0, can_cloak=False, cost=ResourceCost()),
            17: HullSpec(id=17, name="Target", tech_level=1, mass=50, cargo_capacity=100, fuel_tank=300, crew=10, engine_count=2, beam_count=0, torpedo_launcher_count=0, fighter_bay_count=0, can_cloak=False, cost=ResourceCost()),
        },
        engines={
            9: EngineSpec(id=9, name="Transwarp", tech_level=9, cost=ResourceCost(), warp_fuel_factors=(0,) + (10_000,) * 9),
        },
    )


def _ship(ship_id: int, *, hull_id: int, fuel: int, warp: int = 9, waypoint_x: int = 110, mission: str | None = None, target_id: int | None = None) -> Ship:
    return Ship(
        id=ship_id,
        owner_id=1,
        hull_id=hull_id,
        x=100,
        y=100,
        engine_id=9,
        waypoint_x=waypoint_x,
        waypoint_y=100,
        warp=warp,
        mission=mission,
        mission1_target_id=target_id,
        cargo=Cargo(neutronium=fuel),
    )


def _state(*ships: Ship) -> GameState:
    return GameState(game_id=1, turn=5, players={1: Player(id=1)}, ships={s.id: s for s in ships})


def test_simple_tow_lock_succeeds() -> None:
    tower = _ship(1, hull_id=16, fuel=100, mission="6", target_id=2)
    target = _ship(2, hull_id=17, fuel=0)
    result = resolve_tow_locks(_state(tower, target), _specs())
    assert result.successful[0].tower_ship_id == 1
    assert result.successful[0].target_ship_id == 2


def test_four_fingers_break_tow() -> None:
    tower = _ship(1, hull_id=16, fuel=100, warp=7, mission="6", target_id=2)
    target = _ship(2, hull_id=17, fuel=26, warp=7, waypoint_x=150)
    result = resolve_tow_locks(_state(tower, target), _specs())
    assert result.attempts[0].locked is False
    assert result.attempts[0].reason == "target_broke_lock"


def test_lower_ship_id_wins_tow_contest() -> None:
    low = _ship(1, hull_id=16, fuel=100, mission="6", target_id=3)
    high = _ship(2, hull_id=16, fuel=100, mission="6", target_id=3)
    target = _ship(3, hull_id=17, fuel=0)
    result = resolve_tow_locks(_state(low, high, target), _specs())
    assert [(a.tower_ship_id, a.locked, a.reason) for a in result.attempts] == [
        (1, True, None),
        (2, False, "tow_contest_lost"),
    ]


def test_tow_chain_is_fail_closed() -> None:
    one = _ship(1, hull_id=16, fuel=100, mission="6", target_id=2)
    two = _ship(2, hull_id=16, fuel=100, mission="6", target_id=3)
    three = _ship(3, hull_id=17, fuel=0)
    with pytest.raises(UnsupportedTowTopology):
        resolve_tow_locks(_state(one, two, three), _specs())


def test_tow_phase_moves_both_and_uses_combined_mass() -> None:
    tower = _ship(1, hull_id=16, fuel=100, mission="6", target_id=2)
    target = _ship(2, hull_id=17, fuel=0, waypoint_x=150)
    phase = TowMovementPhase(specs=_specs())

    next_state, events = HostEngine((phase,)).step(_state(tower, target), TurnOrders.empty())

    assert (next_state.ships[1].x, next_state.ships[1].y) == (110, 100)
    assert (next_state.ships[2].x, next_state.ships[2].y) == (110, 100)
    assert next_state.ships[2].warp == 0
    assert next_state.ships[2].waypoint_x == 150
    assert next_state.ships[1].cargo.neutronium == 97
    assert events[0].kind == "tow_moved"
    assert ("movement_mass", "250") in events[0].details
    assert next_state.metadata["movement.reserved_ship_ids"] == (1, 2)


def test_failed_tow_is_bumped_to_move_most() -> None:
    tower = _ship(1, hull_id=16, fuel=100, mission="6", target_id=2)
    target = _ship(2, hull_id=17, fuel=0)
    phase = TowMovementPhase(specs=_specs(tower_engines=1))

    next_state, events = HostEngine((phase,)).step(_state(tower, target), TurnOrders.empty())

    assert events[0].kind == "tow_failed"
    assert ("reason", "insufficient_engines") in events[0].details
    assert next_state.metadata["movement.bumped_to_move_most_ship_ids"] == (1,)
    assert (next_state.ships[1].x, next_state.ships[1].y) == (100, 100)
