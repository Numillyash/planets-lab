from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_priority_intercept_non_pia_residual_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_priority_intercept_non_pia_residual_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_supported_nonmatching_fc_accepts_symbolic_and_signed_numeric() -> None:
    assert audit._is_supported_nonmatching_fc(
        {"friendlycode": "abc"},
        {"friendlycode": "-54"},
    )


def test_supported_nonmatching_fc_rejects_matching_and_erratic_numeric() -> None:
    assert not audit._is_supported_nonmatching_fc(
        {"friendlycode": "abc"},
        {"friendlycode": "abc"},
    )
    assert not audit._is_supported_nonmatching_fc(
        {"friendlycode": "12"},
        {"friendlycode": "abc"},
    )


def test_side_detail_preserves_selected_orders_and_hull_metadata() -> None:
    specs = SimpleNamespace(
        hulls={
            29: SimpleNamespace(
                name="Dark Wing Class Battleship",
                special="",
                can_cloak=True,
            )
        }
    )
    detail = audit._side_detail(
        raw={
            "mission": 7,
            "mission1target": 50,
            "mission2target": 0,
            "enemy": 4,
            "friendlycode": "osq",
            "iscloaked": False,
            "neutronium": 55,
            "damage": 3,
        },
        ship_id=57,
        owner_id=3,
        race_id=3,
        hull_id=29,
        opponent_ship_id=50,
        target_owner_id=4,
        pia_class="nonqualifying_intercept",
        specs=specs,
    )
    assert detail["ship_id"] == 57
    assert detail["hull_id"] == 29
    assert detail["hull_can_cloak"] is True
    assert detail["mission"] == 7
    assert detail["mission1target"] == 50
    assert detail["enemy"] == 4
    assert detail["target_owner_id"] == 4
    assert detail["friendlycode"] == "osq"
