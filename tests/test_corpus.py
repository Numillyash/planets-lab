import gzip
import io
import json
import zipfile

import pytest

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi
from planets_lab.corpus.archive import (
    archive_members,
    inspect_turn_member,
    turn_members,
)
from planets_lab.corpus.discovery import finished_games
from planets_lab.corpus.manifest import build_game_manifest, settings_hash


class FakeClient:
    def account_history(self, account_id: int):
        if account_id == 10:
            return [
                {
                    "gameid": 20,
                    "game": {
                        "id": 20,
                        "status": 3,
                        "statusname": "Finished",
                        "dateended": "2026-07-01T00:00:00",
                    },
                    "player": {"id": 4, "raceid": 7},
                },
                {
                    "gameid": 21,
                    "game": {
                        "id": 21,
                        "status": 2,
                        "statusname": "Running",
                        "dateended": "0001-01-01T00:00:00",
                    },
                },
            ]
        return [
            {
                "gameid": 20,
                "game": {
                    "id": 20,
                    "status": 3,
                    "statusname": "Finished",
                    "dateended": "2026-07-01T00:00:00",
                },
            },
            {
                "gameid": 22,
                "game": {
                    "id": 22,
                    "status": 3,
                    "statusname": "Finished",
                    "dateended": "2026-08-01T00:00:00",
                },
            },
        ]


def _zip_bytes(files: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def test_network_client_requires_proxy(monkeypatch) -> None:
    monkeypatch.delenv("PLANETSNU_PROXY_URL", raising=False)
    with pytest.raises(CorpusApiError, match="PLANETSNU_PROXY_URL"):
        PlanetsNuPublicApi()


def test_finished_game_discovery_uses_history_filters_and_deduplicates() -> None:
    games = finished_games(FakeClient(), [10, 11])
    assert [game["id"] for game in games] == [22, 20]
    assert all(game["status"] == 3 for game in games)


def test_manifest_keeps_race_slots_but_not_identity() -> None:
    manifest = build_game_manifest(
        {"id": 20, "status": 3},
        {
            "game": {"id": 20, "turn": 88},
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
    assert manifest["player_slots"] == [{"id": 4, "raceid": 7, "turnjoined": 1}]
    assert "username" not in repr(manifest)
    assert "accountid" not in repr(manifest)


def test_settings_hash_is_key_order_independent() -> None:
    assert settings_hash({"a": 1, "b": 2}) == settings_hash({"b": 2, "a": 1})


def test_archive_members_validates_zip() -> None:
    data = _zip_bytes({"turns/example.json": "{}"})
    assert archive_members(data) == ("turns/example.json",)


def test_archive_members_rejects_non_zip() -> None:
    with pytest.raises(ValueError, match="not a ZIP"):
        archive_members(b"not a zip")


def test_turn_members_parse_player_turn_grid() -> None:
    data = _zip_bytes(
        {
            "player2-turn1.trn": "{}",
            "player1-turn0.trn": "{}",
            "notes.txt": "ignored",
        }
    )
    members = turn_members(data)
    assert [(m.player, m.turn, m.name) for m in members] == [
        (1, 0, "player1-turn0.trn"),
        (2, 1, "player2-turn1.trn"),
    ]


def test_inspect_turn_member_detects_plain_json() -> None:
    payload = {"game": {"id": 20}, "ships": [{"id": 1}], "planets": []}
    data = _zip_bytes({"player1-turn0.trn": json.dumps(payload)})
    report = inspect_turn_member(data, "player1-turn0.trn")
    assert report["format"] == "json"
    assert report["transport"] == "plain"
    assert report["top_level_keys"] == ["game", "planets", "ships"]
    assert report["top_level_shapes"]["ships"] == {"type": "list", "len": 1}


def test_inspect_turn_member_detects_gzip_json() -> None:
    payload = json.dumps({"game": {"id": 20}}).encode()
    data = _zip_bytes({"player1-turn0.trn": gzip.compress(payload)})
    report = inspect_turn_member(data, "player1-turn0.trn")
    assert report["format"] == "json"
    assert report["transport"] == "gzip"
    assert report["top_level_keys"] == ["game"]


def test_loadall_probe_cli_imports() -> None:
    from planets_lab.corpus.probe_loadall_cli import main

    assert callable(main)


def test_loadall_inspector_cli_imports() -> None:
    from planets_lab.corpus.inspect_loadall_cli import main

    assert callable(main)
