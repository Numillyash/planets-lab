from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = (
    REPO_ROOT
    / "tools"
    / "research"
    / "run-postcapture-o-c-forward-independent-with-evidence.sh"
)


def test_o_c_forward_independent_evidence_wrapper_is_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    text = WRAPPER.read_text(encoding="utf-8")
    assert "postcapture-o-c-forward-independent" in text
    assert (
        "artifacts/external-sources/postcapture-occurrence/fresh32-independent"
        in text
    )
    assert "run-postcapture-o-c-forward-independent.sh" in text
