from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from planets_lab.rules.combat.order import FriendlyCodePriorityKind


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_mission7_matched_control_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_mission7_matched_control_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_qualifying_noncloaking_targeted_intercept_requires_matching_target_and_pe() -> None:
    raw = {
        "mission": 7,
        "mission1target": 38,
        "enemy": 2,
        "friendlycode": "001",
    }

    assert audit._qualifies_noncloaking_targeted_intercept(
        interceptor_raw=raw,
        interceptor_owner_id=5,
        interceptor_hull_can_cloak=False,
        opponent_ship_id=38,
        opponent_owner_id=2,
        target_owner_id=2,
    )
    assert not audit._qualifies_noncloaking_targeted_intercept(
        interceptor_raw=raw,
        interceptor_owner_id=5,
        interceptor_hull_can_cloak=True,
        opponent_ship_id=38,
        opponent_owner_id=2,
        target_owner_id=2,
    )
    assert not audit._qualifies_noncloaking_targeted_intercept(
        interceptor_raw={**raw, "enemy": 3},
        interceptor_owner_id=5,
        interceptor_hull_can_cloak=False,
        opponent_ship_id=38,
        opponent_owner_id=2,
        target_owner_id=2,
    )


def test_case2_shape_distinguishes_exact_001_from_broader_numeric_controls() -> None:
    exact = audit._case2_shape(
        interceptor_fc={"kind": FriendlyCodePriorityKind.NUMERIC.value, "numeric_value": 1},
        opponent_fc={"kind": FriendlyCodePriorityKind.SYMBOLIC.value, "numeric_value": None},
        opponent_mission=1,
        reciprocal_pe=True,
    )
    broader = audit._case2_shape(
        interceptor_fc={"kind": FriendlyCodePriorityKind.NUMERIC.value, "numeric_value": 7},
        opponent_fc={"kind": FriendlyCodePriorityKind.SYMBOLIC.value, "numeric_value": None},
        opponent_mission=1,
        reciprocal_pe=True,
    )
    nonreciprocal = audit._case2_shape(
        interceptor_fc={"kind": FriendlyCodePriorityKind.NUMERIC.value, "numeric_value": 1},
        opponent_fc={"kind": FriendlyCodePriorityKind.SYMBOLIC.value, "numeric_value": None},
        opponent_mission=1,
        reciprocal_pe=False,
    )

    assert exact == "case2_exact_order_shape"
    assert broader == "numeric_vs_symbolic_nonkill"
    assert nonreciprocal == "not_reciprocal_pe"


def test_safe_side_is_mechanical_allowlist_only() -> None:
    raw = {
        "mission": 7,
        "mission1target": 38,
        "enemy": 2,
        "friendlycode": "001",
        "damage": 0,
        "neutronium": 1760,
        "name": "private name",
        "note": "private note",
        "messages": ["private"],
    }
    row = audit._safe_side(
        ship_id=62,
        owner_id=5,
        race_id=8,
        hull_id=70,
        hull_can_cloak=False,
        raw=raw,
    )

    assert row["ship_id"] == 62
    assert row["friendly_code"]["numeric_value"] == 1
    assert "name" not in row
    assert "note" not in row
    assert "messages" not in row


def test_standard_relation_reproduces_case2_left_higher_priority() -> None:
    relation = audit._standard_relation(
        left_raw={"mission": 7, "enemy": 2, "friendlycode": "001"},
        right_raw={"mission": 1, "enemy": 5, "friendlycode": "eqe"},
        left_ship_id=62,
        right_ship_id=38,
    )
    assert relation == "left_higher_priority"
