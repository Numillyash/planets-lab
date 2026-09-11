from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_initial_decision_audit import _initial_context  # noqa: E402


def _raw(ship_id: int, *, fc: str, mission: int = 9, enemy: int = 0):
    return {
        "id": ship_id,
        "mission": mission,
        "enemy": enemy,
        "friendlycode": fc,
    }


def _row(target_id: int = 98, attacker_id: int = 264):
    return {
        "target_ship_id": target_id,
        "attacker_ship_id": attacker_id,
    }


def test_initial_context_detects_ranked_above_skip() -> None:
    owners = {
        98: (5, _raw(98, fc="vjh")),
        190: (5, _raw(190, fc="kdu")),
        264: (11, _raw(264, fc="1uP", mission=3)),
    }
    queue = [{"vcr_id": 666, "pair": (190, 264)}]
    result = _initial_context(row=_row(), owner_rows=owners, factual_queue=queue)
    assert result["resolved"] is True
    assert result["initial_attacker"] is True
    assert result["target_outranks_factual_first_opponent"] is True
    assert result["classification"] == "initial_skip_target_outranks_factual"


def test_initial_context_detects_direct_initial_pair_control() -> None:
    owners = {
        118: (5, _raw(118, fc="wds")),
        134: (3, _raw(134, fc="rru", mission=10, enemy=5)),
    }
    queue = [{"vcr_id": 1, "pair": (118, 134)}]
    result = _initial_context(
        row=_row(target_id=118, attacker_id=134),
        owner_rows=owners,
        factual_queue=queue,
    )
    assert result["pair_is_first_for_attacker"] is True
    assert result["initial_attacker"] is True
    assert result["classification"] == "initial_pair_vcr"


def test_initial_context_separates_later_attacker_pair() -> None:
    owners = {
        10: (2, _raw(10, fc="abc")),
        20: (3, _raw(20, fc="def")),
        118: (5, _raw(118, fc="wds")),
        134: (3, _raw(134, fc="rru", mission=10, enemy=5)),
    }
    queue = [
        {"vcr_id": 1, "pair": (10, 20)},
        {"vcr_id": 2, "pair": (118, 134)},
    ]
    result = _initial_context(
        row=_row(target_id=118, attacker_id=134),
        owner_rows=owners,
        factual_queue=queue,
    )
    assert result["pair_is_first_for_attacker"] is True
    assert result["initial_attacker"] is False
    assert result["classification"] == "later_pair_vcr"


def test_initial_context_fails_closed_on_unsupported_priority() -> None:
    owners = {
        98: (5, _raw(98, fc="000")),
        190: (5, _raw(190, fc="kdu")),
        264: (11, _raw(264, fc="1uP", mission=3)),
    }
    result = _initial_context(
        row=_row(),
        owner_rows=owners,
        factual_queue=[{"vcr_id": 666, "pair": (190, 264)}],
    )
    assert result == {"resolved": False, "reason": "target_priority_unresolved"}
