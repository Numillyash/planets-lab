from __future__ import annotations

import pytest

from planets_lab.rules.combat import (
    ReplayUnsupported,
    apply_planet_carryover,
    planet_bay_count,
    planet_beam_count,
    planet_fighter_count,
    planet_native_beam_tech,
    planet_sequence_shape_supported,
    rebuild_planet_combatant,
)


def test_planet_component_formulas_use_integer_host_rounding() -> None:
    assert planet_fighter_count(0) == 0
    assert planet_fighter_count(1) == 1
    assert planet_fighter_count(25) == 5
    assert planet_bay_count(25) == 5
    assert planet_beam_count(25, 50, 0) == 5
    assert planet_beam_count(25, 50, 200) == 10


def test_planet_native_beam_tech_matches_published_capability_thresholds() -> None:
    # The Planets.nu Defense Posts page currently prints a TRUNC formula, but
    # its published capability table and historical VCRs use these ROUND
    # thresholds instead.
    assert planet_native_beam_tech(0) == 0
    assert planet_native_beam_tech(1) == 1
    assert planet_native_beam_tech(4) == 1
    assert planet_native_beam_tech(5) == 2
    assert planet_native_beam_tech(12) == 2
    assert planet_native_beam_tech(13) == 3
    assert planet_native_beam_tech(24) == 3
    assert planet_native_beam_tech(25) == 4
    assert planet_native_beam_tech(40) == 4
    assert planet_native_beam_tech(41) == 5
    assert planet_native_beam_tech(60) == 5
    assert planet_native_beam_tech(61) == 6
    assert planet_native_beam_tech(84) == 6
    assert planet_native_beam_tech(85) == 7
    assert planet_native_beam_tech(112) == 7
    assert planet_native_beam_tech(113) == 8
    assert planet_native_beam_tech(144) == 8
    assert planet_native_beam_tech(145) == 9
    assert planet_native_beam_tech(180) == 9
    assert planet_native_beam_tech(181) == 10
    assert planet_native_beam_tech(400) == 10


def test_rebuild_includes_base_mass_fighters_and_five_bays() -> None:
    rebuilt = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "has_starbase": True,
            "planet_defense": 25,
            "starbase_defense": 50,
            "starbase_fighters": 20,
            "starbase_beam_tech": 10,
            "starbase_damage": 0,
            "starbase_mass_bonus": 200,
            "beam_charge_rate": 1,
        }
    )

    assert rebuilt["mass"] == 375
    assert rebuilt["fighters"] == 25
    assert rebuilt["bay_count"] == 10
    assert rebuilt["beam_count"] == 10
    assert rebuilt["beam_id"] == 10


def test_planet_only_damage_and_fighter_losses_carry_exactly() -> None:
    start = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "has_starbase": False,
            "planet_defense": 65,
            "starbase_defense": None,
            "starbase_fighters": None,
            "starbase_beam_tech": None,
            "starbase_damage": None,
            "starbase_mass_bonus": None,
            "beam_charge_rate": 1,
        }
    )
    assert start["fighters"] == 8

    carried = apply_planet_carryover(
        start,
        start,
        {
            "shield": 0,
            "damage": 43,
            "fighters": 6,
        },
    )

    # TRUNC(65*43/100)=27 damaged DP plus two generated fighter losses.
    assert carried["planet_defense"] == 36
    assert carried["damage"] == 0
    assert carried["shield"] == 0
    assert carried["fighters"] == 6


def test_starbase_fighters_carry_when_no_hull_damage_occurred() -> None:
    start = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "has_starbase": True,
            "planet_defense": 65,
            "starbase_defense": 100,
            "starbase_fighters": 5,
            "starbase_beam_tech": 10,
            "starbase_damage": 12,
            "starbase_mass_bonus": 0,
            "beam_charge_rate": 1,
        }
    )
    assert start["fighters"] == 13

    carried = apply_planet_carryover(
        start,
        start,
        {
            "shield": 35,
            "damage": 0,
            "fighters": 6,
        },
    )

    # Seven losses consume all five base fighters before two generated
    # planetary fighters. Those generated-fighter losses remove two planet DP.
    assert carried["starbase_fighters"] == 0
    assert carried["planet_defense"] == 63
    assert carried["starbase_defense"] == 100
    assert carried["starbase_beam_tech"] == 10
    assert carried["starbase_damage"] == 12
    assert carried["shield"] == 35


def test_starbase_hull_damage_fails_closed_without_host_formula() -> None:
    start = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "has_starbase": True,
            "planet_defense": 65,
            "starbase_defense": 100,
            "starbase_fighters": 5,
            "starbase_beam_tech": 10,
            "starbase_damage": 12,
            "starbase_mass_bonus": 0,
            "beam_charge_rate": 1,
        }
    )

    with pytest.raises(ReplayUnsupported, match="exact multi-wave starbase carry-over stops"):
        apply_planet_carryover(
            start,
            start,
            {
                "shield": 0,
                "damage": 1,
                "fighters": start["fighters"],
            },
        )


def test_robot_starbase_never_gets_shielded_mass_bonus() -> None:
    rebuilt = rebuild_planet_combatant(
        {
            "hull_id": 0,
            "race_id": 9,
            "has_starbase": True,
            "planet_defense": 25,
            "starbase_defense": 50,
            "starbase_fighters": 20,
            "starbase_beam_tech": 10,
            "starbase_damage": 0,
            "starbase_mass_bonus": 200,
        }
    )

    assert rebuilt["starbase_mass_bonus"] == 0
    assert rebuilt["mass"] == 175


def test_only_ship_queue_vs_one_fixed_planet_shape_is_supported() -> None:
    ship = {"hull_id": 10}
    planet = {"hull_id": 0}

    assert planet_sequence_shape_supported((ship,), (planet,))
    assert planet_sequence_shape_supported((ship, ship), (planet,))
    assert planet_sequence_shape_supported((ship, ship), (ship, ship))
    assert not planet_sequence_shape_supported((planet,), (ship,))
    assert not planet_sequence_shape_supported((ship,), (planet, ship))
    assert not planet_sequence_shape_supported((ship,), (planet, planet))
