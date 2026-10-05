from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "probe-postcapture-o-c-forward-independent.py"
)
SPEC = importlib.util.spec_from_file_location(
    "probe_postcapture_o_c_forward_independent",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def report(
    *,
    total: int,
    resolved: int,
    exact: int,
    mismatch: int = 0,
    unresolved: int = 0,
    no_pair: int = 0,
    o_branch: int = 0,
    c_branch: int = 0,
) -> dict:
    return {
        "frozen_qualified_rows": total,
        "summary": {
            "counts": {
                "primary:status:resolved": resolved,
                "primary:exact": exact,
                "primary:mismatch": mismatch,
                "primary:status:unresolved": unresolved,
                "primary:status:no_pair": no_pair,
                "primary:branch:O": o_branch,
                "primary:branch:C": c_branch,
            }
        },
    }


def test_full_branch_pass() -> None:
    status, gate = MODULE._gate_status(
        report(total=4, resolved=4, exact=4, o_branch=2, c_branch=2)
    )
    assert status == "PASS_FULL_BRANCH_COVERAGE"
    assert gate["all_exact"] is True
    assert gate["full_branch_coverage"] is True


def test_partial_branch_pass() -> None:
    status, gate = MODULE._gate_status(
        report(total=3, resolved=3, exact=3, o_branch=3, c_branch=0)
    )
    assert status == "PASS_PARTIAL_BRANCH_COVERAGE"
    assert gate["all_exact"] is True
    assert gate["full_branch_coverage"] is False


def test_mismatch_fails() -> None:
    status, _gate = MODULE._gate_status(
        report(
            total=3,
            resolved=3,
            exact=2,
            mismatch=1,
            o_branch=1,
            c_branch=2,
        )
    )
    assert status == "FAILED_MISMATCH"


def test_unresolved_is_incomplete() -> None:
    status, _gate = MODULE._gate_status(
        report(
            total=3,
            resolved=2,
            exact=2,
            unresolved=1,
            o_branch=1,
            c_branch=1,
        )
    )
    assert status == "INCOMPLETE_UNRESOLVED"


def test_empty_is_insufficient() -> None:
    status, _gate = MODULE._gate_status(
        report(total=0, resolved=0, exact=0)
    )
    assert status == "INSUFFICIENT_NO_COMPARABLE_ROWS"
