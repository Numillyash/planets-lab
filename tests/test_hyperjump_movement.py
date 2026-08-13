import pytest

from planets_lab.core import Cargo, GameState, Planet, Player, Ship
from planets_lab.sim import (
    HostEngine,
    HyperjumpMovementPhase,
    TurnOrders,
    UnsupportedHyperjumpMovement,
    plan_hyperjump,
)


def _ship(
    *,
    waypoint_x: int = 450,
    warp: int = 9,
    fuel: int = 100,
    hull_id: int = 16,
) -> Ship:
    return Ship(
        id=1,
        owner_id=1,
        hull_id=hull_id,
        x=100,
        y=100,
        waypoint_x=waypoint_x,
        waypoint_y=100,
        warp=warp,
        friendly_code="HYP",
        cargo=Cargo(neutronium=fuel),
    )


def _state(ship: Ship, *, planets: dict[int, Planet] | None = None) -> GameState:
    return GameState(
        game_id=1,
        turn=5,
        players={1: Player(id=1)},
        planets=planets or {},
        ships={ship.id: ship},
    )


@pytest.mark.parametrize("waypoint_x", [440, 450, 460])
def test_exact_340_to_360_ly_hyperjump_is_executable(waypoint_x: int) -> None:
    plan = plan_hyperjump(_ship(waypoint_x=waypoint_x), hyperjump_hull_ids=frozenset({16}))
    assert plan.executable is True
    assert plan.destination_x == waypoint_x
    assert plan.destination_y == 100
    assert plan.fuel_used == 50


def test_hyperjump_phase_moves_ship_and_consumes_fixed_fuel() -> None:
    phase = HyperjumpMovementPhase(hyperjump_hull_ids=frozenset({16}))
    next_state, events = HostEngine((phase,)).step(_state(_ship()), TurnOrders.empty())
    moved = next_state.ships[1]
    assert (moved.x, moved.y) == (450, 100)
    assert moved.cargo.neutronium == 50
    assert moved.waypoint_x == 450
    assert moved.warp == 9
    assert events[0].kind == "hyperjump_moved"


def test_out_of_range_waypoint_is_fail_closed_until_350_projection_is_verified() -> None:
    phase = HyperjumpMovementPhase(hyperjump_hull_ids=frozenset({16}))
    with pytest.raises(UnsupportedHyperjumpMovement) as exc_info:
        HostEngine((phase,)).step(_state(_ship(waypoint_x=400)), TurnOrders.empty())
    assert exc_info.value.plan.reason == "default_350_projection_required"


def test_towed_hyperjump_ship_is_skipped() -> None:
    state = _state(_ship())
    state.metadata["movement.reserved_ship_ids"] = (1,)
    phase = HyperjumpMovementPhase(hyperjump_hull_ids=frozenset({16}))
    next_state, events = HostEngine((phase,)).step(state, TurnOrders.empty())
    assert (next_state.ships[1].x, next_state.ships[1].y) == (100, 100)
    assert next_state.ships[1].cargo.neutronium == 100
    assert events[0].kind == "hyperjump_skipped"


def test_hyperjump_warp_well_captures_only_under_three_ly() -> None:
    planets = {7: Planet(id=7, x=452, y=100)}
    phase = HyperjumpMovementPhase(
        hyperjump_hull_ids=frozenset({16}),
        enable_warp_wells=True,
    )
    next_state, events = HostEngine((phase,)).step(
        _state(_ship(), planets=planets), TurnOrders.empty()
    )
    assert (next_state.ships[1].x, next_state.ships[1].y) == (452, 100)
    assert ("warp_well_planet_id", "7") in events[0].details


def test_hyperjump_warp_well_does_not_capture_at_exactly_three_ly() -> None:
    planets = {7: Planet(id=7, x=453, y=100)}
    phase = HyperjumpMovementPhase(
        hyperjump_hull_ids=frozenset({16}),
        enable_warp_wells=True,
    )
    next_state, _ = HostEngine((phase,)).step(
        _state(_ship(), planets=planets), TurnOrders.empty()
    )
    assert (next_state.ships[1].x, next_state.ships[1].y) == (450, 100)


def test_non_capable_hull_is_fail_closed() -> None:
    phase = HyperjumpMovementPhase(hyperjump_hull_ids=frozenset({16}))
    with pytest.raises(UnsupportedHyperjumpMovement) as exc_info:
        HostEngine((phase,)).step(_state(_ship(hull_id=99)), TurnOrders.empty())
    assert exc_info.value.plan.reason == "not_hyperjump_capable"


def test_warp_zero_hyperjump_is_noop() -> None:
    phase = HyperjumpMovementPhase(hyperjump_hull_ids=frozenset({16}))
    next_state, events = HostEngine((phase,)).step(
        _state(_ship(warp=0)), TurnOrders.empty()
    )
    assert (next_state.ships[1].x, next_state.ships[1].y) == (100, 100)
    assert next_state.ships[1].cargo.neutronium == 100
    assert events[0].kind == "hyperjump_noop"
