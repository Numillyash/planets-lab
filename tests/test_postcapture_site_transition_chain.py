from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools" / "research"
PROBE = TOOLS_DIR / "probe-postcapture-site-transition-chain.py"
RUNNER = TOOLS_DIR / "run-postcapture-site-transition-chain.sh"
WRAPPER = TOOLS_DIR / "run-postcapture-site-transition-chain-with-evidence.sh"


def _load_probe():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location(
        "probe_postcapture_site_transition_chain",
        PROBE,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_site_transition_scripts_are_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    runner = RUNNER.read_text(encoding="utf-8")
    assert "game400330-t141-v592-595.json" in runner
    assert "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb" in runner
    assert "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c" in runner


def test_selector_case_adapter_preserves_dispositions() -> None:
    module = _load_probe()
    report = {
        "cases": [
            {
                "game_id": 1,
                "turn": 2,
                "capture_vcr_id": 3,
                "primary": {
                    "candidate_details": {
                        "10": {"disposition": "eligible", "reason": None},
                        "20": {
                            "disposition": "no_request",
                            "reason": "candidate_does_not_request_new_owner",
                        },
                    }
                },
            }
        ]
    }
    cases = module._selector_case_map(report)
    case = cases[(1, 2, 3)]
    states = module._candidate_states_from_case(case)
    assert states[10].disposition == "eligible"
    assert states[20].disposition == "no_request"
    assert states[20].reason == "candidate_does_not_request_new_owner"


def test_capture_context_rejects_mismatched_prize() -> None:
    module = _load_probe()
    case = {
        "captured_ship_id": 10,
        "captor_ship_id": 30,
        "external_order": [10, 20, 30],
        "primary": {
            "candidate_details": {
                "20": {"disposition": "eligible", "reason": None},
            }
        },
    }
    try:
        module._capture_context(
            selector_case=case,
            prize_ship_id=11,
            captor_ship_id=30,
        )
    except ValueError as exc:
        assert "prize mismatch" in str(exc)
    else:
        raise AssertionError("expected ValueError")
