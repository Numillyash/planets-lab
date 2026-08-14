from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.diagnose_freshness_cli import (
    _find_id,
    _find_starbase,
    _freshness,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot() -> ArchiveTurnSnapshot:
    return ArchiveTurnSnapshot(
        member=TurnMember(player=1, turn=20, name="player1-turn20.trn"),
        game_id=620917,
        player_id=1,
        embedded_turn=20,
        snapshot_hash="fixture",
        mechanics_payload={
            "planets": [
                {
                    "id": 45,
                    "ownerid": 0,
                    "clans": 0,
                    "infoturn": 11,
                    "name": "must-not-be-read-by-diagnostic",
                }
            ],
            "starbases": [
                {
                    "id": 45,
                    "planetid": 45,
                    "raceid": 4,
                    "infoturn": 11,
                    "fighters": 25,
                }
            ],
            "ships": [
                {
                    "id": 25,
                    "ownerid": 0,
                    "crew": 10,
                    "warp": 0,
                    "infoturn": 16,
                    "name": "must-not-be-read-by-diagnostic",
                }
            ],
        },
    )


def test_freshness_marks_old_entity_records_stale() -> None:
    snapshot = _snapshot()
    planet = _find_id(snapshot, "planets", 45)
    starbase = _find_starbase(snapshot, 45)
    ship = _find_id(snapshot, "ships", 25)

    assert planet is not None
    assert starbase is not None
    assert ship is not None
    assert _freshness(planet, snapshot.embedded_turn) == (11, True)
    assert _freshness(starbase, snapshot.embedded_turn) == (11, True)
    assert _freshness(ship, snapshot.embedded_turn) == (16, True)


def test_freshness_marks_current_entity_record_fresh() -> None:
    assert _freshness({"infoturn": 20}, 20) == (20, False)
    assert _freshness({}, 20) == (None, None)


def test_freshness_diagnostics_cli_imports() -> None:
    from planets_lab.corpus.diagnose_freshness_cli import main

    assert callable(main)
