from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-public-capture-side-independent-validation.sh"
WRAPPER = (
    REPO_ROOT
    / "tools"
    / "run-public-capture-side-independent-validation-with-evidence.sh"
)


def test_independent_capture_side_runner_syntax_and_frozen_boundaries() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)

    runner = RUNNER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert "public-short-expansion-selected.jsonl" in runner
    assert "public-short-expansion-games.jsonl" in runner
    assert "public-validation-selected.jsonl" in runner
    assert "--partition all" in runner
    assert "--partition independent" in runner
    assert "baseline_overlap" in runner
    assert "expected 32 independent games" in runner
    assert "corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb" in runner
    assert "PASS_FULL_BRANCH_COVERAGE" in runner
    assert "PASS_PARTIAL_BRANCH_COVERAGE" in runner
    assert "FAILED_MISMATCH" in runner
    assert "INCOMPLETE_UNRESOLVED" in runner
    assert "promotion_ready" in runner

    assert 'SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"' in wrapper
    assert 'SOURCE_BRANCH" != "main"' in wrapper
    assert "592607b07efa0f857521da05fe0651127ed8be2d" in wrapper
    assert "git merge-base --is-ancestor" in wrapper
    assert "public-capture-side-independent-validation" in wrapper
    assert "--include artifacts/public-capture-side" in wrapper
