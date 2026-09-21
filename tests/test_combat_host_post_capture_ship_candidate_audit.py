from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_post_capture_ship_candidate_audit import _analyze_site  # noqa: E402


def _entry(ship_id: int, owner_id: int, *, mission: int, enemy: int, fc: str):
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "raw": {
            "mission": mission,
            "enemy": enemy,
            "friendlycode": fc,
        },
    }


def test_post_capture_inventory_retargets_opponent_request_to_new_owner(monkeypatch) -> None:
    import combat_host_post_capture_ship_candidate_audit as module

    monkeypatch.setattr(module, "_relation_signature", lambda *args, **kwargs: ((0, 0, 0), (0, 0, 0)))
    monkeypatch.setattr(module, "_independent_permission", lambda **kwargs: True if kwargs["request"] else False)

    context = {
        "before_turn": 6,
        "site_ship_rows": {
            10: _entry(10, 5, mission=0, enemy=0, fc="900"),
            20: _entry(20, 5, mission=0, enemy=0, fc="800"),
            30: _entry(30, 8, mission=3, enemy=0, fc="100"),
        },
        "relations": {6: {}},
        "controls": {},
        "factual": {"pair_rows": {}},
    }
    capture = {
        "ship_id": 10,
        "captor_owner_id": 3,
        "current_opponent_ship_id": 30,
    }

    result = _analyze_site(context, capture)
    assert result["status"] == "resolved"
    assert result["factual_opponent_predicted_at_site"] is True
    assert result["factual_opponent_requests_new_owner"] is True
    assert result["factual_opponent_requester_rank"] == 1
    assert 20 in result["requester_order"] or result["requester_order"] == [30]
