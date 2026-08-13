from planets_lab.core import Cargo, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim.normal_movement import (
    execute_full_normal_move,
    plan_full_normal_move,
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


def test_plans_and_executes_reachable_full_waypoint() -> None:
    ship = _ship()
    plan = plan_full_normal_move(
        ship,
        _specs(),
        target_x=110,
        target_y=100,
        warp=9,
    )

    assert plan.executable is True
    assert plan.reason is None
    assert plan.distance == 10
    assert plan.max_distance == 81
    assert plan.total_mass == 110
    assert plan.fuel_required == 1

    execute_full_normal_move(ship, plan)

    assert (ship.x, ship.y) == (110, 100)
    assert ship.cargo.neutronium == 39
    assert ship.warp == 9


def test_defers_waypoint_that_requires_partial_coordinate_movement() -> None:
    plan = plan_full_normal_move(
        _ship(),
        _specs(),
        target_x=200,
        target_y=100,
        warp=9,
    )

    assert plan.executable is False
    assert plan.reason == "partial_waypoint_required"
    assert plan.max_distance == 81


def test_defers_insufficient_fuel_instead_of_guessing_proration() -> None:
    plan = plan_full_normal_move(
        _ship(fuel=10),
        _specs(fuel_factor=1_000_000),
        target_x=181,
        target_y=100,
        warp=9,
    )

    assert plan.executable is False
    assert plan.reason == "insufficient_fuel"
    assert plan.fuel_required > 10


def test_warp_zero_does_not_move_to_a_different_waypoint() -> None:
    plan = plan_full_normal_move(
        _ship(),
        _specs(),
        target_x=101,
        target_y=100,
        warp=0,
    )

    assert plan.executable is False
    assert plan.reason == "warp_zero"


def test_same_location_is_a_zero_cost_executable_noop() -> None:
    ship = _ship()
    plan = plan_full_normal_move(
        ship,
        _specs(),
        target_x=100,
        target_y=100,
        warp=9,
    )

    assert plan.executable is True
    assert plan.fuel_required == 0

    execute_full_normal_move(ship, plan)
    assert ship.cargo.neutronium == 40
