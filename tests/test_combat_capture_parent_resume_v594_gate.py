from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

MODULE_PATH = DIAGNOSTICS / "combat_capture_parent_resume_v594_gate.py"
SPEC = importlib.util.spec_from_file_location(
    "combat_capture_parent_resume_v594_gate",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_filtered_controls_drop_whole_target_turn() -> None:
    controls = {
        ("sig", "dir"): {
            (140, 1, (10, 20)),
            (141, 2, (20, 30)),
            (141, 3, (30, 40)),
            (142, 4, (40, 50)),
        }
    }
    filtered = MODULE._filtered_controls(
        controls,
        excluded_battle_turn=141,
    )
    assert filtered[("sig", "dir")] == {
        (140, 1, (10, 20)),
        (142, 4, (40, 50)),
    }


def test_queue_state_uses_only_history_through_v593() -> None:
    factual = [
        {
            "vcr_id": 590,
            "pair": (10, 20),
            "left_ship_id": 20,
            "right_ship_id": 10,
        },
        {
            "vcr_id": 591,
            "pair": (20, 10),
            "left_ship_id": 10,
            "right_ship_id": 20,
        },
        {
            "vcr_id": 593,
            "pair": (30, 40),
            "left_ship_id": 30,
            "right_ship_id": 40,
        },
        {
            "vcr_id": 594,
            "pair": (50, 60),
            "left_ship_id": 50,
            "right_ship_id": 60,
        },
    ]
    state = MODULE._queue_state_through(
        factual,
        through_vcr_id=593,
    )
    assert state.pair_occurrences == {
        (10, 20): 2,
        (30, 40): 1,
    }
    assert state.first_pass_sides == {
        (10, 20): (20, 10),
        (30, 40): (30, 40),
    }


def test_source_enforces_immediate_continuation_precondition() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED" in source
    assert "PARENT_RESUME_PRECONDITION_NOT_MET" in source
    assert "active_parent_ids.remove(prize_id)" in source


def test_source_keeps_v594_as_post_selection_comparator() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    select_index = source.index("selection = select_next_plain_standard(")
    comparator_index = source.index("# Held-out comparator is opened only after selection")
    assert select_index < comparator_index
    assert "All diplomacy controls from battle turn 141 are removed" in source
    assert "through V593" in source
    assert "solely for comparison" in source
