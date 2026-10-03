from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "afsim_r1_model.py"
)
SPEC = importlib.util.spec_from_file_location("afsim_r1_model", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


def ship(
    ship_id: int,
    owner: int,
    *,
    fc: str = "xxx",
    fuel: bool = True,
    kill: bool = False,
    pe: int = 0,
    beams: int = 1,
    tubes: int = 0,
    torps: int = 0,
    bays: int = 0,
    fighters: int = 0,
):
    return MODEL.AFSimShip(
        ship_id=ship_id,
        owner=owner,
        friendly_code=fc,
        fuel=fuel,
        kill=kill,
        primary_enemy=pe,
        beam_count=beams,
        torpedo_tubes=tubes,
        torpedoes=torps,
        fighter_bays=bays,
        fighters=fighters,
    )


def test_attack_value_examples_from_manual() -> None:
    expected = {
        "xxx": 1000,
        "1xx": 1,
        "10x": 10,
        "01x": 1,
        "999": 999,
        "123": 123,
        "18x": 18,
        "x23": 1000,
        "xx2": 1000,
        "x1x": 1000,
        "000": 1000,
        "1x2": 1000,
    }
    for fc, value in expected.items():
        assert MODEL.attack_value_from_friendly_code(fc) == value


def test_sort_key_is_kill_owner_attack_value_ship_id() -> None:
    rows = MODEL.sort_ships(
        [
            ship(50, 2, fc="001", kill=True),
            ship(20, 1, fc="100", kill=False),
            ship(30, 1, fc="010", kill=True),
            ship(10, 1, fc="010", kill=True),
        ]
    )
    assert [row.ship.ship_id for row in rows] == [10, 30, 50, 20]


def test_no_fuel_clears_effective_kill() -> None:
    rows = MODEL.sort_ships(
        [
            ship(10, 1, kill=True, fuel=False),
            ship(20, 2, kill=False, fuel=True),
        ]
    )
    assert rows[0].ship.ship_id == 10
    assert rows[0].effective_kill is False


def test_primary_enemy_equal_owner_is_cleared_after_capture() -> None:
    ships = [
        ship(10, 1, pe=2),
        ship(20, 2),
    ]
    captured = MODEL.apply_capture(
        ships,
        captured_ship_id=10,
        captor_ship_id=20,
    )
    prepared = {row.ship.ship_id: row for row in MODEL.sort_ships(captured)}
    assert prepared[10].ship.owner == 2
    assert prepared[10].effective_primary_enemy == 0


def test_kill_phase_uses_first_sorted_ship_and_first_valid_opponent() -> None:
    pair = MODEL.select_next_pair(
        [
            ship(30, 1, fc="010", kill=True),
            ship(10, 1, fc="001", kill=True),
            ship(40, 2, fc="001"),
            ship(20, 3, fc="001"),
        ]
    )
    assert pair is not None
    assert pair.phase == "kill"
    assert pair.initiator_id == 10
    assert pair.opponent_id == 20
    assert pair.left_id == 10
    assert pair.right_id == 20


def test_primary_enemy_phase_after_no_kill_pair() -> None:
    pair = MODEL.select_next_pair(
        [
            ship(30, 1, fc="001", pe=3),
            ship(10, 2, fc="001"),
            ship(20, 3, fc="001"),
        ]
    )
    assert pair is not None
    assert pair.phase == "primary_enemy"
    assert pair.initiator_id == 30
    assert pair.opponent_id == 20
    assert pair.left_id == 20
    assert pair.right_id == 30


def test_weapon_capability_matches_afsim_predicate() -> None:
    assert ship(1, 1, beams=1).can_fight() is True
    assert ship(1, 1, beams=0, tubes=1, torps=1).can_fight() is True
    assert ship(1, 1, beams=0, bays=1, fighters=1).can_fight() is True
    assert ship(1, 1, beams=0, tubes=1, torps=0, bays=0).can_fight() is False
    assert ship(1, 1, beams=0, bays=1, fighters=0, tubes=0).can_fight() is False


def test_selected_pair_is_canonicalized_by_ship_id_for_vcr_sides() -> None:
    pair = MODEL.select_next_pair(
        [
            ship(90, 1, kill=True, fc="001"),
            ship(12, 2, fc="001"),
        ]
    )
    assert pair is not None
    assert pair.initiator_id == 90
    assert pair.opponent_id == 12
    assert pair.left_id == 12
    assert pair.right_id == 90
