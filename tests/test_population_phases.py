import pytest

from planets_lab.core import Cargo, GameState, Planet, Player
from planets_lab.data import import_loadturn
from planets_lab.rules.population import (
    colonist_growth_for_race,
    colonist_happiness_after_turn,
    colonist_max_population_for_race,
    ordinary_colonist_growth,
    ordinary_colonist_max_population,
    overpopulation_loss,
)
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.population_phases import (
    ColonistGrowthPhase,
    ColonistHappinessPhase,
    ColonistOverpopulationPhase,
    UnsupportedPopulationRule,
)


def _state(*, race_id: int = 1, temperature: int = 50, clans: int = 1_000) -> GameState:
    return GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1, race_id=race_id)},
        planets={
            1: Planet(
                id=1,
                x=100,
                y=100,
                owner_id=1,
                temperature=temperature,
                cargo=Cargo(clans=clans),
                happiness=80,
                tax_rate=0,
                factories=20,
                mines=20,
            )
        },
    )


def test_loadturn_imports_planet_temperature() -> None:
    state = import_loadturn(
        {
            "rst": {
                "game": {"id": 1, "turn": 2},
                "player": {"id": 1, "raceid": 1},
                "planets": [{"id": 7, "x": 10, "y": 20, "ownerid": 1, "temp": 73}],
            }
        }
    )
    assert state.planets[7].temperature == 73


def test_documented_happiness_and_growth_primitives() -> None:
    assert colonist_happiness_after_turn(
        old_happiness=80,
        colonist_clans=1_000,
        tax_rate=0,
        temperature=50,
        factories=20,
        mines=20,
    ) == 89
    assert ordinary_colonist_max_population(50) == 100_000
    assert ordinary_colonist_growth(
        colonist_clans=1_000,
        tax_rate=0,
        happiness=100,
        temperature=50,
    ) == 50


def test_happiness_then_growth_uses_updated_happiness() -> None:
    state = _state()
    engine = HostEngine((ColonistHappinessPhase(), ColonistGrowthPhase()))
    next_state, events = engine.step(state, TurnOrders.empty())
    planet = next_state.planets[1]
    assert planet.happiness == 89
    assert planet.cargo.clans == 1_050
    assert [event.kind for event in events] == [
        "colonist_happiness_changed",
        "colonists_grew",
    ]


def test_growth_stops_below_70_happiness() -> None:
    state = _state()
    state.planets[1].happiness = 69
    next_state, events = HostEngine((ColonistGrowthPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].cargo.clans == 1_000
    assert events == ()


def test_overpopulation_kills_only_unsupported_excess() -> None:
    maximum = ordinary_colonist_max_population(90)
    assert maximum == 209
    assert overpopulation_loss(
        colonist_clans=500,
        maximum_population=maximum,
        supplies=0,
    ) == (30, 0)
    state = _state(temperature=90, clans=500)
    next_state, events = HostEngine((ColonistOverpopulationPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].cargo.clans == 470
    assert events[0].kind == "colonists_lost_to_overpopulation"


def test_crystals_use_hot_base_temperature_and_desert_capacity() -> None:
    state = _state(race_id=7, temperature=100, clans=1_000)
    next_state, _ = HostEngine((ColonistHappinessPhase(),)).step(state, TurnOrders.empty())
    assert next_state.planets[1].happiness == 89
    assert colonist_max_population_for_race(7, 100) == 100_000
    assert colonist_growth_for_race(
        race_id=7,
        colonist_clans=1_000,
        tax_rate=0,
        happiness=100,
        temperature=100,
    ) == 50


def test_fury_robots_and_colonies_keep_hot_outpost_capacity() -> None:
    for race_id in (4, 9, 11):
        assert colonist_max_population_for_race(race_id, 100) == 60


def test_rebels_keep_arctic_colony_capacity() -> None:
    assert colonist_max_population_for_race(10, 19) == 90_000
    assert colonist_max_population_for_race(10, 100) == 60


def test_unknown_race_still_fails_closed() -> None:
    state = _state(race_id=12)
    with pytest.raises(UnsupportedPopulationRule):
        HostEngine((ColonistGrowthPhase(),)).step(state, TurnOrders.empty())
