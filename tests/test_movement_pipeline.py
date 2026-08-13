from planets_lab.core import Cargo, GameState, Player, Ship
from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim import HostEngine, NormalMovementPhase, TowMovementPhase, TurnOrders


def _specs(*, tower_engines: int = 2) -> NuStaticSpecs:
    return NuStaticSpecs(
        hulls={
            16: HullSpec(
                id=16,
                name="Tower",
                tech_level=1,
                mass=100,
                cargo_capacity=100,
                fuel_tank=300,
                crew=10,
                engine_count=tower_engines,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            ),
            17: HullSpec(
                id=17,
                name="Ship",
                tech_level=1,
                mass=50,
                cargo_capacity=100,
                fuel_tank=300,
                crew=10,
                engine_count=2,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            ),
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


def _ship(
    ship_id: int,
    *,
    hull_id: int = 17,
    x: int = 100,
    waypoint_x: int = 110,
    warp: int = 9,
    fuel: int = 100,
    mission: str | None = None,
    target_id: int | None = None,
    friendly_code: str = "",
) -> Ship:
    return Ship(
        id=ship_id,
        owner_id=1,
        hull_id=hull_id,
        x=x,
        y=100,
        engine_id=9,
        waypoint_x=waypoint_x,
        waypoint_y=100,
        warp=warp,
        mission=mission,
        mission1_target_id=target_id,
        friendly_code=friendly_code,
        cargo=Cargo(neutronium=fuel),
    )


def _state(*ships: Ship) -> GameState:
    return GameState(
        game_id=1,
        turn=5,
        players={1: Player(id=1)},
        ships={ship.id: ship for ship in ships},
    )


def test_successful_tow_pair_is_not_moved_again_in_move_most() -> None:
    specs = _specs()
    tower = _ship(1, hull_id=16, mission="6", target_id=2)
    target = _ship(2, waypoint_x=150, fuel=0)
    normal = _ship(3, waypoint_x=120)

    engine = HostEngine((
        TowMovementPhase(specs=specs),
        NormalMovementPhase(specs=specs),
    ))
    next_state, events = engine.step(
        _state(tower, target, normal),
        TurnOrders.empty(),
    )

    assert next_state.ships[1].x == 110
    assert next_state.ships[2].x == 110
    assert next_state.ships[3].x == 120
    assert [event.kind for event in events].count("tow_moved") == 1
    assert [event.entity_id for event in events if event.phase == "normal_movement"] == [3]


def test_failed_tow_attempt_is_bumped_into_move_most() -> None:
    specs = _specs(tower_engines=1)
    tower = _ship(1, hull_id=16, mission="6", target_id=2)
    target = _ship(2, waypoint_x=100, warp=0, fuel=0)

    engine = HostEngine((
        TowMovementPhase(specs=specs),
        NormalMovementPhase(specs=specs),
    ))
    next_state, events = engine.step(
        _state(tower, target),
        TurnOrders.empty(),
    )

    assert events[0].kind == "tow_failed"
    assert next_state.ships[1].x == 110
    assert any(
        event.phase == "normal_movement"
        and event.entity_id == 1
        and event.kind == "ship_moved"
        for event in events
    )


def test_intercept_and_hyp_are_not_sent_to_normal_movement() -> None:
    specs = _specs()
    normal = _ship(1)
    intercept = _ship(2, mission="7")
    hyp = _ship(3, friendly_code="HYP")

    next_state, events = HostEngine((
        NormalMovementPhase(specs=specs),
    )).step(
        _state(normal, intercept, hyp),
        TurnOrders.empty(),
    )

    assert next_state.ships[1].x == 110
    assert next_state.ships[2].x == 100
    assert next_state.ships[3].x == 100
    assert [event.entity_id for event in events] == [1]


def test_explicit_eligibility_remains_supported() -> None:
    specs = _specs()
    one = _ship(1)
    two = _ship(2)

    next_state, events = HostEngine((
        NormalMovementPhase(specs=specs, eligible_ship_ids=frozenset({2})),
    )).step(
        _state(one, two),
        TurnOrders.empty(),
    )

    assert next_state.ships[1].x == 100
    assert next_state.ships[2].x == 110
    assert [event.entity_id for event in events] == [2]
