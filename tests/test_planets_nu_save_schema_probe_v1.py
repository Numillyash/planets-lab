"""Integration gate for the opt-in save-schema browser observer."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/client/planets_nu_save_schema_probe_v1.js"
JS_TEST = ROOT / "tests/js/test_planets_nu_save_schema_probe_v1.cjs"


def test_save_probe_has_no_network_sender_or_persistence():
    text = SOURCE.read_text(encoding="utf-8")
    assert "game/save" in text
    assert "schema-only" in text.lower() or "schema_only" in text.lower()
    assert "report()" in text
    assert "stop()" in text
    assert "localStorage.setItem" not in text
    assert "sendBeacon" not in text
    assert "JSON.stringify(events)" not in text
    assert "document.cookie" not in text
    assert "sessionStorage" not in text
    assert "innerHTML" not in text
    assert "window.open(" not in text
    assert "XMLHttpRequest()" not in text
    assert "new fetch(" not in text


def test_save_probe_in_synthetic_browser():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node runtime unavailable: JS behavior test not runnable")
    run = subprocess.run(
        [node, str(JS_TEST)], cwd=ROOT, capture_output=True,
        text=True, timeout=20, check=False,
    )
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
    assert "no secret leakage" in run.stdout
