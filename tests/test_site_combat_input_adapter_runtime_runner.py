from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "tools" / "run-site-combat-input-adapter-v1.sh"
WRAPPER = REPO_ROOT / "tools" / "run-site-combat-input-adapter-v1-with-evidence.sh"


def test_site_input_adapter_runtime_scripts_are_shell_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)


def test_site_input_adapter_runner_reuses_canonical_site_state_gate() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "PLANETS_SITE_INPUT_ADAPTER_RUNTIME_MODE:-local" in source
    assert 'PLANETS_SITE_STATE_RUNTIME_MODE="$RUNTIME_MODE"' in source
    assert "bash tools/run-site-combat-state-v1.sh" in source
    assert "SITE_STATE_EXACT" in source
    assert "SITE_INPUT_ADAPTER_EXACT" in source
    assert '"site_input_adapter" in boundary' in source
    assert '"capture_immediate_C"' in source
    assert '"capture_parent_resume"' in source


def test_site_input_adapter_wrapper_publishes_named_runtime_evidence() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "tools/run-with-runtime-evidence.sh" in source
    assert "site-combat-input-adapter-v1" in source
    assert "artifacts/combat/site-input-adapter" in source
    assert "tools/run-site-combat-input-adapter-v1.sh" in source
