from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_galactic_power_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_galactic_power_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_documented_side_observation_is_owner_specific() -> None:
    assert audit._documented_side_observation(
        owner_race_id=8,
        hull_id=70,
        factual_side="left",
        dual_empire_gorbie=False,
    ) == "empire_gorbie_left_observed"
    assert audit._documented_side_observation(
        owner_race_id=8,
        hull_id=70,
        factual_side="right",
        dual_empire_gorbie=False,
    ) == "empire_gorbie_right_requires_advantage_context"
    assert audit._documented_side_observation(
        owner_race_id=5,
        hull_id=70,
        factual_side="right",
        dual_empire_gorbie=False,
    ) == "not_applicable"


def test_dual_empire_gorbie_is_fail_closed_for_side_observation() -> None:
    assert audit._documented_side_observation(
        owner_race_id=8,
        hull_id=70,
        factual_side="right",
        dual_empire_gorbie=True,
    ) == "dual_empire_gorbie_ambiguous"


def test_forced_left_override_needed_reproduces_case2_shape() -> None:
    assert audit._forced_left_override_needed(
        factual_side="left",
        standard_relation="left_higher_priority",
    ) is True
    assert audit._forced_left_override_needed(
        factual_side="left",
        standard_relation="right_higher_priority",
    ) is False
    assert audit._forced_left_override_needed(
        factual_side="right",
        standard_relation="right_higher_priority",
    ) is False
    assert audit._forced_left_override_needed(
        factual_side="left",
        standard_relation=None,
    ) is None


def test_safe_order_is_mechanical_allowlist_only() -> None:
    row = audit._safe_order(
        {
            "mission": 7,
            "mission1target": 38,
            "enemy": 2,
            "friendlycode": "001",
            "damage": 0,
            "neutronium": 1760,
            "name": "private",
            "note": "private",
        }
    )
    assert row == {
        "mission": 7,
        "mission1target": 38,
        "enemy": 2,
        "friendlycode": "001",
        "damage": 0,
        "neutronium": 1760,
    }
