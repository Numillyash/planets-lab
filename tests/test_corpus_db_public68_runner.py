from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-corpus-db-public68-compact.sh"


def test_public68_runner_shell_syntax_and_safety_defaults() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)

    text = RUNNER.read_text(encoding="utf-8")
    assert "public-short-expansion-with-public36.jsonl" in text
    assert 'CORPUS_DB_PUBLIC68_EXPECTED_COUNT:-68' in text
    assert 'CORPUS_DB_PUBLIC68_STATE_NAME:-compact-public68-resume' in text
    assert 'CORPUS_DB_PUBLIC68_MIN_FREE_GIB:-40' in text
    assert "corpus-v2compact-public68-*.duckdb" in text
    assert "--activate-current" not in text
    assert "run-corpus-db-explicit-shared-read-check.sh" in text
