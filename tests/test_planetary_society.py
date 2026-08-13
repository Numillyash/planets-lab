from planets_lab.core import Cargo, GameState, NativePopulation, Planet, Player
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.factory_supply_phase import FactorySupplyPhase
from planets_lab.sim.society_phases import (
    AmorphousConsumptionPhase,
    CivilWarPhase,
    NativeGrowthPhase,
    NativeHappinessPhase,
    RiotsPhase,
    StructureDecayPhase,
)


def _state(
    *,
    clans: int = 1_000,
    happiness: int = 80,
    natives: NativePopulation | None = None,
    factories: int = 20,
    mines: int = 20,
    defense: int = 20,
    temperature: int = 50,
) -> GameState:
    return GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1, race_id=1)},
        planets={
            1: Planet(
                id=1,
                x=100,
                y=100,
                owner_id=1,
                temperature=temperature,
                cargo=Cargo(clans=clans),
                factories=factories,
                mines=mines,
                defense_posts=defense,
                happiness=happiness,
                natives=natives,
            )
        },
    )


def test_structure_decay_precedes_factory_output() -> None:
    state = _state(clans=1, factories=10, mines=10, defense=10)
    next_state, events = HostEngine((StructureDecayPhase(), FactorySupplyPhase())).step(
        state, TurnOrders.empty()
    )
    planet = next_state.planets[1]
    assert (planet.factories, planet.mines, planet.defense_posts) == (7, 7, 7)
    assert planet.cargo.supplies == 7
    assert [event.kind for event in events] == ["structures_decayed", "supplies_produced"]


def test_avian_native_happiness_bonus_is_applied() -> None:
    ordinary = _state(
        natives=NativePopulation(race_id=1, clans=1_000, government_id=8, happiness=50)
    )
    avian = _state(
        natives=NativePopulation(race_id=4, clans=1_000, government_id=8, happiness=50)
    )
    ordinary_state, _ = HostEngine((NativeHappinessPhase(),)).step(
        ordinary, TurnOrders.empty()
    )
    avian_state, _ = HostEngine((NativeHappinessPhase(),)).step(avian, TurnOrders.empty())
    assert ordinary_state.planets[1].natives.happiness == 58
    assert avian_state.planets[1].natives.happiness == 68


def test_native_growth_requires_colonization_and_supports_siliconoids() -> None:
    state = _state(
        temperature=100,
        natives=NativePopulation(race_id=9, clans=1_000, government_id=4, happiness=100),
    )
    next_state, events = HostEngine((NativeGrowthPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].natives.clans == 1_040
    assert events[0].kind == "natives_grew"

    uncolonized = _state(
        clans=0,
        temperature=100,
        natives=NativePopulation(race_id=9, clans=1_000, government_id=4, happiness=100),
    )
    uncolonized.planets[1].owner_id = None
    stopped, stopped_events = HostEngine((NativeGrowthPhase(),)).step(
        uncolonized, TurnOrders.empty()
    )
    assert stopped.planets[1].natives.clans == 1_000
    assert stopped_events == ()


def test_amorphous_consumption_uses_end_happiness() -> None:
    state = _state(
        clans=100,
        natives=NativePopulation(race_id=5, clans=1_000, government_id=0, happiness=80),
    )
    next_state, events = HostEngine((AmorphousConsumptionPhase(),)).step(
        state, TurnOrders.empty()
    )
    assert next_state.planets[1].cargo.clans == 85
    assert events[0].kind == "colonists_eaten_by_amorphous"


def test_colonist_and_native_riots_stack_structure_damage() -> None:
    state = _state(
        happiness=39,
        factories=50,
        mines=50,
        natives=NativePopulation(race_id=1, clans=1_000, government_id=4, happiness=39),
    )
    next_state, events = HostEngine((RiotsPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].factories == 39
    assert next_state.planets[1].mines == 35
    assert events[0].kind == "riots_destroyed_structures"


def test_both_civil_wars_apply_population_loss_once_by_default() -> None:
    state = _state(
        clans=1_000,
        happiness=-1,
        factories=50,
        mines=50,
        natives=NativePopulation(race_id=1, clans=2_000, government_id=4, happiness=-1),
    )
    next_state, events = HostEngine((CivilWarPhase(),)).step(state, TurnOrders.empty())
    planet = next_state.planets[1]
    assert planet.cargo.clans == 600
    assert planet.natives.clans == 1_300
    assert planet.factories == 34
    assert planet.mines == 30
    assert dict(events[0].details)["population_applications"] == "1"


def test_amorphous_natives_are_immune_to_civil_war_population_loss() -> None:
    state = _state(
        clans=1_000,
        happiness=-1,
        natives=NativePopulation(race_id=5, clans=2_000, government_id=4, happiness=-1),
    )
    next_state, _ = HostEngine((CivilWarPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].cargo.clans == 600
    assert next_state.planets[1].natives.clans == 2_000
