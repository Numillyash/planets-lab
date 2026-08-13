from planets_lab.core import Cargo, GameState, MineralDeposit, Planet, Player
from planets_lab.rules.mining import mined_amount, trans_uranium_mutation_amount
from planets_lab.sim import HostEngine, TurnOrders
from planets_lab.sim.mineral_phases import MineralMiningPhase, TransUraniumMutationPhase


def test_mining_rates_and_ground_cap() -> None:
    assert mined_amount(mines=100, density=50, ground_amount=1_000) == 50
    assert mined_amount(mines=100, density=50, ground_amount=1_000, mining_rate_percent=70) == 35
    assert mined_amount(mines=100, density=50, ground_amount=1_000, mining_rate_percent=200) == 100
    assert mined_amount(mines=100, density=50, ground_amount=20) == 20
    assert mined_amount(mines=100, density=50, ground_amount=1_000, output_modifier_percent=50) == 25


def test_default_trans_uranium_density_bins() -> None:
    expected = {0: 0, 10: 1, 20: 1, 21: 2, 40: 2, 41: 3, 60: 3, 61: 4, 80: 4, 81: 5, 100: 5}
    for density, amount in expected.items():
        assert trans_uranium_mutation_amount(density=density) == amount


def test_mining_then_mutation_updates_surface_and_ground() -> None:
    planet = Planet(
        id=1,
        x=100,
        y=100,
        owner_id=1,
        cargo=Cargo(),
        mines=100,
        ground_neutronium=MineralDeposit(amount=1_000, density=50),
        ground_duranium=MineralDeposit(amount=1_000, density=20),
        ground_tritanium=MineralDeposit(amount=1_000, density=80),
        ground_molybdenum=MineralDeposit(amount=1_000, density=100),
    )
    state = GameState(
        game_id=1,
        turn=1,
        players={1: Player(id=1, race_id=1)},
        planets={1: planet},
    )

    next_state, events = HostEngine((MineralMiningPhase(), TransUraniumMutationPhase())).step(
        state, TurnOrders.empty()
    )
    result = next_state.planets[1]

    assert result.cargo.neutronium == 35
    assert result.cargo.duranium == 14
    assert result.cargo.tritanium == 56
    assert result.cargo.molybdenum == 70
    assert result.ground_neutronium.amount == 968
    assert result.ground_duranium.amount == 987
    assert result.ground_tritanium.amount == 948
    assert result.ground_molybdenum.amount == 935
    assert [event.kind for event in events] == ["minerals_mined", "minerals_mutated"]
