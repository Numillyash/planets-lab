from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-site-combat-terminal-replay-v1.sh"
WRAPPER = (
    REPO_ROOT / "tools" / "run-site-combat-terminal-replay-v1-with-evidence.sh"
)


def test_terminal_replay_runtime_scripts_are_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)


def test_terminal_replay_runner_reuses_canonical_site_differential() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "PLANETS_SITE_STATE_TERMINAL_SOURCE=replay" in source
    assert "bash tools/run-site-combat-state-v1.sh" in source
    assert "SITE_TERMINAL_REPLAY_EXACT" in source
    assert "current_vcr_replay_carried_overlay" in source
    assert "current_vcr_start_exact_transitions" in source
    assert "next_vcr_start_exact_transitions" in source
    assert "site_terminal_adapter" in source


def test_terminal_replay_wrapper_publishes_named_runtime_evidence() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "tools/run-with-runtime-evidence.sh" in source
    assert "site-combat-terminal-replay-v1" in source
    assert "artifacts/combat/site-terminal-replay" in source
    assert "tools/run-site-combat-terminal-replay-v1.sh" in source
