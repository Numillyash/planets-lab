from planets_lab.core import Cargo, GameState, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim import HostEngine, PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.normal_movement import plan_full_normal_move, project_toward_waypoint
from planets_lab.sim.normal_movement_phase import NormalMovementPhase


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


def _ship(*, fuel: int = 40) -> Ship:
    return Ship(
        id=1,
        owner_id=1,
        hull_id=16,
        x=100,
        y=100,
        engine_id=9,
        cargo=Cargo(neutronium=fuel, supplies=10),
    )


def _state(ship: Ship) -> GameState:
    return GameState(
        game_id="partial-movement",
        turn=10,
        players={1: Player(id=1, name="Alpha")},
        ships={ship.id: ship},
    )


def test_projection_matches_observed_diagonal_sample() -> None:
    assert project_toward_waypoint(
        x=1836,
        y=2187,
        target_x=1851,
        target_y=2299,
        distance=81,
    ) == (1847, 2267)


def test_projection_matches_real_game_680933_turn6_ship32() -> None:
    # NuHost observation: independent nearest-coordinate projection predicts
    # (1551, 2121), while the actual next turn is (1550, 2121).
    assert project_toward_waypoint(
        x=1577,
        y=2044,
        target_x=1532,
        target_y=2174,
        distance=81,
    ) == (1550, 2121)


def test_expanded_planner_executes_partial_waypoint() -> None:
    plan = plan_full_normal_move(
        _ship(),
        _specs(),
        target_x=300,
        target_y=100,
        warp=9,
        allow_partial=True,
        allow_fuel_proration=True,
    )

    assert plan.executable is True
    assert plan.partial is True
    assert (plan.destination_x, plan.destination_y) == (181, 100)
    assert plan.fuel_limited is False


def test_expanded_phase_moves_one_partial_turn_and_preserves_waypoint() -> None:
    state = _state(_ship())
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=1, waypoint_x=300, waypoint_y=100, warp=9),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(),
        eligible_ship_ids=frozenset({1}),
        enable_expanded_movement=True,
    )

    next_state, events = HostEngine((phase,)).step(state, orders)

    ship = next_state.ships[1]
    assert (ship.x, ship.y) == (181, 100)
    assert (ship.waypoint_x, ship.waypoint_y) == (300, 100)
    assert ship.warp == 9
    assert events[0].kind == "ship_moved"
    assert ("partial", "true") in events[0].details
    assert ("fuel_limited", "false") in events[0].details


def test_expanded_phase_prorates_reachable_waypoint_when_fuel_is_short() -> None:
    state = _state(_ship(fuel=10))
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=1, waypoint_x=181, waypoint_y=100, warp=9),
                ),
            )
        }
    )
    phase = NormalMovementPhase(
        specs=_specs(fuel_factor=1_000_000),
        eligible_ship_ids=frozenset({1}),
        enable_expanded_movement=True,
    )

    next_state, events = HostEngine((phase,)).step(state, orders)

    ship = next_state.ships[1]
    assert (ship.x, ship.y) == (101, 100)
    assert ship.cargo.neutronium == 0
    assert ship.warp == 0
    assert (ship.waypoint_x, ship.waypoint_y) == (101, 100)
    assert ("fuel_limited", "true") in events[0].details
