from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "analyze-postcapture-o-c-independent.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_postcapture_o_c_independent",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def qualified_dependency() -> dict:
    return {
        "status": "resolved",
        "factual_opponent_site_predicted": True,
        "factual_opponent_position_source": "stationary_effective_warp_zero",
        "factual_opponent_active": True,
        "factual_opponent_candidate_resolved": True,
        "factual_opponent_requests_new_owner": True,
        "factual_opponent_strict_permission": True,
    }


def row(
    *,
    vcr: int,
    prize: int,
    captor: int,
    factual: int,
    order: list[int],
) -> dict:
    return {
        "game_id": 900001,
        "turn": 10,
        "capture_vcr_id": vcr,
        "next_vcr_id": vcr + 1,
        "captured_ship_id": prize,
        "next_opponent_ship_id": factual,
        "capture_side": "right",
        "factual_prize_side": "right",
        "active_dependency": qualified_dependency(),
        "identity_anchored_result": {
            "external_order": order,
            "capture_cursor": {
                "right_ship_id": prize,
                "left_ship_id": captor,
            },
            "pair_exact": True,
        },
    }


def payload(rows: list[dict]) -> dict:
    return {
        "schema": "planets-lab.combat-public-capture-o-layer-probe.v2.db1",
        "partition": "independent",
        "evidence_status": "INDEPENDENT_VALIDATION_POSTHELDOUT_CANDIDATE",
        "observations": rows,
    }


def test_full_branch_pass() -> None:
    report = MODULE.run(
        payload(
            [
                row(
                    vcr=1,
                    prize=10,
                    captor=20,
                    factual=30,
                    order=[10, 20, 30],
                ),
                row(
                    vcr=3,
                    prize=40,
                    captor=60,
                    factual=50,
                    order=[40, 50, 60],
                ),
            ]
        )
    )
    assert report["status"] == "PASS_FULL_BRANCH_COVERAGE"
    summary = report["summary"]
    assert summary["qualified_o_after_captor"] == 1
    assert summary["qualified_c_between_prize_and_captor"] == 1
    assert summary["qualified_forward_union_covered"] == 2


def test_before_prize_is_counterexample() -> None:
    report = MODULE.run(
        payload(
            [
                row(
                    vcr=1,
                    prize=20,
                    captor=30,
                    factual=10,
                    order=[10, 20, 30],
                )
            ]
        )
    )
    assert report["status"] == "FAILED_COUNTEREXAMPLE"
    assert report["summary"]["qualified_before_or_at_prize"] == 1
    assert len(report["qualified_counterexamples"]) == 1
