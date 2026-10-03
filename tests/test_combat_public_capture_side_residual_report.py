from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools/diagnostics/combat_public_capture_side_residual_report.py"
)
SPEC = importlib.util.spec_from_file_location(
    "combat_public_capture_side_residual_report",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_identity_residuals_keeps_mismatch_and_resolved_null_split() -> None:
    payload = {
        "observations": [
            {
                "identity_anchored_split": {"exact": True},
                "identity_anchored_result": {"status": "resolved"},
            },
            {
                "identity_anchored_split": {"exact": False},
                "identity_anchored_result": {"status": "resolved"},
            },
            {
                "identity_anchored_split": None,
                "identity_anchored_result": {"status": "resolved"},
            },
            {
                "identity_anchored_split": None,
                "identity_anchored_result": {"status": "not_comparable"},
            },
        ]
    }

    rows = MODULE._identity_residuals(payload)
    assert len(rows) == 2
    assert rows[0]["identity_anchored_split"]["exact"] is False
    assert rows[1]["identity_anchored_split"] is None


def test_defaults_point_at_existing_local_residual_artifacts(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["combat_public_capture_side_residual_report.py"],
    )
    args = MODULE.parse_args()
    assert args.mismatch_report.name == "heldout-residual-476380.json"
    assert (
        args.repeated_capture_report.name
        == "heldout-residual-257776.json"
    )
