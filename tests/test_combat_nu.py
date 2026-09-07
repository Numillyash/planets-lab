from __future__ import annotations

import pytest

from planets_lab.rules.combat import (
    ReplayUnsupported,
    normalize_nu_beams,
    normalize_nu_torpedoes,
    replay_nuhost_classic,
    replay_nuhost_from_nu_catalog,
)
from planets_lab.rules.combat import nu as nu_rules


BEAMS = [
    {"id": 1, "name": "Laser", "crewkill": 10, "damage": 3},
    {"id": 2, "name": "X-Ray Laser", "crewkill": 15, "damage": 1},
    {"id": 3, "name": "Plasma Bolt", "crewkill": 3, "damage": 10},
    {"id": 4, "name": "Blaster", "crewkill": 10, "damage": 25},
    {"id": 5, "name": "Positron Beam", "crewkill": 9, "damage": 29},
    {"id": 6, "name": "Disruptor", "crewkill": 30, "damage": 20},
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


def _combat_object(**overrides: object) -> nu_rules.CombatObject:
    values: dict[str, object] = {
        "object_id": 1,
        "owner_id": 1,
        "name": "test ship",
        "beam_count": 0,
        "launcher_count": 0,
        "bay_count": 0,
        "hull_id": 1,
        "beam_id": 0,
        "torpedo_id": 0,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "mass": 79,
        "race_id": 1,
        "beam_kill_rate": 1,
        "beam_charge_rate": 1,
        "torp_charge_rate": 1,
        "torp_miss_rate": 35,
        "crew_defense_rate": 0,
        "torpedoes": 0,
        "fighters": 0,
        "is_planet": False,
    }
    values.update(overrides)
    return nu_rules.CombatObject(**values)  # type: ignore[arg-type]


def _direct_nu_replay(victim: nu_rules.CombatObject) -> nu_rules._NuSignedClassicReplay:
    opponent = _combat_object(object_id=2, owner_id=2, name="opponent")
    return nu_rules._NuSignedClassicReplay(
        seed=1,
        left=victim,
        right=opponent,
        beams={},
        torpedoes={},
    )


def test_normalize_nu_weapon_fields() -> None:
    assert normalize_nu_beams(BEAMS)[-1] == {
        "id": 7,
        "damage": 40,
        "kill": 20,
    }
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


def test_signed_cpp_division_matches_c2ng_semantics() -> None:
    assert nu_rules._cpp_divmod(151, 100) == (1, 51)
    assert nu_rules._cpp_divmod(-151, 100) == (-1, -51)
    assert nu_rules._NuSignedClassicReplay._divide_and_round(-151, 100) == -1
    assert nu_rules._NuSignedClassicReplay._divide_and_round(-50, 100) == 0
    assert nu_rules._NuSignedClassicReplay._rdivadd(-151, 100, -10) == -11


def test_exact_shield_depletion_does_not_damage_crew_on_same_hit() -> None:
    replay = _direct_nu_replay(_combat_object(shield=11, crew=100, mass=79))

    replay._hit(replay.status[0], damage=10, kill=10)

    assert replay.status[0].obj.shield == 0
    assert replay.status[0].obj.damage == 0
    assert replay.status[0].obj.crew == 100


def test_penetrating_shield_hit_still_damages_crew_immediately() -> None:
    replay = _direct_nu_replay(_combat_object(shield=10, crew=100, mass=79))

    replay._hit(replay.status[0], damage=10, kill=10)

    assert replay.status[0].obj.shield == 0
    assert replay.status[0].obj.damage == 2
    assert replay.status[0].obj.crew == 90


def test_nu_adapter_accepts_crew_defense_above_100() -> None:
    payload = _vcr()
    left = payload["left"]
    assert isinstance(left, dict)
    left["shield"] = 0
    left["crewdefensepercent"] = 150

    result = replay_nuhost_from_nu_catalog(
        payload,
        beams=BEAMS,
        torpedoes=TORPEDOES,
        settings={"combatrng": 0},
    )

    assert result["engine"] == "nuhost_classic_119"
    assert result["left"]["crew"] >= 525


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
