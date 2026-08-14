from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.field_corpus import aggregate_field_games, summarize_field_game
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(player: int, turn: int, *, planets=(), ships=(), starbases=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=9,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": list(planets),
            "ships": list(ships),
            "starbases": list(starbases),
        },
    )


def test_field_game_summary_counts_conflicts_without_raw_values() -> None:
    common = {
        "id": 25,
        "ownerid": 0,
        "hullid": 17,
        "x": 100,
        "y": 200,
        "warp": 0,
        "infoturn": 10,
    }
    snapshots = (
        _snapshot(1, 10, ships=[{**common, "crew": 0, "neutronium": 0}]),
        _snapshot(2, 10, ships=[{**common, "crew": 10, "neutronium": 600}]),
    )

    row = summarize_field_game(
        game_id=9,
        settings_hash="a" * 64,
        snapshots=snapshots,
    )

    assert row["snapshots"] == 2
    assert row["entities"] == 1
    assert row["entities_with_conflicts"] == 1
    assert row["conflict_field_counts"]["ship.crew"] == 1
    assert row["conflict_field_counts"]["ship.neutronium"] == 1
    assert row["field_status_counts"]["current_conflict"] == 2
    encoded = repr(row)
    assert "600" not in encoded


def test_field_corpus_aggregation_sums_compact_metrics() -> None:
    row = {
        "settings_hash": "a" * 64,
        "snapshots": 2,
        "entities": 1,
        "resolved_fields": 5,
        "total_fields": 7,
        "entities_with_conflicts": 1,
        "entities_with_unresolved_dynamic": 0,
        "field_status_counts": {"current_consensus": 5, "current_conflict": 2},
        "conflict_field_counts": {"ship.crew": 1, "ship.neutronium": 1},
        "unresolved_dynamic_field_counts": {},
        "entities_with_conflicts_by_kind": {"ship": 1},
        "entities_with_unresolved_dynamic_by_kind": {},
    }

    stats = aggregate_field_games([row, row], failed_game_ids=[77, 77])

    assert stats["games_indexed"] == 2
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [77]
    assert stats["settings_hashes"] == 1
    assert stats["totals"]["resolved_fields"] == 10
    assert stats["field_status_counts"]["current_conflict"] == 4
    assert stats["conflict_field_counts"]["ship.crew"] == 2


def test_field_corpus_cli_imports() -> None:
    from planets_lab.corpus.field_corpus_cli import main

    assert callable(main)
