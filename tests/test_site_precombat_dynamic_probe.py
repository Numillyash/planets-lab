from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

MODULE_PATH = DIAGNOSTICS / "combat_site_precombat_dynamic_probe.py"
SPEC = importlib.util.spec_from_file_location(
    "combat_site_precombat_dynamic_probe",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

RUNNER = REPO_ROOT / "tools" / "run-site-precombat-dynamic-probe-v1.sh"
WRAPPER = (
    REPO_ROOT / "tools" / "run-site-precombat-dynamic-probe-v1-with-evidence.sh"
)


def test_probe_shell_scripts_are_valid() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)


def test_interesting_raw_keeps_dynamic_and_transfer_fields() -> None:
    raw = {
        "friendlycode": "mkt",
        "torpedos": 20,
        "transferfoo": 7,
        "fighters": 3,
        "irrelevant": 99,
    }
    filtered = MODULE._interesting_raw(raw)
    assert filtered == {
        "fighters": 3,
        "friendlycode": "mkt",
        "torpedos": 20,
        "transferfoo": 7,
    }


def test_probe_is_read_only_and_tracks_initial_provenance() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "_initial_state_before_window" in source
    assert "prewindow_vcr_appearance" in source
    assert "tminus1_prediction" in source
    assert "inbound_transfer_candidates" in source
    assert "friendly_code_mkt" in source
    assert "No rule is promoted" in source
