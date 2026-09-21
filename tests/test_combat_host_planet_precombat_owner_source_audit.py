from __future__ import annotations

from combat_host_planet_precombat_owner_source_audit import (
    _interesting_planet_fields,
    _interesting_ship_fields,
    _same_position,
)


def test_same_position_requires_exact_tminus1_coordinates() -> None:
    raw = {"x": 100, "y": 200}

    assert _same_position(raw, x=100, y=200) is True
    assert _same_position(raw, x=101, y=200) is False


def test_interesting_ship_fields_keeps_clan_and_order_context() -> None:
    raw = {
        "id": 7,
        "ownerid": 3,
        "hullid": 25,
        "x": 100,
        "y": 200,
        "clans": 42,
        "mission": 1,
        "mission1target": 99,
        "targetx": 101,
        "targety": 202,
        "friendlycode": "abc",
        "enemy": 5,
        "warp": 0,
        "name": "irrelevant display name",
    }

    fields = _interesting_ship_fields(raw)

    assert fields["clans"] == 42
    assert fields["mission"] == 1
    assert fields["mission1target"] == 99
    assert fields["targetx"] == 101
    assert fields["targety"] == 202
    assert fields["friendlycode"] == "abc"
    assert fields["enemy"] == 5
    assert fields["warp"] == 0
    assert "name" not in fields



def test_interesting_planet_fields_keeps_ground_combat_context() -> None:
    raw = {
        "id": 88,
        "ownerid": 8,
        "raceid": 8,
        "clans": 510,
        "defense": 20,
        "friendlycode": "abc",
        "mines": 100,
        "factories": 100,
    }

    fields = _interesting_planet_fields(raw)

    assert fields["ownerid"] == 8
    assert fields["raceid"] == 8
    assert fields["clans"] == 510
    assert fields["defense"] == 20
    assert fields["friendlycode"] == "abc"
    assert "mines" not in fields
    assert "factories" not in fields
