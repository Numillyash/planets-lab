"""Safe Docker build ABSTAIN attribution from private-local logs only.

No build, network, corpus read or private log publication in these tests.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.diagnostics.sanitize_docker_build_failure_v1 import (
    SCHEMA, build_safe_diagnostic, classify_build_log,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/diagnostics/sanitize_docker_build_failure_v1.py"


@pytest.mark.parametrize(("source","expected"),[
    ("error: failed to solve: no space left on device", "HOST_STORAGE_EXHAUSTED"),
    ("failed: OOMKilled", "HOST_MEMORY_OR_PROCESS_KILLED"),
    ("Cannot connect to the Docker daemon at unix:///path", "DOCKER_DAEMON_UNAVAILABLE"),
    ("error response from daemon: toomanyrequests", "REGISTRY_RATE_OR_AUTH"),
    ("Temporary failure resolving repo.example.invalid", "DNS_RESOLUTION"),
    ("x509: certificate signed by unknown authority", "TLS_CERTIFICATE"),
    ("ERROR: No matching distribution found for xyz-private", "DEPENDENCY_RESOLUTION"),
    ("E: Failed to fetch an apt repository", "REPOSITORY_OR_ARTIFACT_NOT_FOUND"),
    ("failed to read dockerfile: unknown", "DOCKERFILE_OR_BUILD_CONTEXT"),
    ("connection reset by peer", "TRANSPORT_FAILURE"),
    ("ERROR: builder failed at a proprietary step", "UNCLASSIFIED"),
])
def test_candidate_categories_are_fixed_enums_not_root_cause(source,expected):
    assert classify_build_log(source)==expected


def test_real_local_input_never_exported_and_attempt_attribution_remains_uncertain(tmp_path):
    private=tmp_path/"build.log"
    marker="SUPER_PRIVATE_TOKEN_875730"
    private.write_text("RUN --secret="+marker+"\nnetwork is unreachable\n"+marker)
    result=build_safe_diagnostic(private, 17)
    assert result=={
        "schema":SCHEMA, "build_status":"FAILED","build_exit_code":17,
        "build_exit_code_verified":True,
        "diagnostic_category":"TRANSPORT_FAILURE",
        "local_log_available":True,
        "diagnostic_is_definitive_root_cause":False,
        "corpus_entity_accessed":False,
        "host_order_or_phase_verified":False,
        "raw_build_log_exported":False,
    }
    assert marker not in json.dumps(result)


def test_historical_build_exit_not_invented_and_missing_log_still_safe(tmp_path):
    log=tmp_path/"unknown.log"
    d=build_safe_diagnostic(log)
    assert d["build_exit_code"] is None
    assert d["build_exit_code_verified"] is False
    assert d["local_log_available"] is False
    assert d["diagnostic_category"]=="UNCLASSIFIED"


@pytest.mark.parametrize("invalid",[0,-1,256,True,"125"])
def test_failed_build_exit_code_is_strict(invalid,tmp_path):
    with pytest.raises(ValueError):
        build_safe_diagnostic(tmp_path/"not-present.log",invalid)


def test_isolated_host_cli_preserves_privacy_and_never_overwrites(tmp_path):
    old=tmp_path/"private.log"
    old.write_text("PRIVATE_USERNAME_841\nNo space left on device\nSECRET_APIKEY_223")
    output=tmp_path/"diagnostic.json"
    cmd=[sys.executable,"-I","-S",str(CLI),"--input",str(old),
         "--output",str(output),"--exit-code","1"]
    first=subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=15)
    assert first.returncode==0,first.stdout+first.stderr
    report=json.loads(output.read_text())
    assert report["diagnostic_category"]=="HOST_STORAGE_EXHAUSTED"
    assert report["build_exit_code"]==1
    assert "root_cause_confirmed=false" in first.stdout
    assert "PRIVATE_USERNAME_841" not in first.stdout+first.stderr+json.dumps(report)
    assert "SECRET_APIKEY_223" not in first.stdout+first.stderr+json.dumps(report)
    again=subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=15)
    assert again.returncode==2
    assert again.stdout.strip()=="ABSTAIN_BUILD_SAFE_OUTPUT_EXISTS_OR_OVERWRITE"
    assert json.loads(output.read_text())==report


def test_historical_cli_omits_unobserved_build_exit_code(tmp_path):
    p=tmp_path/"past-build.log";p.write_text("some unknown dependency install error\n")
    out=tmp_path/"summary.json"
    r=subprocess.run([sys.executable,"-I","-S",str(CLI),"--input",str(p),
        "--output",str(out)],cwd=tmp_path,capture_output=True,text=True,timeout=15)
    assert r.returncode==0
    result=json.loads(out.read_text())
    assert result["build_exit_code"] is None
    assert result["diagnostic_category"]=="UNCLASSIFIED"


def test_runner_and_evidence_publisher_disclose_only_enum_json_not_private_log():
    runner=(ROOT/"tools/run-public100-baseline68-vcr-temporal-v1.sh").read_text()
    wrapper=(ROOT/"tools/run-public100-baseline68-vcr-temporal-v1-with-evidence.sh").read_text()
    historical=(ROOT/"tools/run-public100-baseline68-vcr-existing-build-log-v1.sh").read_text()
    historical_wrapper=(ROOT/"tools/run-public100-baseline68-vcr-existing-build-log-v1-with-evidence.sh").read_text()
    assert 'BUILD_DIAG="$OUT/build-failure-diagnostic.json"' in runner
    assert runner.index("sanitize_docker_build_failure_v1.py")<runner.index('abstain "ABSTAIN_BUILD_FAILED"')
    assert "--exit-code \"$build_rc\"" in runner
    assert "build-failure-diagnostic.json" in wrapper
    assert "private-local/build.log" not in wrapper
    assert "tools/run-with-runtime-evidence.sh" in wrapper
    assert "private-local/build.log" in historical
    assert "ABSTAIN_BUILD_FAILED" in historical
    assert "--exit-code" not in historical
    assert "tools/run-with-runtime-evidence.sh" in historical_wrapper
    assert "private-local" not in historical_wrapper
    for name in (
        "run-public100-baseline68-vcr-temporal-v1.sh",
        "run-public100-baseline68-vcr-temporal-v1-with-evidence.sh",
        "run-public100-baseline68-vcr-existing-build-log-v1.sh",
        "run-public100-baseline68-vcr-existing-build-log-v1-with-evidence.sh",
    ):
        cmd=subprocess.run(["bash","-n",str(ROOT/"tools"/name)],
                           capture_output=True,text=True,timeout=15)
        assert cmd.returncode==0, name+cmd.stderr
