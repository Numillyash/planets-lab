from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOL = (
    Path(__file__).parents[1]
    / "tools"
    / "diagnostics"
    / "combat_host_matching_fc_suppression_audit.py"
)
spec = importlib.util.spec_from_file_location("combat_host_matching_fc_suppression_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_ordinary_exact_matching_fc_excludes_documented_exceptions() -> None:
    assert audit._ordinary_exact_matching_fc(
        {"friendlycode": "abc"}, {"friendlycode": "abc"}
    ) == "abc"
    assert audit._ordinary_exact_matching_fc(
        {"friendlycode": "abc"}, {"friendlycode": "Abc"}
    ) is None
    for value in ("mkt", "MKT", "lfm", "LFM", "ntp", "NTP"):
        assert audit._ordinary_exact_matching_fc(
            {"friendlycode": value}, {"friendlycode": value}
        ) is None


def test_hostility_shape_uses_kill_or_primary_enemy() -> None:
    assert audit._hostility_shape(
        left_raw={"mission": 3, "enemy": 0},
        left_owner=1,
        right_raw={"mission": 0, "enemy": 0},
        right_owner=2,
    ) == "left_only"
    assert audit._hostility_shape(
        left_raw={"mission": 0, "enemy": 2},
        left_owner=1,
        right_raw={"mission": 0, "enemy": 1},
        right_owner=2,
    ) == "both"
    assert audit._hostility_shape(
        left_raw={"mission": 0, "enemy": 0},
        left_owner=1,
        right_raw={"mission": 0, "enemy": 0},
        right_owner=2,
    ) == "none"


def test_relation_signature_is_owner_order_stable() -> None:
    rows = {
        (5, 2): {(1, 1, 0)},
        (2, 5): {(1, 1, 0)},
    }
    forward = audit._relation_signature(rows, 5, 2)
    reverse = audit._relation_signature(rows, 2, 5)
    assert forward == reverse
    assert audit._unique_relation_signature(forward)
    assert audit._safe_signature(forward) == {
        "low_to_high": [[1, 1, 0]],
        "high_to_low": [[1, 1, 0]],
    }


def test_ambiguous_or_missing_relation_signature_is_not_unique() -> None:
    assert not audit._unique_relation_signature(((), ()))
    assert not audit._unique_relation_signature((
        ((0, 0, 0), (1, 1, 0)),
        ((1, 1, 0),),
    ))


def test_armed_requires_at_least_one_weapon_system() -> None:
    assert audit._armed({"beams": 1, "torps": 0, "bays": 0})
    assert audit._armed({"beams": 0, "torps": 2, "bays": 0})
    assert audit._armed({"beams": 0, "torps": 0, "bays": 1})
    assert not audit._armed({"beams": 0, "torps": 0, "bays": 0})


def test_positive_fuel_and_alive_are_strict() -> None:
    assert audit._positive_fuel({"neutronium": 1})
    assert not audit._positive_fuel({"neutronium": 0})
    assert audit._alive({"damage": 99})
    assert not audit._alive({"damage": 100})
