"""Host-python integration regressions for the completed but invalidated v6 run.

No corpus reads or real Host actions; only published sanitized v5 counters.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.diagnostics.validate_minefield_joint_v6 import JOINT

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/validate_minefield_joint_v6.py"
BASE = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
RUNNER = ROOT / "tools/run-public100-baseline68-mine-joint-v6.sh"

def run_cli(*args: str, cwd: Path):
    # No site-packages, editable installation, cwd import, or PYTHONPATH.
    return subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, timeout=15, check=False,
    )

def source_projection():
    payload = json.loads(BASE.read_text(encoding="utf-8"))
    mine = payload["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
    # Explicitly SYNTHETIC compatible extension to old published margins.
    mine.update(dict(zip(JOINT, (100, 30, 40, 30, 70))))
    return payload

def test_host_isolated_python_selftest_does_not_depend_on_repo_cwd_or_installed_package(tmp_path):
    result = run_cli("--self-test", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "PASS_V6_HOST_VALIDATOR_SELF_TEST_SYNTHETIC_ONLY"
    assert result.stderr == ""

def test_isolated_host_command_can_validate_synthetic_full_aggregate(tmp_path):
    fixture = tmp_path / "published-counts.json"
    fixture.write_text(json.dumps(source_projection()), encoding="utf-8")
    result = run_cli("--input", str(fixture), cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS_SOURCE_JOINT_NONCAUSAL" in result.stdout
    assert "fresh_own_stable_centre_units_changed=70" in result.stdout
    assert "host_phase_diff_verified=false" in result.stdout

@pytest.mark.parametrize("mutate", [
    lambda x: x["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda x: x["generation"].update(read_only=False),
    lambda x: x["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(
        same_id_fresh_own_center_stable_units_changed_joint_not_causal=71),
    lambda x: x["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(
        same_id_fresh_own_center_stable_units_decreased_joint_not_causal=True),
])
def test_isolated_host_command_fails_closed_without_source_leak(tmp_path,mutate):
    payload=source_projection()
    payload["unpublished_sensitive_identifier"]="SHOULD_NEVER_PRINT_8898"
    mutate(payload)
    inp=tmp_path / "bad.json"
    inp.write_text(json.dumps(payload), encoding="utf-8")
    result=run_cli("--input", str(inp),cwd=tmp_path)
    assert result.returncode==2
    assert result.stdout.strip()=="ABSTAIN_V6_VALIDATION"
    assert "SHOULD_NEVER_PRINT" not in result.stdout+result.stderr

def test_selftest_refuses_input_and_missing_normal_input(tmp_path):
    for args in (("--self-test","--input","some.json"),tuple()):
        result=run_cli(*args,cwd=tmp_path)
        assert result.returncode==2
        assert "ABSTAIN" in result.stdout
        assert result.stderr==""

def test_runner_runs_host_preflight_before_costly_deep_m2_and_exports_only_valid_report():
    source=RUNNER.read_text(encoding="utf-8")
    assert source.index("stage=host_joint_validator_self_test") < source.index(
        "stage=deep_m2_100_metadata_68_baseline"
    )
    assert "python3 -I -S tools/diagnostics/validate_minefield_joint_v6.py --self-test" in source
    assert "python3 -I -S tools/diagnostics/validate_minefield_joint_v6.py" in source
    assert "ABSTAIN_GENERIC_AGGREGATE_VALIDATION" in source
    assert "ABSTAIN_JOINT_AGGREGATE_VALIDATION" in source
    assert "ABSTAIN_ECONOMY_GENERATION" in source
    assert 'rm -f "$REPORT"' in source
    assert source.index('rm -f "$REPORT"\nfi') < source.index('echo "stage=deep_m2 result=')
    assert subprocess.run(["bash","-n",str(RUNNER)],capture_output=True).returncode==0
