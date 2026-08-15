from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_differential import evaluate_movement_differential
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot, mechanics_projection


def _snapshot(player: int, turn: int, *, ship, planet, nowarpwells=False):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=7,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "settings": {"nowarpwells": nowarpwells},
            "planets": [planet],
            "ships": [ship],
            "starbases": [],
            "ionstorms": [],
        },
    )


def _ship(turn: int, *, x: int, targetx: int = 122):
    return {
        "id": 10,
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


def _planet(turn: int, *, debrisdisk: int):
    return {
        "id": 5,
        "ownerid": 0,
        "x": 120,
        "y": 100,
        "debrisdisk": debrisdisk,
        "infoturn": turn,
    }


def _summary(*, debrisdisk: int, nowarpwells: bool):
    return evaluate_movement_differential(
        (
            _snapshot(
                1,
                10,
                ship=_ship(10, x=100),
                planet=_planet(10, debrisdisk=debrisdisk),
                nowarpwells=nowarpwells,
            ),
            _snapshot(
                1,
                11,
                ship=_ship(11, x=120),
                planet=_planet(11, debrisdisk=debrisdisk),
                nowarpwells=nowarpwells,
            ),
        )
    )


def test_ordinary_planet_supplies_warp_well_when_enabled() -> None:
    summary = _summary(debrisdisk=0, nowarpwells=False)
    assert summary.category_counts == {"reachable_warp_well_match": 1}
    assert summary.geometrically_explained == 1


def test_debris_planetoid_does_not_supply_warp_well() -> None:
    summary = _summary(debrisdisk=1, nowarpwells=False)
    assert summary.category_counts == {"reachable_other": 1}
    assert summary.geometrically_explained == 0
    assert summary.unresolved == 1


def test_nowarpwells_disables_ordinary_planet_well() -> None:
    summary = _summary(debrisdisk=0, nowarpwells=True)
    assert summary.category_counts == {"reachable_other": 1}
    assert summary.geometrically_explained == 0
    assert summary.unresolved == 1


def test_normalizer_preserves_only_safe_warp_well_setting() -> None:
    projection = mechanics_projection(
        {
            "game": {"id": 7, "turn": 10},
            "player": {"id": 1},
            "players": [],
            "settings": {
                "nowarpwells": False,
                "gamepassword": "must-not-propagate",
                "name": "must-not-propagate-either",
            },
            "planets": [],
            "ships": [],
            "starbases": [],
            "ionstorms": [],
            "minefields": [],
        },
        member="player1-turn10.trn",
    )
    assert projection["settings"] == {"nowarpwells": False}
    assert "must-not-propagate" not in repr(projection)
