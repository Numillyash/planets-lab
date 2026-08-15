import io
import json
import zipfile

from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_warp_well_audit import (
    audit_movement_warp_wells,
    extract_nowarpwells,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(turn: int, *, ship_x: int, debrisdisk: int) -> ArchiveTurnSnapshot:
    ship = {
        "id": 10,
        "ownerid": 1,
        "hullid": 3,
        "x": ship_x,
        "y": 100,
        "warp": 5,
        "targetx": 122,
        "targety": 100,
        "mission": 0,
        "friendlycode": "abc",
        "infoturn": turn,
    }
    planet = {
        "id": 5,
        "ownerid": 0,
        "x": 120,
        "y": 100,
        "debrisdisk": debrisdisk,
        "infoturn": turn,
    }
    return ArchiveTurnSnapshot(
        member=TurnMember(player=1, turn=turn, name=f"player1-turn{turn}.trn"),
        game_id=7,
        player_id=1,
        embedded_turn=turn,
        snapshot_hash=str(turn),
        mechanics_payload={
            "planets": [planet],
            "ships": [ship],
            "starbases": [],
        },
    )


def _archive(nowarpwells: bool) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for turn in (10, 11):
            archive.writestr(
                f"player1-turn{turn}.trn",
                json.dumps(
                    {
                        "game": {"id": 7, "turn": turn},
                        "player": {"id": 1, "raceid": 1},
                        "players": [{"id": 1, "raceid": 1}],
                        "settings": {"nowarpwells": nowarpwells},
                        "planets": [],
                        "ships": [],
                        "starbases": [],
                    }
                ),
            )
    return buffer.getvalue()


def test_extract_nowarpwells_requires_stable_setting() -> None:
    assert extract_nowarpwells(_archive(False)) == (False, "enabled")
    assert extract_nowarpwells(_archive(True)) == (True, "disabled")


def test_planetoid_warp_well_match_is_flagged_invalid() -> None:
    summary = audit_movement_warp_wells(
        (
            _snapshot(10, ship_x=100, debrisdisk=1),
            _snapshot(11, ship_x=120, debrisdisk=1),
        ),
        nowarpwells=False,
    )
    assert summary.warp_well_matches == 1
    assert summary.valid_ordinary_planet_matches == 0
    assert summary.invalid_debris_planet_matches == 1
    assert summary.disabled_warp_well_matches == 0
    assert summary.unknown_context_matches == 0


def test_disabled_warp_well_match_is_flagged_invalid() -> None:
    summary = audit_movement_warp_wells(
        (
            _snapshot(10, ship_x=100, debrisdisk=0),
            _snapshot(11, ship_x=120, debrisdisk=0),
        ),
        nowarpwells=True,
    )
    assert summary.warp_well_matches == 1
    assert summary.valid_ordinary_planet_matches == 0
    assert summary.invalid_debris_planet_matches == 0
    assert summary.disabled_warp_well_matches == 1
    assert summary.unknown_context_matches == 0
