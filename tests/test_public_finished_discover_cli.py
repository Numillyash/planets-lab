from __future__ import annotations

from planets_lab.corpus.public_finished_discover_cli import (
    _eligible_metadata,
    _manifest_bucket,
    _merge_records,
    _round_robin_shortlist,
    _select_records,
)


def _game(
    game_id: int,
    *,
    short: str = "Standard",
    game_type: int = 2,
    turn: int = 80,
    slots: int = 11,
    custom: bool = False,
) -> dict[str, object]:
    return {
        "id": game_id,
        "status": 3,
        "isprivate": False,
        "shortdescription": short,
        "gametype": game_type,
        "turn": turn,
        "slots": slots,
        "iscustom": custom,
    }


def _manifest(
    game_id: int,
    *,
    settings: dict[str, object],
    activeadvantages: str = "",
    activehulls: str = "",
    game_type: int = 2,
    turn: int = 80,
    slots: int = 11,
) -> dict[str, object]:
    return {
        "schema": "planets-lab.corpus-game.v2",
        "game_id": game_id,
        "tier": "B",
        "settings_hash": f"hash-{game_id}",
        "game": {
            "id": game_id,
            "status": 3,
            "gametype": game_type,
            "turn": turn,
            "slots": slots,
            "iscustom": False,
        },
        "settings": settings,
        "player_slots": [
            {
                "id": 1,
                "raceid": 6,
                "activeadvantages": activeadvantages,
                "activehulls": activehulls,
            }
        ],
    }


def test_metadata_filter_rejects_existing_small_or_private_games() -> None:
    existing = frozenset({10})

    assert not _eligible_metadata(
        _game(10),
        existing_ids=existing,
        min_turn=55,
        min_slots=8,
    )
    assert not _eligible_metadata(
        {**_game(11), "turn": 20},
        existing_ids=existing,
        min_turn=55,
        min_slots=8,
    )
    assert not _eligible_metadata(
        {**_game(12), "isprivate": True},
        existing_ids=existing,
        min_turn=55,
        min_slots=8,
    )
    assert _eligible_metadata(
        _game(13),
        existing_ids=existing,
        min_turn=55,
        min_slots=8,
    )


def test_shortlist_round_robins_ruleset_categories() -> None:
    games = [
        _game(1, short="Campaign"),
        _game(2, game_type=6, short="Championship"),
        _game(3, short="Classic"),
        _game(4, short="Standard"),
        _game(5, short="Hosted", custom=True),
        _game(6, game_type=3, short="Teams"),
        _game(7, game_type=4, short="Giant Melee"),
    ]

    shortlist = _round_robin_shortlist(games, limit=7)

    assert {row["id"] for row in shortlist} == set(range(1, 8))


def test_selector_strongly_prioritizes_active_campaign_capabilities() -> None:
    baseline = [
        _manifest(
            1,
            settings={
                "campaignmode": False,
                "sphere": False,
                "chainedintercept": True,
                "unlimitedfuel": False,
            },
        )
    ]
    ordinary = _manifest(
        2,
        settings={
            "campaignmode": False,
            "sphere": False,
            "chainedintercept": True,
            "unlimitedfuel": False,
        },
    )
    campaign = _manifest(
        3,
        settings={
            "campaignmode": True,
            "sphere": False,
            "chainedintercept": True,
            "unlimitedfuel": True,
        },
        activeadvantages="Stack Ships",
        activehulls="Campaign Hull",
    )

    selected, report = _select_records(
        [ordinary, campaign],
        baseline=baseline,
        count=1,
    )

    assert selected[0]["game_id"] == 3
    assert _manifest_bucket(selected[0]) == "campaign_active"
    assert "new_activeadvantages" in report[0]["reasons"]
    assert "new_activehulls" in report[0]["reasons"]


def test_manifest_merge_is_deduplicated_and_deterministic() -> None:
    base = _manifest(10, settings={"campaignmode": False})
    extra = _manifest(20, settings={"campaignmode": True})

    merged = _merge_records([base], [extra, base])

    assert [row["game_id"] for row in merged] == [10, 20]
