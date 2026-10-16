"""Guard standalone M2 evidence generation against accidental pytest dependency."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/planetary_order_aware_slice_v1.py"
RUNNER = ROOT / "tools/run-planetary-order-aware-slice-v1.sh"
WRAPPER = ROOT / "tools/run-planetary-order-aware-slice-v1-with-evidence.sh"


def test_runtime_cli_executes_even_if_pytest_import_is_blocked(tmp_path):
    output = tmp_path / "published" / "report.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((
        str(ROOT / "src"), str(ROOT / "tools/diagnostics"),
    ))
    # This accurately catches any direct or transitive 'import pytest'
    # in the runtime script or the shared scenarios.
    code = (
        "import runpy, sys; "
        "sys.modules['pytest'] = None; "
        f"sys.argv = [{str(SCRIPT)!r}, '--output', {str(output)!r}]; "
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    run = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                         env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "M2_ORDER_AWARE_INTERNAL_TESTED_NOT_NUHOST_DIFFERENTIAL"
    summary = report["summary"]
    assert summary["runtime_self_checks_passed"] is True
    assert summary["runtime_abstention_controls_passed"] == 8
    assert summary["modeled_turns_per_placement"] == 3
    assert summary["phase_balances_per_turn"] == 15
    assert summary["NuHost_phase_order_verified"] is False
    assert len(report["abstention_controls"]) == 8
    assert all(status == "ABSTAIN_UNSUPPORTED_OR_INVALID"
               for status in report["abstention_controls"].values())
    assert len(report["traces"]) == 2
    assert not list(output.parent.glob("*.tmp"))


def test_runner_does_not_require_pytest_or_alter_corpus():
    for script in (RUNNER, WRAPPER):
        subprocess.run(["bash", "-n", str(script)], check=True)
    runner = RUNNER.read_text(encoding="utf-8")
    assert "planetary_order_aware_slice_v1.py" in runner
    assert '"$PYTHON" -m pytest' not in runner
    assert "site-state-v1" in runner
    assert "runtime: dependency-free scenario acceptance" in runner
    assert "activate-current" not in runner
    assert "corpus-db" not in runner
    assert "run-with-runtime-evidence.sh" in WRAPPER.read_text(encoding="utf-8")
