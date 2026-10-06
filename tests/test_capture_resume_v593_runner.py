from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-capture-resume-v593-gate.sh"
WRAPPER = REPO_ROOT / "tools" / "run-capture-resume-v593-gate-with-evidence.sh"


def test_capture_resume_wrappers_are_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)

    runner = RUNNER.read_text(encoding="utf-8")
    assert "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb" in runner
    assert "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c" in runner
    assert "--capture-vcr-id 593" in runner
    assert "combat_capture_immediate_continuation_gate.py" in runner

    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert "capture-resume-v593" in wrapper
    assert "artifacts/combat/capture-resume" in wrapper
