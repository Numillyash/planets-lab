from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-public-postindependent-prospective-validation.sh"
WRAPPER = (
    REPO_ROOT
    / "tools"
    / "run-public-postindependent-prospective-validation-with-evidence.sh"
)
CLEANUP = REPO_ROOT / "tools" / "cleanup-public100-source-archives.sh"


def test_public100_prospective_runner_is_frozen_and_explicit() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    subprocess.run(["bash", "-n", str(CLEANUP)], check=True)

    runner = RUNNER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    cleanup = CLEANUP.read_text(encoding="utf-8")

    assert "public-postindependent-validation-selected.jsonl" in runner
    assert "public-postindependent-validation-games.jsonl" in runner
    assert "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb" in runner
    assert "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c" in runner
    assert "--corpus-db-generation" in runner
    assert "--partition prospective" in runner
    assert "INSUFFICIENT_DISCRIMINATOR_COVERAGE" in runner
    assert "PASS_PROSPECTIVE_VALIDATION" in runner
    assert "fresh_numeric_kill_left" in runner
    assert "fresh_numeric_nonkill_left" in runner

    assert "46bcb08c2f0d3f0449b97921edb03ab6647f7d3b" in wrapper
    assert "git diff --quiet" in wrapper
    assert "combat_public_capture_side_postindependent_candidate.py" in wrapper

    assert "expected exactly 100 public100 game IDs" in cleanup
    assert "DRY RUN ONLY." in cleanup
    assert "--apply" in cleanup
    assert "sha256sum" in cleanup
    assert "game-${game_id}.zip" in cleanup
