from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import combat_host_post_capture_active_membership_audit as module
from combat_host_post_capture_active_membership_audit import _simulate_capture


def _raw(
    ship_id: int,
    owner_id: int,
    *,
    mission: int = 0,
    enemy: int = 0,
    friendlycode: str = "500",
) -> dict[str, object]:
    return {
        "id": ship_id,
        "ownerid": owner_id,
        "hullid": 20,
        "mission": mission,
        "mission1target": 0,
        "enemy": enemy,
        "friendlycode": friendlycode,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "beams": 4,
        "torps": 2,
        "bays": 0,
        "ammo": 10,
    }


def _entry(
    ship_id: int,
    owner_id: int,
    *,
    mission: int = 0,
    enemy: int = 0,
    friendlycode: str = "500",
) -> dict[str, object]:
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": owner_id,
        "hull_id": 20,
        "hull_can_cloak": False,
        "position": (100, 100),
        "source": "test",
        "raw": _raw(
            ship_id,
            owner_id,
            mission=mission,
            enemy=enemy,
            friendlycode=friendlycode,
        ),
    }


def _terminal(
    *,
    destroyed: bool = False,
    captured: bool = False,
    crew: int | None = None,
) -> dict[str, object]:
    return {
        "shield": 0 if destroyed or captured else 50,
        "damage": 100 if destroyed else 10,
        "crew": (
            crew
            if crew is not None
            else (0 if destroyed or captured else 80)
        ),
        "torpedoes": 5,
        "fighters": 0,
        "destroyed": destroyed,
        "captured": captured,
    }


def _appearance(
    ship_id: int,
    owner_id: int,
    race_id: int,
    *,
    terminal: dict[str, object],
) -> dict[str, object]:
    return {
        "ship_id": ship_id,
        "hull_id": 20,
        "owner_id": owner_id,
        "race_id": race_id,
        "start": {
            "shield": 100,
            "damage": 0,
            "crew": 100,
            "beamcount": 4,
            "launchercount": 2,
            "baycount": 0,
            "torpedos": 10,
            "fighters": 0,
        },
        "terminal": terminal,
    }


def _key(vcr_id: int, ship_id: int) -> tuple[int, int, int, int]:
    return (1, 7, vcr_id, ship_id)


def _context(
    *,
    queue: list[dict[str, object]],
    predictions: dict[int, dict[str, object]],
) -> dict[str, object]:
    return {
        "game_id": 1,
        "battle_turn": 7,
        "before_turn": 6,
        "x": 100,
        "y": 100,
        "site": (100, 100),
        "site_ship_rows": predictions,
        "predictions": predictions,
        "relations": {6: {}},
        "controls": {},
        "factual": {"pair_rows": {}},
        "factual_queue": queue,
    }


def test_destroyed_prior_candidate_is_removed_before_capture_ranking(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "_relation_signature",
        lambda *args, **kwargs: ((0, 0, 0), (0, 0, 0)),
    )
    monkeypatch.setattr(
        module,
        "_independent_permission",
        lambda **kwargs: True if kwargs["request"] else False,
    )

    queue = [
        {"vcr_id": 1, "pair": (10, 20), "left_ship_id": 20, "right_ship_id": 10},
        {"vcr_id": 2, "pair": (10, 30), "left_ship_id": 10, "right_ship_id": 30},
        {"vcr_id": 3, "pair": (10, 40), "left_ship_id": 10, "right_ship_id": 40},
    ]
    predictions = {
        10: _entry(10, 1),
        20: _entry(20, 2, mission=3, friendlycode="100"),
        30: _entry(30, 3),
        40: _entry(40, 4, mission=3, friendlycode="200"),
    }
    appearances = {
        _key(1, 10): _appearance(10, 1, 1, terminal=_terminal()),
        _key(1, 20): _appearance(20, 2, 2, terminal=_terminal(destroyed=True)),
        _key(2, 10): _appearance(10, 1, 1, terminal=_terminal(captured=True)),
        _key(2, 30): _appearance(30, 3, 3, terminal=_terminal()),
    }
    capture = {
        "ship_id": 10,
        "captor_ship_id": 30,
        "captor_owner_id": 3,
        "current_opponent_ship_id": 40,
        "from_vcr_id": 2,
        "to_vcr_id": 3,
    }

    result = _simulate_capture(
        context=_context(queue=queue, predictions=predictions),
        capture=capture,
        appearances=appearances,
    )

    assert result["status"] == "resolved"
    assert result["prize_owner_id_after_capture"] == 3
    assert result["removed_ship_ids"] == [20]
    assert result["factual_opponent_active"] is True
    assert result["strict_requester_order"] == [40]
    assert result["factual_opponent_strict_rank"] == 1


def test_double_capture_uses_mutated_owner_from_prior_vcr(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "_relation_signature",
        lambda *args, **kwargs: ((0, 0, 0), (0, 0, 0)),
    )
    monkeypatch.setattr(
        module,
        "_independent_permission",
        lambda **kwargs: True if kwargs["request"] else False,
    )

    queue = [
        {"vcr_id": 1, "pair": (10, 20), "left_ship_id": 10, "right_ship_id": 20},
        {"vcr_id": 2, "pair": (10, 30), "left_ship_id": 10, "right_ship_id": 30},
        {"vcr_id": 3, "pair": (10, 40), "left_ship_id": 10, "right_ship_id": 40},
    ]
    predictions = {
        10: _entry(10, 1),
        20: _entry(20, 2),
        30: _entry(30, 3),
        40: _entry(40, 4, mission=3, friendlycode="200"),
    }
    appearances = {
        _key(1, 10): _appearance(10, 1, 1, terminal=_terminal(captured=True)),
        _key(1, 20): _appearance(20, 2, 2, terminal=_terminal()),
        _key(2, 10): _appearance(10, 2, 2, terminal=_terminal(captured=True)),
        _key(2, 30): _appearance(30, 3, 1, terminal=_terminal()),
    }
    capture = {
        "ship_id": 10,
        "captor_ship_id": 30,
        "captor_owner_id": 3,
        "current_opponent_ship_id": 40,
        "from_vcr_id": 2,
        "to_vcr_id": 3,
    }

    result = _simulate_capture(
        context=_context(queue=queue, predictions=predictions),
        capture=capture,
        appearances=appearances,
    )

    assert result["status"] == "resolved"
    assert result["prize_owner_id_after_capture"] == 3
    assert result["owner_changed_ship_ids"] == [10]
    assert [row["captured_ship_ids"] for row in result["mutation_trace"]] == [
        [10],
        [10],
    ]
    assert result["factual_opponent_strict_rank"] == 1



def test_raw_active_ship_decodes_nu_torpedo_ammo() -> None:
    entry = _entry(140, 10)
    raw = entry["raw"]
    assert isinstance(raw, dict)
    raw.update(
        {
            "beams": 4,
            "torps": 2,
            "bays": 0,
            "ammo": 20,
            "torpedoid": 10,
        }
    )
    active = module._raw_active_ship(entry, ship_id=140)
    assert active["launcher_count"] == 2
    assert active["bay_count"] == 0
    assert active["torpedoes"] == 20
    assert active["fighters"] == 0


def test_raw_active_ship_decodes_nu_carrier_ammo() -> None:
    entry = _entry(141, 10)
    raw = entry["raw"]
    assert isinstance(raw, dict)
    raw.update(
        {
            "beams": 6,
            "torps": 0,
            "bays": 10,
            "ammo": 67,
        }
    )
    active = module._raw_active_ship(entry, ship_id=141)
    assert active["launcher_count"] == 0
    assert active["bay_count"] == 10
    assert active["torpedoes"] == 0
    assert active["fighters"] == 67


def test_raw_active_ship_fails_closed_on_hybrid_ammo() -> None:
    entry = _entry(142, 10)
    raw = entry["raw"]
    assert isinstance(raw, dict)
    raw.update(
        {
            "torps": 3,
            "bays": 2,
            "ammo": 12,
        }
    )
    with pytest.raises(ValueError, match="ambiguous Nu ammo=12"):
        module._raw_active_ship(entry, ship_id=142)
