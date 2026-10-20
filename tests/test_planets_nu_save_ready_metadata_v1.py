"""Passive metadata-only save/ready sequence probe integration controls."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/client/planets_nu_save_ready_metadata_v1.js"
TEST = ROOT / "tests/js/test_planets_nu_save_ready_metadata_v1.cjs"


def test_metadata_probe_safety_contract():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "planets-lab.client-save-ready-metadata.v1" in source
    assert "CLIENT_SEQUENCE_OBSERVED_NOT_NUHOST_ORDER_RECEIPT" in source
    assert "UNWITNESSED_CLIENT_PERFORMANCE_CLOCK" in source
    assert "candidate_ordered_client_sequences_not_host_verified" in source
    assert "independently_witnessed_host_start: false" in source
    assert "verified_server_order_acceptance: false" in source
    assert "nuhost_execution_verified: false" in source
    assert "originalFetch.apply(this, arguments)" in source
    assert "originalSend.apply(this, arguments)" in source
    assert "response.clone().text()" in source
    for forbidden in (
        "localStorage", "sessionStorage", "document.cookie",
        "sendBeacon(", "navigator.sendBeacon", "window.open(",
        "eval(", "innerHTML", "XMLHttpRequest()", "fetch('",
    ):
        assert forbidden not in source


def test_synthetic_browser_order_timeline_and_no_payload_exposure():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node not present; fake browser scenario is not runnable")
    result = subprocess.run(
        [node, str(TEST)],
        capture_output=True, text=True, timeout=30, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "synthetic browser tests: OK" in result.stdout
