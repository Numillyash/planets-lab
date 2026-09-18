from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_post_mutation_next_pair_audit import _simulate_site  # noqa: E402


def _decision(left_ship_id: int, right_ship_id: int) -> dict[str, object]:
    active = min(left_ship_id, right_ship_id)
    target = max(left_ship_id, right_ship_id)
    return {
        "engagement_eligible": True,
        "matching_fc_blocks": False,
        "left_hwm_applies": False,
        "right_hwm_applies": False,
        "phase": "standard",
        "prestandard_kind": None,
        "phase_attacker_ship_id": None,
        "left_ship_id": target,
        "right_ship_id": active,
        "unresolved_reasons": [],
    }


def _row(a: int, b: int) -> dict[str, object]:
    return {
        "pair": [a, b],
        "left": {
            "ship_id": a,
            "owner_id": a,
            "mission": 3 if a == 10 else 0,
            "enemy": 0,
            "friendlycode": f"{a:03d}"[-3:],
        },
        "right": {
            "ship_id": b,
            "owner_id": b,
            "mission": 0,
            "enemy": 0,
            "friendlycode": f"{b:03d}"[-3:],
        },
        "strict": _decision(a, b),
    }


def _terminal(
    *,
    destroyed: bool = False,
    captured: bool = False,
) -> dict[str, object]:
    return {
        "shield": 0 if destroyed else 50,
        "damage": 100 if destroyed else 10,
        "crew": 0 if destroyed or captured else 80,
        "torpedoes": 5,
        "fighters": 0,
        "destroyed": destroyed,
        "captured": captured,
    }


def _appearance(
    ship_id: int,
    *,
    terminal: dict[str, object],
) -> dict[str, object]:
    return {
        "ship_id": ship_id,
        "hull_id": 20,
        "race_id": 2,
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


def test_destroyed_top_target_opens_next_independent_pair() -> None:
    queue = [
        {
            "vcr_id": 1,
            "pair": (10, 20),
            "left_ship_id": 20,
            "right_ship_id": 10,
        },
        {
            "vcr_id": 2,
            "pair": (10, 30),
            "left_ship_id": 30,
            "right_ship_id": 10,
        },
    ]
    appearances = {
        (1, 7, 1, 10): _appearance(10, terminal=_terminal()),
        (1, 7, 1, 20): _appearance(
            20,
            terminal=_terminal(destroyed=True),
        ),
        (1, 7, 2, 10): _appearance(10, terminal=_terminal()),
        (1, 7, 2, 30): _appearance(30, terminal=_terminal()),
    }

    result = _simulate_site(
        game_id=1,
        battle_turn=7,
        rows=[_row(10, 20), _row(10, 30)],
        profile="strict",
        factual_queue=queue,
        appearances=appearances,
    )

    assert result["status"] == "exact"
    assert result["transition_count"] == 1
    transition = result["transitions"][0]
    assert transition["predicted_pair"] == [10, 30]
    assert transition["inactive_pair_count"] == 1
    assert transition["exact"] is True


def test_capture_predecessor_is_excluded_fail_closed() -> None:
    queue = [
        {
            "vcr_id": 1,
            "pair": (10, 20),
            "left_ship_id": 20,
            "right_ship_id": 10,
        },
        {
            "vcr_id": 2,
            "pair": (10, 30),
            "left_ship_id": 30,
            "right_ship_id": 10,
        },
    ]
    appearances = {
        (1, 7, 1, 10): _appearance(10, terminal=_terminal()),
        (1, 7, 1, 20): _appearance(
            20,
            terminal=_terminal(captured=True),
        ),
        (1, 7, 2, 10): _appearance(10, terminal=_terminal()),
        (1, 7, 2, 30): _appearance(30, terminal=_terminal()),
    }

    result = _simulate_site(
        game_id=1,
        battle_turn=7,
        rows=[_row(10, 20), _row(10, 30)],
        profile="strict",
        factual_queue=queue,
        appearances=appearances,
    )

    assert result["status"] == "excluded"
    assert result["reason"] == "capture_predecessor"
