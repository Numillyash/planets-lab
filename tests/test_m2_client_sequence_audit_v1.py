"""V1 metadata-only client chronology: independent cross-language audit."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from planets_lab.sim.planetary_client_sequence_audit import (
    ClientSequenceInvalid, audit_atomic_metadata_bundle, safe_metadata_summary,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "diagnostics"))
from m2_client_sequence_audit_v1 import fake_browser_bundle


@pytest.fixture(scope="module")
def synthetic_bundle():
    if shutil.which("node") is None:
        pytest.skip("Node.js unavailable")
    return fake_browser_bundle()


def test_cross_language_valid_fake_browser_bundle_is_self_consistent(synthetic_bundle):
    result = audit_atomic_metadata_bundle(synthetic_bundle)
    assert result.status == "SELF_CONSISTENT_CLIENT_METADATA_NOT_NUHOST_VERIFIED"
    assert result.retained_metadata_events == 3
    assert result.total_save_calls == 1
    assert result.total_turnready_calls == 2
    assert result.candidate_ordered_client_sequences_not_host_verified == 1
    assert result.ambiguous_or_unconfirmed_ready_events == 1
    assert result.repeated_ready_without_fresh_save_events == 1
    assert not result.independently_witnessed_host_start
    assert not result.independent_server_order_acceptance_verified
    assert not result.nuhost_execution_verified
    assert not result.raw_client_metadata_returned
    summary = json.dumps(safe_metadata_summary(synthetic_bundle))
    for field in ("events", "started_ms", "settled_ms", "FAKE_BEARER",
                  "FICTIONAL_GAME", "api.planets.nu", "gameid"):
        assert field not in summary


@pytest.mark.parametrize("change", [
    lambda b: b.update(secret="unexpected"),
    lambda b: b["trace"].update(authorization="Bearer confidential"),
    lambda b: b["trace"]["events"][0].update(private_payload="raw"),
    lambda b: b["report"].update(nuhost_execution_verified=True),
    lambda b: b["report"].update(verified_server_order_acceptance=True),
    lambda b: b["report"].update(candidate_ordered_client_sequences_not_host_verified=2),
    lambda b: b["report"].update(dropped_metadata_events=1),
    lambda b: b["report"].update(total_turnready_calls=3),
    lambda b: b["trace"]["events"][0].update(id=2),
    lambda b: b["trace"]["events"][2].update(started_ms=0),
    lambda b: b["trace"]["events"][1].update(settled_ms=None),
    lambda b: b["trace"]["events"][1].update(http_status=True),
    lambda b: b["trace"]["events"][1].update(outcome="UNRECOGNIZED"),
    lambda b: b["trace"]["events"][1].update(app_success="true"),
    lambda b: b["trace"]["events"][1].update(started_ms=float("nan")),
    lambda b: b["trace"]["events"][1].update(route="private-game"),
    lambda b: b["trace"]["events"].append("malformed"),
    lambda b: b["trace"]["events"].pop(0),
    lambda b: b.update(schema="planets-lab.fake-upgrade.v7"),
])
def test_malformed_or_forged_trace_and_report_fail_closed(synthetic_bundle, change):
    invalid = deepcopy(synthetic_bundle)
    change(invalid)
    with pytest.raises(ClientSequenceInvalid) as error:
        safe_metadata_summary(invalid)
    assert str(error.value) == "ABSTAIN_INVALID_OR_UNTRUSTED_CLIENT_METADATA"


def test_client_success_never_promotes_trust_or_execution(synthetic_bundle):
    sample = deepcopy(synthetic_bundle)
    sample["report"]["client_visible_save_success_events"] = 1
    sample["report"]["client_visible_ready_success_events"] = 2
    # The client success fields alone cannot set any external provenance.
    outcome = safe_metadata_summary(sample)
    assert not outcome["nuhost_execution_verified"]
    assert not outcome["independent_server_order_acceptance_verified"]
    assert not outcome["independently_witnessed_host_start"]


def test_cli_synthetic_emits_only_safe_aggregate():
    if shutil.which("node") is None:
        pytest.skip("Node.js unavailable")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "diagnostics" /
                             "m2_client_sequence_audit_v1.py"), "--synthetic"],
        capture_output=True, text=True, timeout=25, cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "SELF_CONSISTENT_CLIENT_METADATA_NOT_NUHOST_VERIFIED" in proc.stdout
    for secret in ("FAKE_BEARER", "FICTIONAL_GAME", "started_ms", "gameid"):
        assert secret not in proc.stdout
    assert "nuhost_execution_verified: false" in proc.stdout


def test_cli_rejects_private_bundle_from_repo_or_world_readable(tmp_path, synthetic_bundle):
    script = str(ROOT / "tools" / "diagnostics" / "m2_client_sequence_audit_v1.py")
    file = tmp_path / "client_metadata.json"
    file.write_text(json.dumps(synthetic_bundle))
    file.chmod(0o644)
    proc = subprocess.run(
        [sys.executable, script, "--private-bundle", str(file)],
        capture_output=True, text=True, timeout=25,
    )
    assert proc.returncode == 2
    assert str(file) not in proc.stdout
    file.chmod(0o600)
    proc = subprocess.run(
        [sys.executable, script, "--private-bundle", str(file)],
        capture_output=True, text=True, timeout=25,
    )
    assert proc.returncode == 0, proc.stderr
    assert str(file) not in proc.stdout
    link = tmp_path / "link.json"
    link.symlink_to(file)
    proc = subprocess.run(
        [sys.executable, script, "--private-bundle", str(link)],
        capture_output=True, text=True, timeout=25,
    )
    assert proc.returncode == 2
    assert str(link) not in proc.stdout
