from copy import deepcopy

import pytest

from planets_lab.rules.combat import (
    ReplayUnsupported,
    beam_specs_from_catalog,
    combat_rng_from_settings,
    replay_nuhost_classic,
    torpedo_specs_from_catalog,
)


BEAMS = [
    {"id": 1, "name": "Laser", "kill": 10, "damage": 3},
    {"id": 2, "name": "X-Ray Laser", "kill": 15, "damage": 1},
    {"id": 3, "name": "Plasma Bolt", "kill": 3, "damage": 10},
    {"id": 4, "name": "Blaster", "kill": 10, "damage": 25},
    {"id": 5, "name": "Positron Beam", "kill": 9, "damage": 29},
    {"id": 6, "name": "Disruptor", "kill": 30, "damage": 20},
    {"id": 7, "name": "Heavy Blaster", "kill": 20, "damage": 40},
]

TORPEDOES = [
    {"id": 5, "name": "Mark 3c Photon", "kill": 9, "damage": 25, "range": 300},
    {"id": 6, "name": "Mark 4 Photon", "kill": 13, "damage": 30, "range": 300},
]


def vcr2() -> dict:
    return {
        "id": 2,
        "turn": 8,
        "seed": 49,
        "battletype": 1,
        "x": 1816,
        "y": 2175,
        "leftownerid": 4,
        "rightownerid": 3,
        "left": {
            "objectid": 20,
            "name": "ILL WIND CLASS BATTLECRUISER",
            "beamcount": 10,
            "launchercount": 2,
            "baycount": 0,
            "hullid": 37,
            "beamid": 7,
            "torpedoid": 6,
            "shield": 100,
            "damage": 0,
            "crew": 525,
            "mass": 275,
            "raceid": 4,
            "beamkillbonus": 1,
            "beamchargerate": 2,
            "torpchargerate": 1,
            "torpmisspercent": 35,
            "crewdefensepercent": 0,
            "torpedos": 5,
            "fighters": 0,
            "hasstarbase": False,
        },
        "right": {
            "objectid": 35,
            "name": "Fantasia",
            "beamcount": 0,
            "launchercount": 0,
            "baycount": 0,
            "hullid": 0,
            "beamid": 1,
            "torpedoid": 0,
            "shield": 0,
            "damage": 0,
            "crew": 10000,
            "mass": 100,
            "raceid": 3,
            "beamkillbonus": 1,
            "beamchargerate": 1,
            "torpchargerate": 1,
            "torpmisspercent": 35,
            "crewdefensepercent": 0,
            "torpedos": 0,
            "fighters": 0,
            "hasstarbase": False,
        },
    }


def vcr3() -> dict:
    return {
        "id": 3,
        "turn": 8,
        "seed": 55,
        "battletype": 1,
        "x": 1836,
        "y": 2187,
        "leftownerid": 4,
        "rightownerid": 3,
        "left": {
            "objectid": 39,
            "name": "ILL WIND CLASS BATTLECRUISER",
            "beamcount": 10,
            "launchercount": 2,
            "baycount": 0,
            "hullid": 37,
            "beamid": 7,
            "torpedoid": 5,
            "shield": 100,
            "damage": 0,
            "crew": 525,
            "mass": 275,
            "raceid": 4,
            "beamkillbonus": 1,
            "beamchargerate": 2,
            "torpchargerate": 1,
            "torpmisspercent": 35,
            "crewdefensepercent": 0,
            "torpedos": 0,
            "fighters": 0,
            "hasstarbase": False,
        },
        "right": {
            "objectid": 74,
            "name": "New Bohemia",
            "beamcount": 5,
            "launchercount": 0,
            "baycount": 9,
            "hullid": 0,
            "beamid": 7,
            "torpedoid": 0,
            "shield": 100,
            "damage": 0,
            "crew": 10000,
            "mass": 186,
            "raceid": 3,
            "beamkillbonus": 1,
            "beamchargerate": 1,
            "torpchargerate": 1,
            "torpmisspercent": 35,
            "crewdefensepercent": 0,
            "torpedos": 0,
            "fighters": 9,
            "hasstarbase": False,
        },
    }


def test_catalog_mapping_preserves_classic_weapon_values() -> None:
    beams = beam_specs_from_catalog(BEAMS)
    torpedoes = torpedo_specs_from_catalog(TORPEDOES)

    assert beams[7].damage == 40
    assert beams[7].kill == 20
    assert torpedoes[6].damage == 30
    assert torpedoes[6].kill == 13
    assert torpedoes[6].firing_range_bonus == 0


def test_vcr2_consumes_all_torpedoes_and_destroys_planet() -> None:
    result = replay_nuhost_classic(vcr2(), beams=BEAMS, torpedoes=TORPEDOES)

    assert result["engine"] == "nuhost_classic_119"
    assert result["left"]["torpedoes"] == 0
    assert result["left"]["survived"] is True
    assert "right_destroyed" in result["result"]


def test_vcr3_matches_known_classic_terminal_state() -> None:
    result = replay_nuhost_classic(vcr3(), beams=BEAMS, torpedoes=TORPEDOES)

    assert result["left"]["torpedoes"] == 0
    assert result["left"]["shield"] == 29
    assert result["left"]["damage"] == 0
    assert result["left"]["crew"] == 525
    assert result["left"]["survived"] is True
    assert result["right"]["fighters"] == 0
    assert "right_destroyed" in result["result"]


def test_replay_does_not_mutate_input_payload() -> None:
    payload = vcr2()
    before = deepcopy(payload)

    replay_nuhost_classic(payload, beams=BEAMS, torpedoes=TORPEDOES)

    assert payload == before


def test_extended_combat_rng_fails_closed() -> None:
    with pytest.raises(ReplayUnsupported):
        replay_nuhost_classic(vcr2(), beams=BEAMS, torpedoes=TORPEDOES, combat_rng=1)


def test_combat_rng_setting_parser_is_explicit() -> None:
    assert combat_rng_from_settings({"combatrng": 0}) == 0
    assert combat_rng_from_settings({"COMBAT_RNG": "1"}) == 1
    assert combat_rng_from_settings({}) is None
