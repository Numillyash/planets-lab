import io
import json
import zipfile

from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_chunnel_context import (
    ChunnelAbilityCatalog,
    evaluate_chunnel_residual_context,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _ship(
    ship_id: int,
    hull_id: int,
    *,
    x: int,
    y: int,
    turn: int,
    friendly_code: str = "abc",
) -> dict:
    return {
        "id": ship_id,
        "ownerid": 1,
        "hullid": hull_id,
        "x": x,
        "y": y,
        "warp": 0,
        "targetx": x,
        "targety": y,
        "mission": 0,
        "friendlycode": friendly_code,
        "infoturn": turn,
        "neutronium": 100,
    }


def _snapshot(turn: int, *, moved: bool) -> ArchiveTurnSnapshot:
    destination_x = 200 if moved else 0
    ships = [
        _ship(
            123,
            56,
            x=destination_x,
            y=0,
            turn=turn,
            friendly_code="456",
        ),
        _ship(456, 56, x=200, y=0, turn=turn),
        _ship(10, 17, x=destination_x, y=0, turn=turn),
    ]
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
            "ships": ships,
            "planets": [],
            "starbases": [],
            "ionstorms": [],
            "minefields": [],
        },
    )


def test_observed_chunnel_explains_initiator_and_same_owner_passenger() -> None:
    abilities = ChunnelAbilityCatalog(
        initiator_hull_ids=frozenset({56}),
        target_hull_ids=frozenset({56}),
        self_hull_ids=frozenset(),
        first_member="player1-turn10.trn",
        last_member="player1-turn11.trn",
        ability_sets_consistent=True,
    )
    result = evaluate_chunnel_residual_context(
        (
            _snapshot(10, moved=False),
            _snapshot(11, moved=True),
        ),
        abilities,
    )
    assert result["observed_chunnel_events"] == 1
    assert result["residual_before_chunnel"] == 2
    assert result["chunnel_explained"] == 2
    assert result["residual_after_chunnel"] == 0
    assert result["chunnel_counts"] == {"initiator": 1, "passenger_same_owner": 1}
    assert result["explained_category_counts"] == {"warp_zero_external_move": 2}


def _archive_payload(turn: int, *, changed: bool = False) -> dict:
    special = "Chunnel Initiator, Chunnel Target - test"
    hulls = [
        {"id": 56, "name": "Firecloud", "special": special},
        {"id": 17, "name": "Freighter", "special": ""},
    ]
    if changed:
        hulls.append({"id": 999, "name": "Late Target", "special": "Chunnel Target"})
    return {
        "game": {"id": 7, "turn": turn},
        "player": {"id": 1},
        "players": [{"id": 1}],
        "hulls": hulls,
    }


def test_extracts_only_stable_chunnel_abilities_from_changed_catalog() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("player1-turn0.trn", json.dumps(_archive_payload(0)))
        archive.writestr("player1-turn1.trn", json.dumps(_archive_payload(1, changed=True)))

    abilities = extract_stable_chunnel_abilities(buffer.getvalue())
    assert abilities.ability_sets_consistent is False
    assert abilities.initiator_hull_ids == frozenset({56})
    assert abilities.target_hull_ids == frozenset({56})
    assert 999 not in abilities.target_hull_ids


def test_chunnel_context_cli_imports() -> None:
    from planets_lab.corpus.movement_chunnel_context_corpus_cli import main

    assert callable(main)
