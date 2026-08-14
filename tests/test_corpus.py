import io
import json
import zipfile

import pytest

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi
from planets_lab.corpus.archive import (
    TurnMember,
    archive_members,
    inspect_turn_member,
    turn_members,
)
from planets_lab.corpus.discovery import finished_games
from planets_lab.corpus.manifest import build_game_manifest, settings_hash
from planets_lab.corpus.normalizer import (
    ArchiveTurnSnapshot,
    consecutive_archive_transitions,
    load_archive_snapshots,
    ownerless_ship_diagnostics,
    summarize_archive_snapshots,
)


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


def _turn_payload(player: int, turn: int) -> dict:
    return {
        "game": {"id": 680910, "turn": turn},
        "player": {
            "id": player,
            "raceid": player,
            "username": f"user-{player}",
            "email": f"user-{player}@example.invalid",
            "savekey": "must-not-propagate",
        },
        "players": [
            {
                "id": 1,
                "raceid": 1,
                "username": "one",
                "email": "one@example.invalid",
            },
            {
                "id": 2,
                "raceid": 2,
                "username": "two",
                "savekey": "secret-like",
            },
        ],
        "planets": [],
        "ships": [],
        "starbases": [],
        "ionstorms": [],
        "messages": [{"text": "not mechanics corpus data"}],
    }


def _loadall_fixture() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for player in (1, 2):
            for turn in (0, 1):
                archive.writestr(
                    f"player{player}-turn{turn}.trn",
                    json.dumps(_turn_payload(player, turn)),
                )
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
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("turns/example.json", "{}")
    assert archive_members(buffer.getvalue()) == ("turns/example.json",)


def test_archive_members_rejects_non_zip() -> None:
    with pytest.raises(ValueError, match="not a ZIP"):
        archive_members(b"not a zip")


def test_turn_members_parse_player_turn_grid() -> None:
    members = turn_members(_loadall_fixture())
    assert [(member.player, member.turn) for member in members] == [
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
    ]


def test_inspect_turn_member_reports_json_without_contents() -> None:
    data = _loadall_fixture()
    member = turn_members(data)[0]
    report = inspect_turn_member(data, member)
    assert report["format"] == "json"
    assert report["json_type"] == "dict"
    assert "player" in report["top_level_keys"]
    assert "must-not-propagate" not in repr(report)


def test_loadall_normalizer_builds_streams_and_drops_player_identity() -> None:
    snapshots = load_archive_snapshots(_loadall_fixture())
    assert len(snapshots) == 4
    assert {snapshot.player_id for snapshot in snapshots} == {1, 2}
    assert {snapshot.archive_turn for snapshot in snapshots} == {0, 1}

    for snapshot in snapshots:
        representation = repr(snapshot.mechanics_payload)
        assert "username" not in representation
        assert "email" not in representation
        assert "savekey" not in representation
        assert "messages" not in representation
        state = snapshot.import_state()
        assert state.game_id == 680910
        assert state.turn == snapshot.embedded_turn

    summary = summarize_archive_snapshots(snapshots)
    assert summary.snapshots == 4
    assert summary.players == (1, 2)
    assert summary.archive_turns == (0, 1)
    assert summary.missing_grid_cells == ()
    assert summary.transitions == 2
    assert summary.embedded_consecutive_transitions == 2

    transitions = consecutive_archive_transitions(snapshots)
    assert [(t.before.player_id, t.before.archive_turn, t.after.archive_turn) for t in transitions] == [
        (1, 0, 1),
        (2, 0, 1),
    ]


def test_ownerless_ship_diagnostics_are_mechanical_and_privacy_safe() -> None:
    snapshot = ArchiveTurnSnapshot(
        member=TurnMember(player=8, turn=23, name="player8-turn23.trn"),
        game_id=680910,
        player_id=8,
        embedded_turn=23,
        snapshot_hash="fixture",
        mechanics_payload={
            "ships": [
                {
                    "id": 17,
                    "ownerid": 0,
                    "hullid": 12,
                    "x": 1000,
                    "y": 1200,
                    "warp": 0,
                    "name": "must-not-print",
                    "friendlycode": "xxx",
                },
                {
                    "id": 18,
                    "ownerid": 2,
                    "hullid": 13,
                    "x": 1100,
                    "y": 1300,
                },
            ]
        },
    )

    diagnostics = ownerless_ship_diagnostics(snapshot)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["id"] == 17
    assert diagnostic["ownerid"] == 0
    assert diagnostic["hullid"] == 12
    assert diagnostic["player"] == 8
    assert "name" in diagnostic["present_keys"]
    assert "friendlycode" in diagnostic["present_keys"]
    assert "must-not-print" not in repr(diagnostic)
    assert "xxx" not in repr(diagnostic)


def test_loadall_probe_cli_imports() -> None:
    from planets_lab.corpus.probe_loadall_cli import main

    assert callable(main)


def test_loadall_inspector_cli_imports() -> None:
    from planets_lab.corpus.inspect_loadall_cli import main

    assert callable(main)


def test_loadall_normalizer_cli_imports() -> None:
    from planets_lab.corpus.normalize_loadall_cli import main

    assert callable(main)
