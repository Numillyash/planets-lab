from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "postcapture_occurrence_candidates.py"
)
SPEC = importlib.util.spec_from_file_location(
    "postcapture_occurrence_candidates",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)


def c(
    ship_id: int,
    priority: tuple[int, int, int],
    pair_occurrences: int,
    appearances: int,
):
    return MODEL.Candidate(
        ship_id=ship_id,
        priority=priority,
        pair_occurrences=pair_occurrences,
        attacker_appearances=appearances,
    )


def test_static_priority_reproduces_rank1_residual_shape() -> None:
    rows = [
        c(198, (3, 198, 0), 1, 2),
        c(467, (3, 467, 0), 0, 0),
    ]
    assert MODEL.select_static_priority(rows).ship_id == 198
    assert MODEL.select_pair_occurrence_round(rows).ship_id == 467


def test_pair_round_preserves_static_priority_inside_same_round() -> None:
    rows = [
        c(300, (3, 300, 0), 0, 2),
        c(200, (3, 200, 0), 0, 5),
    ]
    assert MODEL.select_pair_occurrence_round(rows).ship_id == 200


def test_pair_round_prefers_fresh_pair_over_higher_static_priority() -> None:
    rows = [
        c(100, (0, 1, 100), 1, 1),
        c(900, (4, 900, 0), 0, 4),
    ]
    assert MODEL.select_pair_occurrence_round(rows).ship_id == 900


def test_pair_cap_excludes_third_occurrence_candidate() -> None:
    rows = [
        c(100, (0, 1, 100), 2, 0),
        c(200, (4, 200, 0), 0, 0),
    ]
    assert MODEL.select_static_priority(rows).ship_id == 100
    assert MODEL.select_static_cap2(rows).ship_id == 200
    assert MODEL.select_pair_occurrence_round(rows).ship_id == 200


def test_attacker_freshness_can_diverge_from_pair_round() -> None:
    rows = [
        # Ship 100 fought someone else, but never this prize.
        c(100, (3, 100, 0), 0, 3),
        # Ship 200 has never appeared and also has a fresh pair.
        c(200, (3, 200, 0), 0, 0),
    ]
    assert MODEL.select_pair_occurrence_round(rows).ship_id == 100
    assert MODEL.select_fresh_attacker_boolean(rows).ship_id == 200
    assert MODEL.select_attacker_appearance_count(rows).ship_id == 200


def test_boolean_and_count_freshness_can_diverge() -> None:
    rows = [
        c(100, (3, 100, 0), 0, 5),
        c(200, (3, 200, 0), 0, 1),
    ]
    assert MODEL.select_fresh_attacker_boolean(rows).ship_id == 100
    assert MODEL.select_attacker_appearance_count(rows).ship_id == 200
