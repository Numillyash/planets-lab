from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot
from planets_lab.corpus.reconstruction import reconstruct_cross_perspective


def _snapshot(player: int, turn: int, *, planets=(), ships=(), starbases=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=1,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": list(planets),
            "ships": list(ships),
            "starbases": list(starbases),
        },
    )


def test_reconstruction_prefers_current_owner_perspective_for_planet_and_base() -> None:
    snapshots = (
        _snapshot(
            1,
            20,
            planets=[{"id": 45, "ownerid": 0, "clans": 0, "infoturn": 12}],
            starbases=[{"planetid": 45, "fighters": 25, "infoturn": 11}],
        ),
        _snapshot(
            4,
            20,
            planets=[{"id": 45, "ownerid": 4, "clans": 1600, "infoturn": 20}],
            starbases=[{"planetid": 45, "fighters": 25, "infoturn": 20}],
        ),
    )

    summary = reconstruct_cross_perspective(snapshots)
    planet = next(r for r in summary.resolutions if r.kind == "planet" and r.entity_id == 45)
    base = next(r for r in summary.resolutions if r.kind == "starbase" and r.entity_id == 45)

    assert planet.status == "owner_perspective"
    assert planet.authoritative_player_id == 4
    assert planet.record["ownerid"] == 4
    assert base.status == "owner_perspective"
    assert base.authoritative_player_id == 4


def test_reconstruction_preserves_fresh_observer_dependent_ghost_crew_conflict() -> None:
    common = {
        "id": 25,
        "ownerid": 0,
        "hullid": 17,
        "x": 2272,
        "y": 2310,
        "warp": 0,
        "infoturn": 20,
    }
    snapshots = (
        _snapshot(4, 20, ships=[{**common, "crew": 0}]),
        _snapshot(7, 20, ships=[{**common, "crew": -1}]),
        _snapshot(8, 20, ships=[{**common, "crew": 10}]),
    )

    summary = reconstruct_cross_perspective(snapshots)
    ship = next(r for r in summary.resolutions if r.kind == "ship" and r.entity_id == 25)

    assert ship.status == "conflict"
    assert ship.authoritative_player_id is None
    assert ship.conflicts == {"crew": (0, 10)}
    assert ship.record is None


def test_reconstruction_marks_stale_only_entity_as_no_current() -> None:
    snapshots = (
        _snapshot(1, 30, ships=[{"id": 9, "ownerid": 2, "hullid": 3, "infoturn": 25}]),
        _snapshot(3, 30, ships=[{"id": 9, "ownerid": 2, "hullid": 3, "infoturn": 25}]),
    )

    summary = reconstruct_cross_perspective(snapshots)
    ship = next(r for r in summary.resolutions if r.kind == "ship" and r.entity_id == 9)

    assert ship.status == "no_current"
    assert ship.current_players == ()
    assert ship.stale_players == (1, 3)


def test_reconstruct_cli_imports() -> None:
    from planets_lab.corpus.reconstruct_cli import main

    assert callable(main)
