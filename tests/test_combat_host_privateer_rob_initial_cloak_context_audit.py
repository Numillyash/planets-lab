from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_initial_cloak_context_audit import (  # noqa: E402
    _basic_cloak_fuel_cost,
    _distance,
    _focus_kind,
    _stable_owner_hull_identity,
    _within_loki_range,
)


def test_focus_kind_keeps_only_prior_true_clean_initial_rows() -> None:
    assert (
        _focus_kind(
            {
                "target_prior_cloak": "true",
                "initial_context": {"classification": "initial_skip_target_outranks_factual"},
            }
        )
        == "initial_skip_target_outranks_factual"
    )
    assert (
        _focus_kind(
            {
                "target_prior_cloak": "true",
                "initial_context": {"classification": "initial_pair_vcr"},
            }
        )
        == "initial_pair_vcr"
    )
    assert (
        _focus_kind(
            {
                "target_prior_cloak": "false",
                "initial_context": {"classification": "initial_pair_vcr"},
            }
        )
        is None
    )
    assert (
        _focus_kind(
            {
                "target_prior_cloak": "true",
                "initial_context": {"classification": "initial_skip_target_not_above_factual"},
            }
        )
        is None
    )


def test_loki_range_is_inclusive_at_ten_lightyears() -> None:
    assert _distance((0, 0), (6, 8)) == 10.0
    assert _within_loki_range(10.0) is True
    assert _within_loki_range(10.0001) is False
    assert _within_loki_range(None) is None


def test_basic_cloak_fuel_cost_uses_documented_minimum() -> None:
    assert _basic_cloak_fuel_cost(55) == 5
    assert _basic_cloak_fuel_cost(90) == 5
    assert _basic_cloak_fuel_cost(421) == 21
    assert _basic_cloak_fuel_cost(None) is None


def test_stable_owner_hull_identity_requires_same_owner_and_hull() -> None:
    assert (
        _stable_owner_hull_identity(
            before_owner_id=5,
            before_hull_id=46,
            after_owner_id=5,
            after_raw={"hullid": 46},
        )
        is True
    )
    assert (
        _stable_owner_hull_identity(
            before_owner_id=5,
            before_hull_id=46,
            after_owner_id=6,
            after_raw={"hullid": 46},
        )
        is False
    )
    assert (
        _stable_owner_hull_identity(
            before_owner_id=5,
            before_hull_id=46,
            after_owner_id=5,
            after_raw={"hullid": 44},
        )
        is False
    )
