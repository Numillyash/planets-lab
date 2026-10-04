from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-public-postindependent-validation-acquisition.sh"
WRAPPER = (
    REPO_ROOT
    / "tools"
    / "run-public-postindependent-validation-acquisition-with-evidence.sh"
)


def test_postindependent_validation_acquisition_profile_is_frozen() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)

    runner = RUNNER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert "public-short-expansion-with-public36.jsonl" in runner
    assert "public-postindependent-validation-selected.jsonl" in runner
    assert "public-postindependent-validation-games.jsonl" in runner
    assert 'MIN_TURN="${MIN_TURN:-80}"' in runner
    assert 'MAX_TURN="${MAX_TURN:-180}"' in runner
    assert 'MIN_SLOTS="${MIN_SLOTS:-8}"' in runner
    assert 'MAX_SLOTS="${MAX_SLOTS:-16}"' in runner
    assert 'PROBE_LIMIT="${PROBE_LIMIT:-320}"' in runner
    assert 'SELECT_COUNT="${SELECT_COUNT:-32}"' in runner
    assert 'baseline_count" != "68"' in runner

    assert 'SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"' in wrapper
    assert 'SOURCE_BRANCH" != "main"' in wrapper
    assert "46bcb08c2f0d3f0449b97921edb03ab6647f7d3b" in wrapper
    assert "git merge-base --is-ancestor" in wrapper
    assert "git diff --quiet" in wrapper
    assert "combat_public_capture_side_postindependent_candidate.py" in wrapper
    assert "public-postindependent-validation-acquisition" in wrapper
    assert "--include artifacts/public-postindependent-validation" in wrapper
