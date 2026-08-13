from planets_lab.validation.real_game import SCHEMA_V1, SCHEMA_V2, parse_record


def _record(schema: str) -> dict:
    return {
        "schema": schema,
        "game_id": 680933,
        "turn": 33,
        "batch_id": 99,
        "observer_planets_account_id": 10,
        "source_player_slot_id": 2,
        "source": "planets.nu/loadturn",
        "snapshot_hash": "schema-test",
        "players": [{"id": 2, "raceid": 2}],
        "planets": [],
        "ships": [],
        "starbases": [],
    }


def test_v1_remains_compatible_without_ionstorms() -> None:
    batch = parse_record(_record(SCHEMA_V1))
    assert batch.ionstorms == ()


def test_v2_exposes_ionstorms() -> None:
    raw = _record(SCHEMA_V2)
    raw["ionstorms"] = [
        {
            "id": 7,
            "x": 1800,
            "y": 1800,
            "radius": 100,
            "voltage": 160,
            "warp": 6,
            "heading": 347,
            "isgrowing": True,
        }
    ]
    batch = parse_record(raw)
    assert len(batch.ionstorms) == 1
    assert batch.ionstorms[0]["id"] == 7
    assert batch.ionstorms[0]["heading"] == 347
