from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.field_reconstruction import reconstruct_fields
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


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


def test_field_reconstruction_keeps_resolved_ship_fields_when_other_fields_conflict() -> None:
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
        _snapshot(4, 20, ships=[{**common, "crew": 0, "engineid": 0, "neutronium": 0}]),
        _snapshot(7, 20, ships=[{**common, "crew": -1, "engineid": 9, "neutronium": 600}]),
        _snapshot(8, 20, ships=[{**common, "crew": 10, "engineid": 9, "neutronium": 600}]),
    )

    summary = reconstruct_fields(snapshots)
    ship = next(e for e in summary.entities if e.kind == "ship" and e.entity_id == 25)

    assert ship.fields["hullid"].status == "current_consensus"
    assert ship.fields["hullid"].value == 17
    assert ship.fields["x"].value == 2272
    assert ship.fields["warp"].value == 0
    assert ship.fields["crew"].status == "current_conflict"
    assert ship.fields["crew"].alternatives == (0, 10)
    assert ship.fields["engineid"].status == "current_conflict"
    assert ship.fields["neutronium"].status == "current_conflict"
    assert "crew" in ship.conflict_fields


def test_field_reconstruction_prefers_owner_perspective_field_values() -> None:
    snapshots = (
        _snapshot(
            1,
            20,
            planets=[{"id": 45, "ownerid": 0, "clans": 0, "x": 1, "y": 2, "infoturn": 12}],
        ),
        _snapshot(
            4,
            20,
            planets=[{"id": 45, "ownerid": 4, "clans": 1600, "x": 1, "y": 2, "infoturn": 20}],
        ),
    )

    summary = reconstruct_fields(snapshots)
    planet = next(e for e in summary.entities if e.kind == "planet" and e.entity_id == 45)

    assert planet.owner_hint == 4
    assert planet.fields["ownerid"].status == "owner_perspective"
    assert planet.fields["ownerid"].value == 4
    assert planet.fields["clans"].status == "owner_perspective"
    assert planet.fields["clans"].value == 1600


def test_field_reconstruction_allows_stale_fallback_only_for_static_fields() -> None:
    snapshots = (
        _snapshot(
            1,
            10,
            planets=[{"id": 3, "x": 100, "y": 200, "ownerid": 2, "clans": 500, "infoturn": 7}],
        ),
        _snapshot(
            2,
            10,
            planets=[{"id": 3, "x": 100, "y": 200, "ownerid": 2, "clans": 500, "infoturn": 7}],
        ),
    )

    summary = reconstruct_fields(snapshots)
    planet = next(e for e in summary.entities if e.kind == "planet" and e.entity_id == 3)

    assert planet.fields["x"].status == "stale_static_consensus"
    assert planet.fields["x"].value == 100
    assert planet.fields["y"].status == "stale_static_consensus"
    assert planet.fields["ownerid"].status == "no_current"
    assert planet.fields["clans"].status == "no_current"
    assert "ownerid" in planet.unresolved_dynamic_fields


def test_field_reconstruction_uses_planet_owner_for_starbase_fields() -> None:
    snapshots = (
        _snapshot(
            4,
            30,
            planets=[{"id": 45, "ownerid": 4, "x": 1, "y": 2, "infoturn": 30}],
            starbases=[{"planetid": 45, "fighters": 25, "defense": 100, "infoturn": 30}],
        ),
        _snapshot(
            7,
            30,
            planets=[{"id": 45, "ownerid": 4, "x": 1, "y": 2, "infoturn": 30}],
            starbases=[{"planetid": 45, "fighters": 0, "defense": 0, "infoturn": 30}],
        ),
    )

    summary = reconstruct_fields(snapshots)
    base = next(e for e in summary.entities if e.kind == "starbase" and e.entity_id == 45)

    assert base.owner_hint == 4
    assert base.fields["fighters"].status == "owner_perspective"
    assert base.fields["fighters"].value == 25
    assert base.fields["defense"].value == 100
