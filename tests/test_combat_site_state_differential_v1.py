from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

MODULE_PATH = DIAGNOSTICS / "combat_site_state_differential_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "combat_site_state_differential_v1",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

RUNNER = REPO_ROOT / "tools" / "run-site-combat-state-v1.sh"
WRAPPER = REPO_ROOT / "tools" / "run-site-combat-state-v1-with-evidence.sh"


def test_site_state_runner_scripts_are_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)

    runner = RUNNER.read_text(encoding="utf-8")
    assert "combat_site_state_differential_v1.py" in runner
    assert "--start-vcr-id 592" in runner
    assert "--end-vcr-id 595" in runner
    assert "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c" in runner

    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert "site-combat-state-v1" in wrapper
    assert "artifacts/combat/site-state" in wrapper


def test_capture_side_detection_is_explicit() -> None:
    current = {
        "vcr_id": 592,
        "left_ship_id": 184,
        "right_ship_id": 140,
    }
    assert MODULE._capture_side(current, prize_ship_id=140) == "right"
    assert MODULE._capture_side(current, prize_ship_id=184) == "left"


def test_compare_requires_pair_and_side_exact() -> None:
    predicted = {
        "pair": [140, 170],
        "left_ship_id": 140,
        "right_ship_id": 170,
    }
    factual = {
        "pair": (170, 140),
        "left_ship_id": 140,
        "right_ship_id": 170,
    }
    exact = MODULE._compare(predicted, factual)
    assert exact["pair_exact"] is True
    assert exact["side_exact"] is True
    assert exact["exact"] is True


def test_stateful_differential_uses_carried_state_for_parent_selection() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "SiteCombatState" in source
    assert "apply_site_terminal_batch" in source
    assert "record_factual_site_pair" in source
    assert "parent_queue_active_ship_ids(state)" in source
    assert "select_temporary_capture_continuation" in source
    assert "select_parent_resume" in source
    assert "CARRIED_STATE_HISTORY_ANCHORED" in source
    assert "site_executor module" in source
    assert "terminal outcomes remain injected" in source


def test_stateful_differential_delegates_input_assembly_to_reusable_adapter() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "site_input_adapter" in source
    assert "build_post_capture_candidate_states" in source
    assert "build_parent_standard_pair_inputs" in source
    assert "baseline_module._candidate_input" in source
    assert "_immediate_candidate_states" not in source
    assert "_pair_inputs_for_parent" not in source
    assert "reusable evidence-scoped site_input_adapter" in source
