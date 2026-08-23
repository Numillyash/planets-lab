from __future__ import annotations

from planets_lab.corpus.manifest import (
    MANIFEST_SCHEMA,
    build_game_manifest,
    sanitize_manifest_record,
)


def test_game_metadata_is_allowlisted_in_generated_manifest() -> None:
    manifest = build_game_manifest(
        {"id": 20, "status": 3},
        {
            "game": {
                "id": 20,
                "name": "Fixture Game",
                "status": 3,
                "statusname": "Finished",
                "turn": 88,
                "dateended": "2026-08-01T00:00:00",
                "gametype": 2,
                "iscustom": False,
                "isprivate": False,
                "password": "must-not-propagate",
                "email": "must-not-propagate@example.invalid",
                "savekey": "must-not-propagate",
                "future_secret_field": "must-not-propagate",
            },
            "settings": {"nuionstorms": True},
            "players": [
                {
                    "id": 4,
                    "raceid": 7,
                    "username": "public-name",
                    "accountid": 123,
                    "turnjoined": 1,
                }
            ],
        },
    )

    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["game"] == {
        "id": 20,
        "name": "Fixture Game",
        "status": 3,
        "statusname": "Finished",
        "turn": 88,
        "dateended": "2026-08-01T00:00:00",
        "gametype": 2,
        "iscustom": False,
        "isprivate": False,
    }
    assert manifest["player_slots"] == [{"id": 4, "raceid": 7, "turnjoined": 1}]

    representation = repr(manifest)
    assert "must-not-propagate" not in representation
    assert "username" not in representation
    assert "accountid" not in representation
    assert "future_secret_field" not in representation


def test_existing_v1_manifest_can_be_sanitized_offline() -> None:
    migrated = sanitize_manifest_record(
        {
            "schema": "planets-lab.corpus-game.v1",
            "game_id": 20,
            "tier": "B",
            "settings_hash": "stale-hash-is-recomputed",
            "game": {
                "id": 20,
                "turn": 88,
                "dateended": "2026-08-01T00:00:00",
                "gametype": 2,
                "iscustom": False,
                "isprivate": False,
                "password": "must-not-propagate",
            },
            "settings": {"nuionstorms": False, "foo": 1},
            "player_slots": [
                {
                    "id": 4,
                    "raceid": 7,
                    "turnjoined": 1,
                    "username": "must-not-propagate",
                }
            ],
        }
    )

    assert migrated["schema"] == MANIFEST_SCHEMA
    assert "password" not in migrated["game"]
    assert migrated["player_slots"] == [{"id": 4, "raceid": 7, "turnjoined": 1}]
    assert migrated["settings"] == {"nuionstorms": False, "foo": 1}
    assert migrated["settings_hash"] != "stale-hash-is-recomputed"
