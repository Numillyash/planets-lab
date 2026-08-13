from planets_lab.core import Cargo, GameState, NativePopulation, Planet, Player
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.factory_supply_phase import FactorySupplyPhase
from planets_lab.sim.tax_collection_phase import TaxCollectionPhase


def _state(*, native_race_id: int = 7) -> GameState:
    planet = Planet(
        id=1,
        x=100,
        y=100,
        owner_id=1,
        cargo=Cargo(clans=500, supplies=10, megacredits=100),
        factories=20,
        happiness=100,
        tax_rate=10,
        natives=NativePopulation(
            race_id=native_race_id,
            clans=10_000,
            government_id=4,
            happiness=100,
            tax_rate=10,
        ),
    )
    return GameState(game_id=1, turn=1, players={1: Player(id=1)}, planets={1: planet})


def test_factory_supplies_then_taxes_update_planet_resources() -> None:
    engine = HostEngine((FactorySupplyPhase(), TaxCollectionPhase()))
    next_state, events = engine.step(_state(), TurnOrders.empty())

    planet = next_state.planets[1]
    assert planet.cargo.supplies == 30
    assert planet.cargo.megacredits == 1_100
    assert [event.kind for event in events] == ["supplies_produced", "taxes_collected"]


def test_tax_phase_supports_federation_style_double_colonist_tax() -> None:
    state = _state()
    state.planets[1].natives = None
    phase = TaxCollectionPhase(racial_modifier_by_player_id={1: 2.0})

    next_state, _ = HostEngine((phase,)).step(state, TurnOrders.empty())
    assert next_state.planets[1].cargo.megacredits == 1_100


def test_tax_phase_can_mark_native_race_as_nonpaying() -> None:
    phase = TaxCollectionPhase(untaxable_native_race_ids=frozenset({7}))
    next_state, _ = HostEngine((phase,)).step(_state(native_race_id=7), TurnOrders.empty())

    assert next_state.planets[1].cargo.megacredits == 600
