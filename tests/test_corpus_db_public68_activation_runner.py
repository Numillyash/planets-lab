from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "activate-corpus-db-compact-public68.sh"


def test_public68_activation_runner_syntax_and_guard_defaults() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)

    text = RUNNER.read_text(encoding="utf-8")
    assert "corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb" in text
    assert "5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a" in text
    assert 'CORPUS_DB_ACTIVATE_ARCHIVES:-68' in text
    assert 'CORPUS_DB_ACTIVATE_MEMBERS:-169569' in text
    assert "09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7" in text
    assert "run-corpus-db-shared-read-check.sh" in text
    assert "FAILED_AND_ROLLED_BACK" in text
    assert "ALREADY_ACTIVE_AND_VERIFIED" in text
