from planets_lab.core import Cargo, GameState, MineralDeposit, NativePopulation, Planet, Player
from planets_lab.sim import PLANETARY_HOST_PHASE_ORDER, PlanetaryHostPipeline, TurnOrders


def _state() -> GameState:
    return GameState(
        game_id=1,
        turn=7,
        players={1: Player(id=1, race_id=1)},
        planets={
            1: Planet(
                id=1,
                x=100,
                y=100,
                owner_id=1,
                temperature=50,
                cargo=Cargo(clans=100),
                ground_duranium=MineralDeposit(amount=1_000, density=100),
                factories=100,
                mines=100,
                defense_posts=50,
                happiness=90,
                tax_rate=0,
                natives=NativePopulation(
                    race_id=2,
                    clans=1_000,
                    government_id=8,
                    happiness=90,
                    tax_rate=0,
                ),
            )
        },
    )


def test_planetary_pipeline_uses_documented_relative_host_order() -> None:
    pipeline = PlanetaryHostPipeline()
    assert tuple(phase.name for phase in pipeline.phases) == PLANETARY_HOST_PHASE_ORDER


def test_full_planetary_pipeline_turn_is_end_to_end_deterministic() -> None:
    pipeline = PlanetaryHostPipeline()
    next_state, events = pipeline.engine().step(_state(), TurnOrders.empty(), seed=12345)

    planet = next_state.planets[1]
    assert next_state.turn == 8

    # Happiness is computed before production/taxes/growth.
    assert planet.happiness == 99
    assert planet.natives is not None
    assert planet.natives.happiness == 98

    # Factory output includes Bovinoids, then both populations grow.
    assert planet.cargo.supplies == 110
    assert planet.cargo.clans == 105
    assert planet.natives.clans == 1_040

    # Federation mines at 70%; mutation then replenishes the ground deposit.
    assert planet.cargo.duranium == 70
    assert planet.ground_duranium.amount == 935

    assert [event.kind for event in events] == [
        "colonist_happiness_changed",
        "native_happiness_changed",
        "supplies_produced",
        "colonists_grew",
        "natives_grew",
        "minerals_mined",
        "minerals_mutated",
    ]
