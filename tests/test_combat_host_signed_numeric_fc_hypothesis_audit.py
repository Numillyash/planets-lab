from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_signed_numeric_fc_hypothesis_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_signed_numeric_fc_hypothesis_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_signed_three_character_codes_are_hypothesis_numeric() -> None:
    assert audit._signed_fc_kind("-54") == ("strict_numeric", -54)
    assert audit._signed_fc_kind("+07") == ("strict_numeric", 7)


def test_documented_numeric_and_symbolic_behavior_is_preserved() -> None:
    assert audit._signed_fc_kind("125") == ("strict_numeric", 125)
    assert audit._signed_fc_kind("001") == ("strict_numeric", 1)
    assert audit._signed_fc_kind("abc") == ("symbolic", None)
    assert audit._signed_fc_kind("-5") == ("symbolic", None)


def test_delta_counts_reports_removed_and_added_residuals() -> None:
    before = {"right_higher_priority": 417, "left_higher_priority": 3}
    after = {"right_higher_priority": 419, "left_higher_priority": 1}
    assert audit._delta_counts(before, after) == {
        "left_higher_priority": -2,
        "right_higher_priority": 2,
    }
