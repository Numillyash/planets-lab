from __future__ import annotations

import pytest

from planets_lab.rules.combat import (
    ReplayUnsupported,
    normalize_nu_beams,
    normalize_nu_torpedoes,
    replay_nuhost_classic,
    replay_nuhost_from_nu_catalog,
)


BEAMS = [
    {"id": 7, "name": "Heavy Blaster", "crewkill": 20, "damage": 40},
]
TORPEDOES = [
    {
        "id": 6,
        "name": "Mark 4 Photon",
        "crewkill": 13,
        "damage": 30,
        "combatrange": 300,
    },
    {
        "id": 11,
        "name": "Nu long-range torpedo",
        "crewkill": 1,
        "damage": 1,
        "combatrange": 0,
    },
]


def _vcr() -> dict[str, object]:
    return {
        "id": 2,
        "turn": 8,
        "seed": 49,
        "battletype": 1,
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
            "beamid": 7,
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


def test_normalize_nu_weapon_fields() -> None:
    assert normalize_nu_beams(BEAMS) == [
        {"id": 7, "damage": 40, "kill": 20},
    ]
    assert normalize_nu_torpedoes(TORPEDOES) == [
        {"id": 6, "damage": 30, "kill": 13, "firingrangebonus": 0},
        {"id": 11, "damage": 1, "kill": 1, "firingrangebonus": 40},
    ]


def test_explicit_combat_range_is_relative_to_300() -> None:
    mapped = normalize_nu_torpedoes(
        [{"id": 5, "damage": 25, "crewkill": 9, "combatrange": 340}]
    )
    assert mapped[0]["firingrangebonus"] == 40


def test_missing_combat_rng_fails_closed() -> None:
    with pytest.raises(ReplayUnsupported, match="does not contain combatrng"):
        replay_nuhost_from_nu_catalog(
            _vcr(), beams=BEAMS, torpedoes=TORPEDOES, settings={}
        )


def test_extended_combat_rng_fails_closed() -> None:
    with pytest.raises(ReplayUnsupported, match="combat RNG mode 1"):
        replay_nuhost_from_nu_catalog(
            _vcr(),
            beams=BEAMS,
            torpedoes=TORPEDOES,
            settings={"combatrng": 1},
        )


def test_nu_adapter_matches_direct_normalized_core() -> None:
    via_adapter = replay_nuhost_from_nu_catalog(
        _vcr(),
        beams=BEAMS,
        torpedoes=TORPEDOES,
        settings={"combatrng": 0},
    )
    direct = replay_nuhost_classic(
        _vcr(),
        beams=normalize_nu_beams(BEAMS),
        torpedoes=normalize_nu_torpedoes(TORPEDOES),
        combat_rng=0,
    )
    assert via_adapter == direct
    assert via_adapter["left"]["torpedoes"] == 0
    assert via_adapter["left"]["survived"] is True
    assert "right_destroyed" in via_adapter["result"]
