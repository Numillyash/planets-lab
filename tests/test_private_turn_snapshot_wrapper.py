from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "tools" / "run-private-turn-snapshot.sh"


def test_private_snapshot_wrapper_is_shell_valid_and_secret_safe() -> None:
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    text = WRAPPER.read_text(encoding="utf-8")
    assert "PLANETSNU_API_KEY is not set" in text
    assert "-e PLANETSNU_API_KEY" in text
    assert "python -m planets_lab.corpus.private_turn_snapshot_cli" in text
    assert "echo $PLANETSNU_API_KEY" not in text
    assert "set -x" not in text
