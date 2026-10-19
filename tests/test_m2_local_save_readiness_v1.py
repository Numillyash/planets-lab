"""Local-only game-save preflight: never promote HTTP success to Host evidence."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "diagnostics"))
from m2_local_save_readiness_v1 import read_private, synthetic_report
from planets_lab.sim.planetary_save_evidence_readiness import (
    SaveEvidenceInvalid, public_aggregate,
)


def test_mixed_http_application_and_omission_counts_are_disjoint():
    report = synthetic_report()
    actual = public_aggregate(report)
    assert actual["retained_save_events"] == 4
    assert actual["total_save_route_calls"] == 6
    assert actual["total_turnready_route_calls_unlinked"] == 1
    assert actual["save_calls_not_retained"] == 2
    assert actual["parseable_nontruncated_request_events"] == 2
    assert actual["unavailable_or_truncated_request_events"] == 2
    assert actual["explicit_http_and_app_success_events"] == 1
    assert actual["application_failure_events"] == 1
    assert actual["http_failure_events"] == 1
    assert actual["ambiguous_or_missing_response_events"] == 1
    assert actual["transport_error_events"] == 0
    assert actual["any_known_field_redaction_marker_events"] == 1
    assert not actual["independent_server_order_acceptance_verified"]
    assert not actual["independent_host_start_witness_verified"]
    assert not actual["nuhost_execution_verified"]
    assert not actual["private_payload_content_returned"]
    assert "SYNTHETIC_ONLY" not in json.dumps(actual)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(status="DIFF_VERIFIED"),
    lambda r: r.update(no_extra_requests=False),
    lambda r: r.update(verified_NuHost_order_mapping=True),
    lambda r: r.update(observed_save_calls_retained=11),
    lambda r: r["observations"].append(deepcopy(r["observations"][0])),
    lambda r: r["route_counters"].update(save=1),
    lambda r: r["observations"][0]["request"]["body"].update(
        savekey="DANGEROUS_RAW_SECRET"
    ),
    lambda r: r["observations"][0]["request"]["body"].update(
        nested={"access_token": "DANGEROUS_RAW_SECRET"}
    ),
    lambda r: r["observations"][0].update(http_status=True),
    lambda r: r["observations"][0].update(method="INJECTED"),
    lambda r: r["observations"][0]["response"].update(
        encoding="x", surprise="payload"
    ),
])
def test_rejects_malformed_misleading_or_unmasked_capture(mutation):
    report = synthetic_report()
    mutation(report)
    with pytest.raises(SaveEvidenceInvalid):
        public_aggregate(report)


def test_request_parseability_never_proves_order_completeness():
    report = synthetic_report()
    report["observations"] = report["observations"][:1]
    report["observed_save_calls_retained"] = 1
    report["route_counters"]["save"] = 1
    result = public_aggregate(report)
    assert result["parseable_nontruncated_request_events"] == 1
    assert result["explicit_http_and_app_success_events"] == 1
    assert result["verified_order_payload_mapping"] is False
    assert result["signed_all_owner_orders_verified"] is False
    assert result["independent_server_order_acceptance_verified"] is False
    assert result["nuhost_execution_verified"] is False


def test_transport_failure_does_not_masquerade_as_http_response():
    report = synthetic_report()
    row = report["observations"][0]
    row["transport_error"] = True
    row["http_status"] = None
    row["response"] = None
    aggregate = public_aggregate(report)
    assert aggregate["transport_error_events"] == 1
    assert aggregate["explicit_http_and_app_success_events"] == 0
    row["http_status"] = 200
    with pytest.raises(SaveEvidenceInvalid):
        public_aggregate(report)


def test_cli_local_private_capture_outputs_only_aggregate(tmp_path):
    report = synthetic_report()
    marker = "PRIVATE_STRATEGY_VERY_SECRET_DO_NOT_LEAK"
    report["observations"][0]["request"]["body"]["internal_note"] = marker
    file = tmp_path / "private_capture.json"
    file.write_text(json.dumps(report), encoding="utf-8")
    file.chmod(0o600)
    result = subprocess.run(
        [sys.executable,
         str(ROOT / "tools" / "diagnostics" / "m2_local_save_readiness_v1.py"),
         "--private-input", str(file)],
        capture_output=True, text=True, cwd=ROOT, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "LOCAL_PRIVATE_AGGREGATE_ONLY" in result.stdout
    for secret in (marker, str(file), "SYNTHETIC_ONLY", "savekey", "internal_note"):
        assert secret not in result.stdout
    assert "nuhost_execution_verified" in result.stdout


def test_cli_refuses_world_readable_or_symlinked_file_without_leaking(tmp_path):
    file = tmp_path / "private_capture.json"
    file.write_text(json.dumps(synthetic_report()), encoding="utf-8")
    script = str(ROOT / "tools" / "diagnostics" / "m2_local_save_readiness_v1.py")
    file.chmod(0o644)
    proc = subprocess.run(
        [sys.executable, script, "--private-input", str(file)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 2
    assert "ABSTAIN_PRIVATE_CAPTURE_INVALID_OR_UNSAFE" in proc.stdout
    assert str(file) not in proc.stdout
    file.chmod(0o600)
    link = tmp_path / "capture_symlink.json"
    link.symlink_to(file)
    proc = subprocess.run(
        [sys.executable, script, "--private-input", str(link)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 2
    assert str(link) not in proc.stdout


def test_cli_synthetic_only_safe_output():
    result = subprocess.run(
        [sys.executable,
         str(ROOT / "tools" / "diagnostics" / "m2_local_save_readiness_v1.py"),
         "--synthetic"],
        capture_output=True, text=True, cwd=ROOT, timeout=30,
    )
    assert result.returncode == 0
    assert "SYNTHETIC_NO_PRIVATE_DATA" in result.stdout
    assert "SYNTHETIC_ONLY" not in result.stdout
    assert "PRIVATE_STRATEGY" not in result.stdout
    assert "nuhost_execution_verified: false" in result.stdout
