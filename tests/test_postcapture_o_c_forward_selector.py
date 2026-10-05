from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "postcapture_o_c_forward_selector.py"
)
SPEC = importlib.util.spec_from_file_location(
    "postcapture_o_c_forward_selector",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def state(ship_id: int, disposition: str, reason: str | None = None):
    return MODULE.CandidateState(
        ship_id=ship_id,
        disposition=disposition,
        reason=reason,
    )


def test_o_selects_first_eligible_after_captor() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[10, 20, 30, 40],
        prize_ship_id=10,
        captor_ship_id=20,
        states={
            30: state(30, "pair_blocked"),
            40: state(40, "eligible"),
        },
    )
    assert result.status == "resolved"
    assert result.branch == "O"
    assert result.predicted_ship_id == 40


def test_c_scans_between_prize_and_captor_after_o_exhausts() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[10, 20, 30, 40],
        prize_ship_id=10,
        captor_ship_id=30,
        states={
            40: state(40, "no_request"),
            20: state(20, "eligible"),
        },
    )
    assert result.status == "resolved"
    assert result.branch == "C"
    assert result.predicted_ship_id == 20


def test_unknown_o_candidate_fails_closed_before_c() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[10, 20, 30, 40],
        prize_ship_id=10,
        captor_ship_id=30,
        states={
            40: state(40, "unresolved", "strict_permission_unresolved"),
            20: state(20, "eligible"),
        },
    )
    assert result.status == "unresolved"
    assert result.branch == "O"
    assert result.unresolved_ship_id == 40


def test_unknown_c_candidate_fails_closed_before_later_c_candidate() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[10, 20, 30, 40, 50],
        prize_ship_id=10,
        captor_ship_id=40,
        states={
            50: state(50, "inactive"),
            20: state(20, "unresolved", "pair_bounds_disagree"),
            30: state(30, "eligible"),
        },
    )
    assert result.status == "unresolved"
    assert result.branch == "C"
    assert result.unresolved_ship_id == 20


def test_before_prize_is_never_reached() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[5, 10, 20, 30],
        prize_ship_id=10,
        captor_ship_id=30,
        states={
            5: state(5, "eligible"),
            20: state(20, "no_request"),
        },
    )
    assert result.status == "no_pair"
    assert result.predicted_ship_id is None


def test_pair_exhausted_is_skippable() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[10, 20, 30],
        prize_ship_id=10,
        captor_ship_id=20,
        states={
            30: state(30, "pair_exhausted"),
        },
    )
    assert result.status == "no_pair"


def test_reversed_right_capture_geometry_fails_closed() -> None:
    result = MODULE.select_o_then_c_forward(
        order=[20, 10, 30],
        prize_ship_id=10,
        captor_ship_id=20,
        states={30: state(30, "eligible")},
    )
    assert result.status == "unresolved"
    assert result.reason == "unsupported_right_capture_geometry"
