from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot
from planets_lab.corpus.readiness import (
    CONFLICT,
    PARTIAL,
    READY,
    STALE,
    MOVEMENT_FUEL_MASS,
    MOVEMENT_GEOMETRY,
    evaluate_readiness,
)


def _snapshot(player: int, archive_turn: int, embedded_turn: int, *, ships=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(
            player=player,
            turn=archive_turn,
            name=f"player{player}-turn{archive_turn}.trn",
        ),
        game_id=1,
        player_id=player,
        embedded_turn=embedded_turn,
        snapshot_hash=f"{player}-{archive_turn}",
        mechanics_payload={
            "planets": [],
            "ships": list(ships),
            "starbases": [],
        },
    )


def _ship(turn: int, *, owner=1, infoturn=None, **overrides):
    raw = {
        "id": 10,
        "ownerid": owner,
        "hullid": 3,
        "x": 100,
        "y": 200,
        "warp": 6,
        "targetx": 130,
        "targety": 240,
        "engineid": 5,
        "beamid": 0,
        "torpedoid": 0,
        "beams": 0,
        "torps": 0,
        "bays": 0,
        "ammo": 0,
        "neutronium": 100,
        "duranium": 2,
        "tritanium": 3,
        "molybdenum": 4,
        "supplies": 5,
        "clans": 6,
        "infoturn": turn if infoturn is None else infoturn,
    }
    raw.update(overrides)
    return raw


def test_movement_geometry_ready_on_clean_embedded_consecutive_transition() -> None:
    snapshots = (
        _snapshot(1, 10, 10, ships=[_ship(10)]),
        _snapshot(1, 11, 11, ships=[_ship(11, x=130, y=240)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    assert summary.valid_turn_pairs == 1
    assert summary.skipped_turn_pairs == 0
    assert summary.status_counts == {READY: 1}
    assert summary.results[0].issues == ()


def test_geometry_conflict_is_not_discarded_as_whole_archive() -> None:
    snapshots = (
        _snapshot(1, 10, 10, ships=[_ship(10, owner=0, x=100)]),
        _snapshot(2, 10, 10, ships=[_ship(10, owner=0, x=101)]),
        _snapshot(1, 11, 11, ships=[_ship(11, owner=0, x=130)]),
        _snapshot(2, 11, 11, ships=[_ship(11, owner=0, x=130)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    assert summary.status_counts == {CONFLICT: 1}
    assert "before.ship.x.current_conflict" in summary.results[0].issues


def test_stale_only_dynamic_movement_field_marks_transition_stale() -> None:
    snapshots = (
        _snapshot(2, 10, 10, ships=[_ship(10, owner=0, infoturn=9)]),
        _snapshot(2, 11, 11, ships=[_ship(11, owner=0)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    assert summary.status_counts == {STALE: 1}
    assert any(issue.startswith("before.ship.warp.no_current") for issue in summary.results[0].issues)


def test_fuel_mass_conditionally_requires_fitted_component_ids() -> None:
    snapshots = (
        _snapshot(1, 10, 10, ships=[_ship(10, beams=2, beamid=-1)]),
        _snapshot(1, 11, 11, ships=[_ship(11, x=130, y=240, neutronium=90)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_FUEL_MASS)
    assert summary.status_counts == {PARTIAL: 1}
    assert "before.ship.beamid.no_current" in summary.results[0].issues


def test_fuel_mass_rejects_ambiguous_combined_ammo_role() -> None:
    snapshots = (
        _snapshot(1, 10, 10, ships=[_ship(10, torps=2, bays=1, ammo=20, torpedoid=4)]),
        _snapshot(1, 11, 11, ships=[_ship(11, x=130, y=240, neutronium=90)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_FUEL_MASS)
    assert summary.status_counts == {PARTIAL: 1}
    assert "before.ship.ammo.ambiguous_torpedo_or_fighter_ammo" in summary.results[0].issues


def test_nonconsecutive_embedded_boundary_is_skipped() -> None:
    snapshots = (
        _snapshot(1, 1, 1, ships=[_ship(1)]),
        _snapshot(1, 2, 1, ships=[_ship(1)]),
        _snapshot(1, 3, 3, ships=[_ship(3)]),
    )
    summary = evaluate_readiness(snapshots, MOVEMENT_GEOMETRY)
    assert summary.valid_turn_pairs == 0
    assert summary.skipped_turn_pairs == 2
    assert summary.evaluated_entities == 0
