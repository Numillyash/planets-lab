import pytest

from planets_lab.data import NuLoadTurnError, import_loadturn


def test_import_loadturn_maps_unambiguous_core_fields() -> None:
    payload = {
        "rst": {
            "game": {"id": 42, "turn": 17},
            "player": {"id": 1, "username": "Alpha", "raceid": 3},
            "planets": [
                {
                    "id": 10,
                    "x": 1000,
                    "y": 1000,
                    "ownerid": 1,
                    "neutronium": 50,
                    "duranium": 20,
                    "tritanium": 30,
                    "molybdenum": 40,
                    "supplies": 100,
                    "clans": 500,
                    "megacredits": 900,
                    "groundneutronium": 1000,
                    "densityneutronium": 50,
                    "factories": 20,
                    "mines": 30,
                    "defense": 5,
                }
            ],
            "ships": [
                {
                    "id": 101,
                    "ownerid": 1,
                    "hullid": 12,
                    "engineid": 9,
                    "beamid": 4,
                    "torpedoid": 5,
                    "x": 1000,
                    "y": 1000,
                    "targetx": 1081,
                    "targety": 1000,
                    "warp": 9,
                    "friendlycode": "abc",
                    "neutronium": 120,
                    "damage": 7,
                    "ammo": 99,
                }
            ],
            "starbases": [
                {
                    "id": 501,
                    "planetid": 10,
                    "defense": 50,
                    "fighters": 20,
                    "hulltechlevel": 10,
                    "enginetechlevel": 9,
                    "beamtechlevel": 8,
                    "torptechlevel": 7,
                }
            ],
        },
    }

    state = import_loadturn(payload)

    assert state.game_id == 42
    assert state.turn == 17
    assert state.players[1].name == "Alpha"
    assert state.planets[10].cargo.megacredits == 900
    assert state.planets[10].ground_neutronium.amount == 1000
    assert state.ships[101].waypoint_x == 1081
    assert state.ships[101].warp == 9
    assert state.ships[101].cargo.neutronium == 120
    assert state.ships[101].fighters == 0
    assert state.ships[101].torpedoes == 0
    assert state.starbases[10].owner_id == 1
    assert state.starbases[10].tech_torpedo == 7


def test_import_loadturn_creates_owner_stub_if_player_records_are_absent() -> None:
    state = import_loadturn(
        {
            "rst": {
                "planets": [],
                "ships": [{"id": 1, "ownerid": 4, "hullid": 2, "x": 1, "y": 2}],
                "starbases": [],
            }
        },
        game_id=9,
        turn=3,
    )

    assert state.players[4].id == 4


def test_import_loadturn_rejects_starbase_without_owner_or_owned_planet() -> None:
    with pytest.raises(NuLoadTurnError, match="no resolvable owner"):
        import_loadturn(
            {
                "rst": {
                    "game": {"id": 9, "turn": 3},
                    "planets": [{"id": 10, "x": 1, "y": 1, "ownerid": 0}],
                    "ships": [],
                    "starbases": [{"id": 20, "planetid": 10}],
                }
            }
        )


def test_import_loadturn_requires_rst_object() -> None:
    with pytest.raises(NuLoadTurnError, match="payload.rst"):
        import_loadturn({}, game_id=1, turn=1)
