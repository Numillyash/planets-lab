from planets_lab.core import Cargo, GameState, NativePopulation, Planet, Player
from planets_lab.rules.population import cyborg_assimilation
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.cyborg_assimilation_phase import CyborgAssimilationPhase


def test_cyborg_population_conversion_rate() -> None:
    assert cyborg_assimilation(
        colonist_clans=500,
        native_clans=1_000,
        native_race_id=1,
    ) == 500
    assert cyborg_assimilation(
        colonist_clans=500,
        native_clans=1_000,
        native_race_id=5,
    ) == 0


def test_cyborg_population_phase_updates_planet() -> None:
    state = GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1, race_id=6)},
        planets={1: Planet(
            id=1,
            x=100,
            y=100,
            owner_id=1,
            cargo=Cargo(clans=500),
            natives=NativePopulation(race_id=1, clans=1_000, government_id=4),
        )},
    )
    next_state, events = HostEngine((CyborgAssimilationPhase(),)).step(
        state, TurnOrders.empty()
    )
    assert next_state.planets[1].cargo.clans == 1_000
    assert next_state.planets[1].natives is not None
    assert next_state.planets[1].natives.clans == 500
    assert len(events) == 1
