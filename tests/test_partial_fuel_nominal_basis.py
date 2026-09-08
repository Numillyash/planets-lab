from planets_lab.core import Cargo, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim.normal_movement import execute_full_normal_move, plan_full_normal_move


def _specs(*, hull_mass: int, fuel_factor: int) -> NuStaticSpecs:
    hull = HullSpec(
        id=23,
        name="Partial fuel anchor hull",
        tech_level=1,
        mass=hull_mass,
        cargo_capacity=2000,
        fuel_tank=5000,
        crew=1,
        engine_count=1,
        beam_count=0,
        torpedo_launcher_count=0,
        fighter_bay_count=0,
        can_cloak=False,
        cost=ResourceCost(),
    )
    engine = EngineSpec(
        id=9,
        name="Anchor engine",
        tech_level=9,
        cost=ResourceCost(),
        warp_fuel_factors=(0,) + (fuel_factor,) * 9,
    )
    return NuStaticSpecs(hulls={23: hull}, engines={9: engine})


def _ship(*, x: int, y: int, fuel: int) -> Ship:
    return Ship(
        id=41,
        owner_id=2,
        hull_id=23,
        x=x,
        y=y,
        engine_id=9,
        warp=9,
        cargo=Cargo(neutronium=fuel),
    )


def test_move_most_anchor_uses_continuous_nominal_leg_before_rasterization() -> None:
    """Reproduce the 360690/T164/ship41 40-vs-41 discriminator.

    Hull mass 506 plus 11 KT fuel gives the factual 517 KT movement mass.
    The synthetic engine factor is chosen so the rasterized 80.498-ly endpoint
    costs 40 KT while the continuous 81-ly leg costs 41 KT. With only 11 KT,
    the latter is the model that reproduces the factual NuHost endpoint.
    """

    ship = _ship(x=1949, y=2950, fuel=11)
    plan = plan_full_normal_move(
        ship,
        _specs(hull_mass=506, fuel_factor=8040),
        target_x=2008,
        target_y=3067,
        warp=9,
        allow_partial=True,
        allow_fuel_proration=True,
    )

    assert plan.executable is True
    assert plan.partial is True
    assert plan.fuel_limited is True
    assert plan.total_mass == 517
    assert plan.max_distance == 81
    assert plan.fuel_required == 41
    assert plan.fuel_used == 11
    assert (plan.destination_x, plan.destination_y) == (1959, 2969)

    execute_full_normal_move(ship, plan)
    assert (ship.x, ship.y) == (1959, 2969)
    assert ship.cargo.neutronium == 0
    assert ship.warp == 0
    assert (ship.waypoint_x, ship.waypoint_y) == (1959, 2969)


def test_intercept_anchor_equivalent_uses_72_not_rasterized_71_cost() -> None:
    """Reproduce the 620694/T73/ship278 71-vs-72 geometry discriminator.

    The constructed 900-KT movement mass and engine factor make the integer
    one-turn endpoint distance cost 71 KT while the continuous W9 81-ly leg
    costs 72 KT. NuHost's factual endpoint corresponds to 29/72 proration.
    InterceptMovementPhase uses this same planner, so this locks the shared
    movement-law primitive without duplicating Intercept phase setup here.
    """

    ship = _ship(x=2758, y=2098, fuel=29)
    plan = plan_full_normal_move(
        ship,
        _specs(hull_mass=871, fuel_factor=8000),
        target_x=2717,
        target_y=2026,
        warp=9,
        allow_partial=True,
        allow_fuel_proration=True,
    )

    assert plan.executable is True
    assert plan.partial is True
    assert plan.fuel_limited is True
    assert plan.total_mass == 900
    assert plan.max_distance == 81
    assert plan.fuel_required == 72
    assert plan.fuel_used == 29
    assert (plan.destination_x, plan.destination_y) == (2742, 2070)
