from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from planets_lab.corpus.movement_residual_context import StormRecord

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_cloak_fuel_attribution_audit import (  # noqa: E402
    _clean_stationary_fuel_context,
    _glory_start_context,
    _inside_any_ion_disturbance,
    _loki_start_exposure,
)


def test_inside_any_ion_disturbance() -> None:
    storm = StormRecord(
        id=1,
        x=100.0,
        y=100.0,
        radius=20.0,
        voltage=100.0,
        warp=1,
        heading=90.0,
        parent_id=0,
    )
    assert _inside_any_ion_disturbance((storm,), position=(110, 100)) is True
    assert _inside_any_ion_disturbance((storm,), position=(121, 100)) is False
    assert _inside_any_ion_disturbance((storm,), position=None) is None


def test_loki_start_exposure_requires_foreign_active_loki_within_range() -> None:
    rows = {
        1: (5, {"hullid": 46, "x": 100, "y": 100, "damage": 0}),
        2: (6, {"hullid": 7, "x": 108, "y": 100, "damage": 19}),
        3: (6, {"hullid": 7, "x": 100, "y": 100, "damage": 20}),
        4: (5, {"hullid": 7, "x": 100, "y": 100, "damage": 0}),
    }
    exposed, ids = _loki_start_exposure(
        rows=rows,
        target_owner_id=5,
        target_position=(100, 100),
    )
    assert exposed is True
    assert ids == [2]


def test_glory_start_context_uses_static_special_and_active_fc() -> None:
    specs = SimpleNamespace(
        hulls={
            39: SimpleNamespace(name="D19b", special="Glory Device\nRadiation Shielding"),
            46: SimpleNamespace(name="Meteor", special="Gravitonic"),
        }
    )
    rows = {
        10: (6, {"hullid": 39, "x": 100, "y": 100, "friendlycode": "TRG"}),
        11: (6, {"hullid": 39, "x": 100, "y": 100, "friendlycode": "abc"}),
        12: (6, {"hullid": 46, "x": 100, "y": 100, "friendlycode": "pop"}),
        13: (5, {"hullid": 39, "x": 100, "y": 100, "friendlycode": "pop"}),
    }
    result = _glory_start_context(
        rows=rows,
        target_owner_id=5,
        target_position=(100, 100),
        specs=specs,
    )
    assert [row["ship_id"] for row in result] == [10, 11]
    assert result[0]["active_code"] is True
    assert result[1]["active_code"] is False


def test_clean_stationary_fuel_context() -> None:
    assert _clean_stationary_fuel_context(
        damage_zero=True,
        effective_warp=0,
        same_position=True,
        outbound_transfer=False,
        inbound_transfer=False,
        foreign_origin_count=0,
    ) is True
    assert _clean_stationary_fuel_context(
        damage_zero=True,
        effective_warp=0,
        same_position=True,
        outbound_transfer=False,
        inbound_transfer=False,
        foreign_origin_count=1,
    ) is False
    assert _clean_stationary_fuel_context(
        damage_zero=True,
        effective_warp=1,
        same_position=True,
        outbound_transfer=False,
        inbound_transfer=False,
        foreign_origin_count=0,
    ) is False
