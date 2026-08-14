from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot
from planets_lab.corpus.readiness_corpus import (
    aggregate_readiness_games,
    summarize_readiness_game,
)


def _snapshot(player: int, turn: int, *, x: int, targetx: int):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=7,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": [],
            "starbases": [],
            "ships": [
                {
                    "id": 1,
                    "ownerid": player,
                    "hullid": 2,
                    "x": x,
                    "y": 100,
                    "warp": 5,
                    "targetx": targetx,
                    "targety": 100,
                    "engineid": 4,
                    "beamid": 0,
                    "torpedoid": 0,
                    "beams": 0,
                    "torps": 0,
                    "bays": 0,
                    "ammo": 0,
                    "neutronium": 50,
                    "duranium": 0,
                    "tritanium": 0,
                    "molybdenum": 0,
                    "supplies": 0,
                    "clans": 0,
                    "infoturn": turn,
                }
            ],
        },
    )


def test_readiness_game_and_corpus_aggregation() -> None:
    row = summarize_readiness_game(
        game_id=7,
        settings_hash="a" * 64,
        snapshots=(
            _snapshot(1, 10, x=100, targetx=125),
            _snapshot(1, 11, x=125, targetx=125),
        ),
    )
    assert row["profiles"]["movement_geometry"]["status_counts"] == {"ready": 1}
    assert row["profiles"]["movement_fuel_mass"]["status_counts"] == {"ready": 1}

    stats = aggregate_readiness_games([row], failed_game_ids=[99, 99])
    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [99]
    assert stats["settings_hashes"] == 1
    assert stats["snapshots"] == 2
    assert stats["profiles"]["movement_geometry"]["status_counts"] == {"ready": 1}
    assert stats["profiles_by_settings_hash"]["a" * 64]["movement_fuel_mass"] == {"ready": 1}


def test_readiness_corpus_cli_imports() -> None:
    from planets_lab.corpus.readiness_corpus_cli import main

    assert callable(main)
