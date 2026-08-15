from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.field_reconstruction import (
    clear_reconstruction_cache,
    reconstruct_fields,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot
from planets_lab.corpus.readiness import (
    MOVEMENT_GEOMETRY,
    clear_readiness_cache,
    evaluate_readiness,
)


def _snapshot(turn: int, x: int) -> ArchiveTurnSnapshot:
    ship = {
        "id": 10,
        "ownerid": 1,
        "hullid": 3,
        "x": x,
        "y": 100,
        "warp": 5,
        "targetx": 125,
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
        snapshot_hash=f"fixture-{turn}-{x}",
        mechanics_payload={
            "game": {"id": 7, "turn": turn},
            "player": {"id": 1},
            "players": [{"id": 1}],
            "planets": [],
            "ships": [ship],
            "starbases": [],
            "ionstorms": [],
            "minefields": [],
            "settings": {"nowarpwells": False},
        },
    )


def test_reconstruction_reuses_same_snapshot_tuple() -> None:
    snapshots = (_snapshot(10, 100), _snapshot(11, 125))
    clear_reconstruction_cache()
    first = reconstruct_fields(snapshots)
    second = reconstruct_fields(snapshots)
    assert second is first


def test_readiness_reuses_same_snapshot_tuple_and_profile() -> None:
    snapshots = (_snapshot(10, 100), _snapshot(11, 125))
    clear_reconstruction_cache()
    clear_readiness_cache()
    first = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    second = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    assert second is first


def test_pipeline_cli_imports() -> None:
    from planets_lab.corpus.movement_pipeline_corpus_cli import main

    assert callable(main)
