from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(player: int, turn: int, *, ships=(), planets=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=7,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": list(planets),
            "ships": list(ships),
            "starbases": [],
        },
    )


def _ship(turn: int, *, ship_id: int, x: int, targetx: int):
    return {
        "id": ship_id,
        "ownerid": 1,
        "hullid": 3,
        "x": x,
        "y": 100,
        "warp": 5,
        "targetx": targetx,
        "targety": 100,
        "mission": 0,
        "friendlycode": "abc",
        "infoturn": turn,
    }


def test_planet_geometry_index_is_built_once_per_game(monkeypatch) -> None:
    import planets_lab.corpus.movement_differential as movement_differential

    original = movement_differential._planet_tuples_by_turn
    calls = 0

    def counted(entities):
        nonlocal calls
        calls += 1
        return original(entities)

    monkeypatch.setattr(movement_differential, "_planet_tuples_by_turn", counted)

    summary = movement_differential.evaluate_movement_differential(
        (
            _snapshot(
                1,
                10,
                ships=[
                    _ship(10, ship_id=10, x=100, targetx=125),
                    _ship(10, ship_id=11, x=200, targetx=225),
                ],
                planets=[{"id": 5, "ownerid": 0, "x": 120, "y": 100, "infoturn": 10}],
            ),
            _snapshot(
                1,
                11,
                ships=[
                    _ship(11, ship_id=10, x=125, targetx=125),
                    _ship(11, ship_id=11, x=225, targetx=225),
                ],
                planets=[{"id": 5, "ownerid": 0, "x": 120, "y": 100, "infoturn": 11}],
            ),
        )
    )

    assert summary.evaluated_move_most == 2
    assert calls == 1
