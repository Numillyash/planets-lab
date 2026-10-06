from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

MODULE_PATH = DIAGNOSTICS / "combat_capture_mutable_site_loop_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "combat_capture_mutable_site_loop_v1",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_c_prediction_flips_prize_side_from_capture() -> None:
    immediate = {
        "capture": {"prize_ship_id": 140},
        "selection": {
            "branch": "C",
            "predicted_ship_id": 170,
        },
    }
    current = {
        "vcr_id": 592,
        "left_ship_id": 184,
        "right_ship_id": 140,
    }
    predicted = MODULE._c_prediction(
        current=current,
        immediate=immediate,
    )
    assert predicted["pair"] == [140, 170]
    assert predicted["capture_side"] == "right"
    assert predicted["prize_next_side"] == "left"
    assert predicted["left_ship_id"] == 140
    assert predicted["right_ship_id"] == 170


def test_c_prediction_refuses_unvalidated_o_branch() -> None:
    immediate = {
        "capture": {"prize_ship_id": 140},
        "selection": {
            "branch": "O",
            "predicted_ship_id": 170,
        },
    }
    current = {
        "vcr_id": 592,
        "left_ship_id": 184,
        "right_ship_id": 140,
    }
    try:
        MODULE._c_prediction(
            current=current,
            immediate=immediate,
        )
    except ValueError as exc:
        assert "supports independently covered C branch only" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_compare_requires_pair_and_side_exact() -> None:
    predicted = {
        "pair": [140, 170],
        "left_ship_id": 140,
        "right_ship_id": 170,
    }
    factual = {
        "vcr_id": 593,
        "pair": (170, 140),
        "left_ship_id": 140,
        "right_ship_id": 170,
    }
    exact = MODULE._compare(predicted, factual)
    assert exact["pair_exact"] is True
    assert exact["side_exact"] is True
    assert exact["exact"] is True

    flipped = dict(factual)
    flipped["left_ship_id"] = 170
    flipped["right_ship_id"] = 140
    mismatch = MODULE._compare(predicted, flipped)
    assert mismatch["pair_exact"] is True
    assert mismatch["side_exact"] is False
    assert mismatch["exact"] is False


def test_loop_source_preserves_history_anchored_boundary() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "COMPOSITIONAL_HISTORY_ANCHORED" in source
    assert "does not generate combat terminal outcomes" in source
    assert "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED" in source
    assert "PARENT_RESUME_EXACT" in source
    assert "SITE_LOOP_EXACT" in source
