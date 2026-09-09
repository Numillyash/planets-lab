from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_candidate_set_audit import (  # noqa: E402
    _fuel_input,
    _independent_permission,
    _intrinsic_stationary_reason,
    _potential_chunnel_source_sites,
    _tow_target_ids,
)


def test_intrinsic_stationary_accepts_plain_warp_zero_ship() -> None:
    raw = {
        "x": 1000,
        "y": 1000,
        "warp": 0,
        "mission": 1,
        "friendlycode": "abc",
    }
    assert (
        _intrinsic_stationary_reason(
            ship_id=10,
            raw=raw,
            tow_targets=frozenset(),
            chunnel_source_sites=frozenset(),
        )
        is None
    )


def test_intrinsic_stationary_fails_closed_on_special_or_external_movement() -> None:
    base = {"x": 1000, "y": 1000, "warp": 0, "mission": 1, "friendlycode": "abc"}

    assert _intrinsic_stationary_reason(
        ship_id=10,
        raw={**base, "mission": 7},
        tow_targets=frozenset(),
        chunnel_source_sites=frozenset(),
    ) == "intercept_movement"

    assert _intrinsic_stationary_reason(
        ship_id=10,
        raw=base,
        tow_targets=frozenset({10}),
        chunnel_source_sites=frozenset(),
    ) == "tow_target"

    assert _intrinsic_stationary_reason(
        ship_id=10,
        raw=base,
        tow_targets=frozenset(),
        chunnel_source_sites=frozenset({(1000, 1000)}),
    ) == "potential_chunnel_source_stack"


def test_tow_targets_are_collected_without_claiming_tow_success() -> None:
    rows = {
        1: (5, {"mission": 6, "mission1target": 9}),
        2: (5, {"mission": 1, "mission1target": 8}),
        3: (6, {"mission": 6, "mission1target": 0}),
    }
    assert _tow_target_ids(rows) == frozenset({9})


def test_obvious_firecloud_source_marks_whole_start_site_unresolved() -> None:
    rows = {
        12: (
            5,
            {"hullid": 56, "friendlycode": "077", "x": 1000, "y": 1000},
        ),
        77: (
            5,
            {"hullid": 56, "friendlycode": "abc", "x": 1200, "y": 1200},
        ),
        88: (
            5,
            {"hullid": 17, "friendlycode": "abc", "x": 1000, "y": 1000},
        ),
    }
    assert _potential_chunnel_source_sites(rows) == frozenset({(1000, 1000)})


def test_fuel_input_never_turns_tminus1_zero_into_a_hard_blocker() -> None:
    assert _fuel_input({"neutronium": 10}) is True
    assert _fuel_input({"neutronium": 0}) is None
    assert _fuel_input({}) is None


def test_independent_permission_is_leave_pair_out() -> None:
    signature = (((1, 1, 0),), ((1, 1, 0),))
    own_row = (20, 7, (10, 11))
    other_row = (18, 4, (30, 31))
    controls = {(signature, "low_to_high"): {own_row, other_row}}

    assert _independent_permission(
        request=True,
        owner_id=5,
        opponent_owner_id=6,
        signature=signature,
        controls=controls,
        excluded_rows=frozenset({own_row}),
    ) is True

    assert _independent_permission(
        request=True,
        owner_id=5,
        opponent_owner_id=6,
        signature=signature,
        controls={(signature, "low_to_high"): {own_row}},
        excluded_rows=frozenset({own_row}),
    ) is None

    assert _independent_permission(
        request=False,
        owner_id=5,
        opponent_owner_id=6,
        signature=signature,
        controls=controls,
        excluded_rows=frozenset(),
    ) is False
