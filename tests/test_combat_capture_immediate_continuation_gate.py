from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

MODULE_PATH = DIAGNOSTICS / "combat_capture_immediate_continuation_gate.py"
SPEC = importlib.util.spec_from_file_location(
    "combat_capture_immediate_continuation_gate",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_fixture_order_is_unique_for_game400330_turn141() -> None:
    order = MODULE._fixture_order(game_id=400330, turn=141)
    assert order == (
        421,
        296,
        216,
        140,
        170,
        382,
        471,
        134,
        184,
        195,
        280,
        285,
        330,
    )


def test_pair_occurrences_stop_at_capture_vcr() -> None:
    queue = [
        {"vcr_id": 590, "pair": (10, 20)},
        {"vcr_id": 591, "pair": (20, 10)},
        {"vcr_id": 592, "pair": (10, 30)},
        {"vcr_id": 593, "pair": (30, 40)},
        {"vcr_id": 594, "pair": (30, 40)},
    ]
    counts = MODULE._pair_occurrences(queue, through_vcr_id=593)
    assert counts == {
        (10, 20): 2,
        (10, 30): 1,
        (30, 40): 1,
    }


def test_gate_uses_sentinel_not_heldout_opponent_identity() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "SENTINEL_HELDOUT_OPPONENT_ID" in source
    assert '"current_opponent_ship_id": SENTINEL_HELDOUT_OPPONENT_ID' in source
    assert "HELD_OUT_NEXT_PAIR_NOT_USED" in source
    assert "No VCR N+1 ship id, pair, side or terminal state is consumed" in source


def test_gate_has_parent_resume_terminal_status() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED" in source
    assert "IMMEDIATE_CONTINUATION_RESOLVED" in source
    assert "IMMEDIATE_CONTINUATION_UNRESOLVED" in source
