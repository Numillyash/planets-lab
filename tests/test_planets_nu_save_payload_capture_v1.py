"""Safety and browser integration tests for owner-approved full game-data captures.

A fake JS browser tests the live hooks: NO calls to the real Planets.nu API.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/client/planets_nu_save_payload_capture_v1.js"
TEST = ROOT / "tests/js/test_planets_nu_save_payload_capture_v1.cjs"


def test_real_payload_probe_safety_boundary_and_readme():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "planets-lab.save-payload-capture.v1" in source
    assert "CLIENT_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK" in source
    assert "CLIENT_REQUEST_DIFFERENTIAL_NOT_NUHOST_HOST_VERIFIED" in source
    assert "originalFetch.apply(this, arguments)" in source
    assert "originalSend.apply(this, arguments)" in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "document.cookie" not in source
    assert "sendBeacon" not in source
    assert "window.open(" not in source
    assert "eval(" not in source
    assert "innerHTML" not in source
    assert "api[_-]?key" in source
    assert "save[_-]?key" in source


def test_real_payload_probe_with_fake_browser():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; synthetic browser integration test cannot run")
    result = subprocess.run(
        [node, str(TEST)], cwd=ROOT,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "state differential: OK" in result.stdout
