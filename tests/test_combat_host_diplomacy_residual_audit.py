from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_diplomacy_residual_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_diplomacy_residual_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_safe_relation_projects_only_numeric_mechanical_fields() -> None:
    row = audit._safe_relation(
        {
            "id": 91,
            "playerid": 4,
            "playertoid": 3,
            "relationto": 2,
            "relationfrom": 0,
            "conflictlevel": 1,
            "color": "secret-looking-string",
            "username": "must-not-leak",
        }
    )
    assert row == {
        "id": 91,
        "playerid": 4,
        "playertoid": 3,
        "relationto": 2,
        "relationfrom": 0,
        "conflictlevel": 1,
    }


def test_target_pair_accepts_only_the_two_directed_edges() -> None:
    assert audit._is_target_pair({"playerid": 4, "playertoid": 3}, 4, 3)
    assert audit._is_target_pair({"playerid": 3, "playertoid": 4}, 4, 3)
    assert not audit._is_target_pair({"playerid": 4, "playertoid": 5}, 4, 3)
    assert not audit._is_target_pair({"playerid": 5, "playertoid": 3}, 4, 3)


def test_unique_relation_values_deduplicate_perspective_copies() -> None:
    rows = [
        {"perspective_player": 4, "playerid": 4, "playertoid": 3, "relationto": 2, "relationfrom": 0, "conflictlevel": 0},
        {"perspective_player": 7, "playerid": 4, "playertoid": 3, "relationto": 2, "relationfrom": 0, "conflictlevel": 0},
        {"perspective_player": 3, "playerid": 3, "playertoid": 4, "relationto": 0, "relationfrom": 2, "conflictlevel": 0},
    ]
    assert audit._unique_relation_values(rows, 4, 3) == {
        "4->3": [[2, 0, 0]],
        "3->4": [[0, 2, 0]],
    }


def test_mirror_consistency_checks_to_from_direction() -> None:
    consistent = {
        "4->3": [[2, 0, 0]],
        "3->4": [[0, 2, 0]],
    }
    inconsistent = {
        "4->3": [[2, 0, 0]],
        "3->4": [[0, 3, 0]],
    }
    ambiguous = {
        "4->3": [[2, 0, 0], [3, 0, 0]],
        "3->4": [[0, 2, 0]],
    }
    assert audit._mirror_consistent(consistent, 4, 3) is True
    assert audit._mirror_consistent(inconsistent, 4, 3) is False
    assert audit._mirror_consistent(ambiguous, 4, 3) is None
