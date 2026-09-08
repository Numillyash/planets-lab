from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_order_field_inventory.py"
spec = importlib.util.spec_from_file_location("combat_host_order_field_inventory", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_candidate_order_key_is_semantic_not_broad_substring_noise() -> None:
    assert audit._candidate_order_key("mission")
    assert audit._candidate_order_key("mission1target")
    assert audit._candidate_order_key("primaryenemy")
    assert audit._candidate_order_key("enemy")
    assert audit._candidate_order_key("friendlycode")
    assert audit._candidate_order_key("pe")
    assert not audit._candidate_order_key("engineid")
    assert not audit._candidate_order_key("neutronium")


def test_friendlycode_shape_separates_documented_numeric_range() -> None:
    assert audit._friendlycode_shape("001") == "numeric_001_999"
    assert audit._friendlycode_shape("999") == "numeric_001_999"
    assert audit._friendlycode_shape("000") == "000"
    assert audit._friendlycode_shape("12") == "numeric_other_len_2"
    assert audit._friendlycode_shape("abc") == "non_numeric"
    assert audit._friendlycode_shape(None) == "missing_or_non_string"


def test_catalog_inventory_only_surfaces_mission_named_top_level_keys() -> None:
    rows = audit._catalog_inventory(
        {
            "missions": [{"id": 3, "name": "Example"}],
            "missionSettings": {"enabled": True},
            "ships": [{"id": 1}],
        }
    )
    assert [row["key"] for row in rows] == ["missionSettings", "missions"]
    assert rows[1]["sample"] == [{"id": 3, "name": "Example"}]
