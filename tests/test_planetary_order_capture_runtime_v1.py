from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/planetary_order_capture_v1.py"
RUNNER = ROOT / "tools/run-planetary-prehost-order-capture-v1.sh"
WRAPPER = ROOT / "tools/run-planetary-prehost-order-capture-v1-with-evidence.sh"


def test_admission_cli_no_pytest_import_or_private_capture_bytes(tmp_path):
    out = tmp_path / "report.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((
        str(ROOT / "src"), str(ROOT / "tools/diagnostics"),
    ))
    code = (
        "import runpy, sys; "
        "sys.modules['pytest'] = None; "
        f"sys.argv=[{str(SCRIPT)!r},'--output',{str(out)!r}]; "
        f"runpy.run_path({str(SCRIPT)!r},run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env=env,
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema"] == "planets-lab.prehost-order-capture-controls.v1"
    assert report["summary"]["abstention_controls_passed"] == 8
    assert report["summary"]["modeled_placement_count"] == 2
    assert not report["summary"]["actual_NuHost_order_submission_authenticated"]
    assert not report["summary"]["historical_differential_verified"]
    assert not report["summary"]["capture_timestamp_independently_attested"]
    assert report["summary"]["corpus_files_opened"] == 0
    assert all(x.startswith("ABSTAIN_") for x in report["abstention_controls"].values())
    data = out.read_text(encoding="utf-8")
    assert "synthetic-operator-key-never-for-production" not in data
    assert "planet_transfer" not in data
    assert '"orders"' not in data
    assert not list(out.parent.glob("*.tmp"))


def test_capture_runner_shell_and_separate_runtime_evidence_wrapper():
    for script in (RUNNER, WRAPPER):
        subprocess.run(["bash", "-n", str(script)], check=True)
    runner = RUNNER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert "planetary_order_capture_v1.py" in runner
    assert "python -m pytest" not in runner
    assert "-m pytest" not in runner
    assert "site-state-v1" in runner
    assert "activate-current" not in runner
    assert "planets-corpus-db" not in runner
    assert "run-with-runtime-evidence.sh" in wrapper
    assert "--include artifacts/planetary/prehost-order-capture-v1/published" in wrapper
