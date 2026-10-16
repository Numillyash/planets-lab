"""CI checks the standalone owner bundle runner, even without pytest installed."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/planetary_owner_bundle_v1.py"
RUNNER = ROOT / "tools/run-planetary-owner-capture-bundle-v1.sh"
WRAPPER = ROOT / "tools/run-planetary-owner-capture-bundle-v1-with-evidence.sh"


def test_no_pytest_dependency_or_private_order_publication(tmp_path):
    path = tmp_path / "report.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT / "src"), str(ROOT / "tools/diagnostics"))
    )
    code = (
        "import sys,runpy;"
        "sys.modules['pytest']=None;"
        f"sys.argv=[{str(SCRIPT)!r},'--output',{str(path)!r}];"
        f"runpy.run_path({str(SCRIPT)!r},run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env,
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["schema"] == "planets-lab.prehost-owner-bundle-controls.v1"
    assert report["summary"]["complete_bundle_accepted"] is True
    assert report["summary"]["missing_player_abstains"] is True
    assert report["summary"]["abstain_controls_passed"] == 8
    assert report["summary"]["placement_count"] == 2
    assert report["summary"]["NuHost_orders_authenticated"] is False
    assert report["summary"]["independent_clock_provenance_verified"] is False
    assert report["summary"]["corpus_files_opened"] == 0
    assert all(v.startswith("ABSTAIN_") for v in report["controls"].values())
    raw = path.read_text(encoding="utf-8")
    for secret in ("research-player1-key-only", "research-player2-key-only",
                   "planet_transfer", "player_orders", "tag_hex"):
        assert secret not in raw
    assert not list(path.parent.glob("*.tmp"))


def test_shell_wrappers_are_noninvasive():
    for path in (RUNNER, WRAPPER):
        subprocess.run(["bash", "-n", str(path)], check=True)
    runner = RUNNER.read_text()
    wrapper = WRAPPER.read_text()
    assert "site-state-v1" in runner
    assert "planetary_owner_bundle_v1.py" in runner
    assert "-m pytest" not in runner
    assert "planets-corpus-db" not in runner
    assert "--activate-current" not in runner
    assert "run-with-runtime-evidence.sh" in wrapper
    assert "--include artifacts/planetary/owner-capture-bundle-v1/published" in wrapper
