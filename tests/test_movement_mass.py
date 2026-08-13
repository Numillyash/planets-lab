import pytest

from planets_lab.core import Cargo, Ship
from planets_lab.data import BeamSpec, HullSpec, NuStaticSpecs, ResourceCost, TorpedoSpec
from planets_lab.rules import MovementMassError, ship_movement_mass


def _specs() -> NuStaticSpecs:
    zero_cost = ResourceCost()
    return NuStaticSpecs(
        hulls={
            1: HullSpec(
                id=1,
                name="Test Hull",
                tech_level=1,
                mass=100,
                cargo_capacity=200,
                fuel_tank=100,
                crew=50,
                engine_count=1,
                beam_count=4,
                torpedo_launcher_count=4,
                fighter_bay_count=0,
                can_cloak=False,
                cost=zero_cost,
            )
        },
        beams={
            2: BeamSpec(
                id=2,
                name="Test Beam",
                tech_level=1,
                mass=5,
                damage=1,
                crew_kill=1,
                cost=zero_cost,
            )
        },
        torpedoes={
            3: TorpedoSpec(
                id=3,
                name="Test Torpedo",
                tech_level=1,
                mass=8,
                damage=1,
                crew_kill=1,
                combat_range=1,
                launcher_cost=1,
                torpedo_cost=1,
                cost=zero_cost,
            )
        },
    )


def test_ship_movement_mass_uses_fitted_components_and_loaded_mass() -> None:
    ship = Ship(
        id=10,
        owner_id=1,
        hull_id=1,
        x=0,
        y=0,
        beam_id=2,
        torpedo_id=3,
        beam_count=2,
        torpedo_launcher_count=3,
        torpedoes=7,
        cargo=Cargo(
            neutronium=20,
            supplies=4,
            clans=3,
            duranium=2,
            tritanium=1,
            molybdenum=5,
            megacredits=999,
        ),
    )

    # Hull 100 + beams 2*5 + tubes 3*8 + torpedoes 7 + loaded mass 35.
    assert ship_movement_mass(ship, _specs()) == 176


def test_ship_movement_mass_counts_fighters_as_mass() -> None:
    ship = Ship(
        id=11,
        owner_id=1,
        hull_id=1,
        x=0,
        y=0,
        fighters=12,
        cargo=Cargo(neutronium=8),
    )

    assert ship_movement_mass(ship, _specs()) == 120


def test_ship_movement_mass_rejects_unresolved_ammo() -> None:
    ship = Ship(
        id=12,
        owner_id=1,
        hull_id=1,
        x=0,
        y=0,
        unresolved_ammo=5,
    )

    with pytest.raises(MovementMassError, match="unresolved ammo"):
        ship_movement_mass(ship, _specs())


def test_ship_movement_mass_requires_component_specs_for_fitted_weapons() -> None:
    ship = Ship(
        id=13,
        owner_id=1,
        hull_id=1,
        x=0,
        y=0,
        beam_count=1,
    )

    with pytest.raises(MovementMassError, match="no beam component id"):
        ship_movement_mass(ship, _specs())
