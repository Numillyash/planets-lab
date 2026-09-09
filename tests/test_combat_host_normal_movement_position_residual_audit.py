from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_normal_movement_position_residual_audit import (  # noqa: E402
    POSITION_SCHEMA,
    _boolish,
    _candidate_families,
    _find_named_setting,
    _mismatch_rows,
)


def _report(*, mismatch_count: int, examples: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": POSITION_SCHEMA,
        "summary": {"ship_occurrences": {"position_mismatch": mismatch_count}},
        "examples": examples,
    }


def test_mismatch_rows_requires_complete_example_population() -> None:
    rows = _mismatch_rows(
        _report(
            mismatch_count=2,
            examples=[{"ship_id": 1}, {"ship_id": 2}],
        )
    )
    assert [row["ship_id"] for row in rows] == [1, 2]

    with pytest.raises(ValueError, match="does not contain every mismatch example"):
        _mismatch_rows(
            _report(
                mismatch_count=2,
                examples=[{"ship_id": 1}],
            )
        )


def test_mismatch_rows_rejects_wrong_schema() -> None:
    with pytest.raises(ValueError, match="position report schema"):
        _mismatch_rows(
            {
                "schema": "wrong",
                "summary": {"ship_occurrences": {"position_mismatch": 0}},
                "examples": [],
            }
        )


def test_candidate_families_collapse_storm_modes_but_keep_other_mechanics() -> None:
    assert _candidate_families(
        (
            "ion_storm_nu_candidate:ion_storm_drag",
            "ion_storm_classic_candidate:ion_storm_drag",
            "mine:normal_mine_hit_scaled_floor_exact",
            "observed_tow_route",
        )
    ) == ("ion_storm", "mine", "tow")


def test_boolish_and_recursive_setting_lookup_are_fail_closed() -> None:
    payload = {
        "settings": {"nuIonStorms": "true"},
        "nested": [{"nu-ion-storms": 1}],
    }
    values = _find_named_setting(payload, "nuionstorms")
    assert values == ["true", 1]
    assert {_boolish(value) for value in values} == {True}
    assert _boolish("maybe") is None
    assert _boolish(2) is None
