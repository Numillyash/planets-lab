import io
import json
import zipfile

from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_residual_profile import extract_hull_catalog, profile_residual_hulls
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(turn: int, *, x: int, y: int) -> ArchiveTurnSnapshot:
    ship = {
        "id": 10,
        "ownerid": 1,
        "hullid": 17,
        "x": x,
        "y": y,
        "warp": 0,
        "targetx": 100,
        "targety": 100,
        "mission": 0,
        "friendlycode": "abc",
        "infoturn": turn,
    }
    return ArchiveTurnSnapshot(
        member=TurnMember(player=1, turn=turn, name=f"player1-turn{turn}.trn"),
        game_id=7,
        player_id=1,
        embedded_turn=turn,
        snapshot_hash=str(turn),
        mechanics_payload={
            "game": {"id": 7, "turn": turn},
            "player": {"id": 1},
            "players": [{"id": 1}],
            "ships": [ship],
            "planets": [],
            "starbases": [],
            "ionstorms": [],
            "minefields": [],
        },
    )


def test_profiles_warp_zero_external_move_by_hull() -> None:
    profile = profile_residual_hulls(
        (
            _snapshot(10, x=100, y=100),
            _snapshot(11, x=110, y=100),
        )
    )
    assert profile["residual_unresolved"] == 1
    assert profile["category_hull_counts"] == {"warp_zero_external_move|17": 1}


def _archive_payload(turn: int) -> dict:
    return {
        "game": {"id": 7, "turn": turn},
        "player": {"id": 1},
        "players": [{"id": 1}],
        "hulls": [
            {
                "id": 17,
                "name": "Test Hull",
                "mass": 100,
                "cargo": 200,
                "fueltank": 300,
                "advantages": [5],
            }
        ],
        "advantages": [{"id": 5, "name": "Test Ability"}],
    }


def test_extract_hull_catalog_compares_first_and_last_turn() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("player1-turn0.trn", json.dumps(_archive_payload(0)))
        archive.writestr("player1-turn1.trn", json.dumps(_archive_payload(1)))

    catalog = extract_hull_catalog(buffer.getvalue())
    assert catalog.consistent is True
    assert catalog.first_hash == catalog.last_hash
    assert catalog.hulls[17]["name"] == "Test Hull"
    assert catalog.hulls[17]["advantage_ids"] == [5]
    assert catalog.hulls[17]["advantage_names"] == ["Test Ability"]


def test_residual_profile_cli_imports() -> None:
    from planets_lab.corpus.movement_residual_profile_cli import main

    assert callable(main)
