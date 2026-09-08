from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from planets_lab.corpus.reconstruction import PerspectiveRecord


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_residual_physical_stack_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_residual_physical_stack_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def _record(player_id: int, *, owner_id: int, turn: int = 19, **fields: object) -> PerspectiveRecord:
    raw = {"id": fields.pop("id", 10), "ownerid": owner_id, "hullid": fields.pop("hullid", 1), **fields}
    return PerspectiveRecord(
        player_id=player_id,
        archive_turn=turn,
        embedded_turn=turn,
        infoturn=turn,
        raw=raw,
    )


def test_owner_current_record_prefers_exact_owner_perspective() -> None:
    owner = _record(5, owner_id=5, id=89, x=100, y=200)
    other = _record(6, owner_id=5, id=89, x=100, y=200)
    status, record, current_count, owner_count = audit._owner_current_record((other, owner))
    assert status == "owner_current"
    assert record is owner
    assert current_count == 2
    assert owner_count == 1


def test_owner_current_record_fails_closed_when_owner_missing() -> None:
    other = _record(6, owner_id=5, id=89)
    status, record, current_count, owner_count = audit._owner_current_record((other,))
    assert status == "no_owner_current"
    assert record is None
    assert current_count == 1
    assert owner_count == 0


def test_candidate_reasons_capture_stack_and_intercept_context() -> None:
    reasons = audit._candidate_reasons(
        ship_id=77,
        raw={
            "x": 10,
            "y": 20,
            "targetx": 30,
            "targety": 40,
            "mission": 7,
            "mission1target": 89,
        },
        tracked_ship_ids={80, 89},
        battle_xy=(30, 40),
        tracked_tminus1_positions={(10, 20)},
    )
    assert reasons == [
        "waypoint_to_battle_coordinate",
        "intercepts_tracked_ship",
        "shares_tminus1_location_with_tracked_ship",
    ]


def test_candidate_reasons_always_keep_tracked_ship() -> None:
    reasons = audit._candidate_reasons(
        ship_id=80,
        raw={"x": 1, "y": 2, "targetx": 1, "targety": 2, "mission": 3},
        tracked_ship_ids={80, 89},
        battle_xy=(100, 200),
        tracked_tminus1_positions={(1, 2)},
    )
    assert reasons == ["tracked_ship"]


def test_safe_owner_record_does_not_emit_private_fields() -> None:
    record = _record(
        5,
        owner_id=5,
        id=89,
        x=10,
        y=20,
        mission=7,
        friendlycode="2eC",
        name="private",
        note="private",
    )
    safe = audit._safe_owner_record(record)
    assert safe["fields"]["id"] == 89
    assert safe["fields"]["friendlycode"] == "2eC"
    assert "name" not in safe["fields"]
    assert "note" not in safe["fields"]
