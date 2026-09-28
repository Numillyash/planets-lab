from __future__ import annotations

from collections import Counter

from planets_lab.corpus.public_validation_backfill_cli import (
    _select_backfill,
    _selection_target,
)
from planets_lab.corpus.public_finished_discover_cli import _manifest_bucket


def _manifest(
    game_id: int,
    *,
    campaign: bool = False,
    sphere: bool = False,
    finite_fuel: bool = False,
    game_type: int = 2,
    turn: int = 100,
    slots: int = 11,
) -> dict[str, object]:
    settings = {
        "campaignmode": campaign,
        "sphere": sphere,
        "unlimitedfuel": not finite_fuel,
        "chainedintercept": True,
        "cloakandintercept": True,
    }
    return {
        "schema": "planets-lab.corpus-game.v2",
        "game_id": game_id,
        "settings_hash": f"hash-{game_id}",
        "game": {
            "id": game_id,
            "gametype": game_type,
            "turn": turn,
            "slots": slots,
            "iscustom": False,
        },
        "settings": settings,
        "player_slots": [],
    }


def test_selection_target_uses_original_bucket_counts() -> None:
    selected = [
        _manifest(1, campaign=True),
        _manifest(2, game_type=6),
        _manifest(3, sphere=True),
    ]
    report = {
        "selected_games": 3,
        "selected_by_bucket": {
            "campaign": 1,
            "championship": 1,
            "sphere": 1,
        },
    }

    count, buckets = _selection_target(report, selected)

    assert count == 3
    assert buckets == Counter(
        {"campaign": 1, "championship": 1, "sphere": 1}
    )


def test_backfill_prefers_missing_bucket_over_generic_novelty() -> None:
    baseline = [_manifest(100, finite_fuel=True)]
    successful = [
        _manifest(1, campaign=True),
        _manifest(2, finite_fuel=True),
    ]
    candidates = [
        _manifest(10, game_type=6, turn=80),
        _manifest(11, campaign=True, turn=250),
        _manifest(12, sphere=True, turn=120),
    ]

    replacements, _rows, buckets = _select_backfill(
        candidates=candidates,
        baseline=baseline,
        successful=successful,
        rejected_ids=set(),
        target_count=4,
        target_buckets=Counter(
            {
                "campaign": 1,
                "finite_fuel": 1,
                "championship": 1,
                "sphere": 1,
            }
        ),
    )

    assert {_manifest_bucket(row) for row in replacements} == {
        "championship",
        "sphere",
    }
    assert buckets["campaign"] == 1
    assert buckets["finite_fuel"] == 1
    assert buckets["championship"] == 1
    assert buckets["sphere"] == 1


def test_backfill_never_reuses_rejected_ids() -> None:
    replacements, _rows, _buckets = _select_backfill(
        candidates=[
            _manifest(10, game_type=6, turn=250),
            _manifest(11, game_type=6, turn=200),
        ],
        baseline=[],
        successful=[],
        rejected_ids={10},
        target_count=1,
        target_buckets=Counter({"championship": 1}),
    )

    assert [row["game_id"] for row in replacements] == [11]
