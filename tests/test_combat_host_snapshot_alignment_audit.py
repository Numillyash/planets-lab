from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_snapshot_alignment_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_snapshot_alignment_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_scope_separates_identity_from_post_movement_position() -> None:
    rows = [
        {
            "t_minus_1": {
                "present": True,
                "owner_match": True,
                "hull_match": True,
                "position_match": False,
                "mission_present": True,
                "target_present": True,
                "friendlycode_present": True,
            },
            "t": {
                "present": True,
                "owner_match": False,
                "hull_match": True,
                "position_match": True,
                "mission_present": True,
                "target_present": False,
                "friendlycode_present": True,
            },
        },
        {
            "t_minus_1": {"present": False},
            "t": {
                "present": True,
                "owner_match": True,
                "hull_match": True,
                "position_match": False,
                "mission_present": False,
                "target_present": False,
                "friendlycode_present": True,
            },
        },
    ]

    scope = audit._scope(rows)

    assert scope["ship_sides"] == 2
    assert scope["t_minus_1"]["presence"] == {"present": 1, "missing": 1}
    assert scope["t_minus_1"]["owner_hull_identity"] == {"match": 1}
    assert scope["t_minus_1"]["owner_hull_position"] == {"not_match": 1}
    assert scope["t_minus_1"]["private_fields_present"] == {
        "mission": 1,
        "mission1target": 1,
        "friendlycode": 1,
    }

    assert scope["t"]["presence"] == {"present": 2}
    assert scope["t"]["owner_hull_identity"] == {"not_match": 1, "match": 1}
    assert scope["t"]["owner_hull_position"] == {"not_match": 2}
    assert scope["t"]["private_fields_present"] == {
        "mission": 1,
        "mission1target": 0,
        "friendlycode": 2,
    }


def test_target_id_accepts_known_raw_aliases() -> None:
    assert audit._target_id({"mission1target": 42}) == 42
    assert audit._target_id({"mission1_target_id": 43}) == 43
    assert audit._target_id({"mission1targetid": 44}) == 44
    assert audit._target_id({}) is None
