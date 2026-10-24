"""Only artificial JUnit XML: verify no names, paths, private failure details leak."""
from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.public100_pytest_safe_counts_v2 import (
    SCHEMA, classify_junit,
)


def test_successful_junit_only_reports_counts():
    raw = (b'<testsuites><testsuite name="SECRET_PRIVATE_NAME" tests="10" '
           b'failures="0" errors="0" skipped="2">'
           b'<testcase name="private-planet-id-99999"/></testsuite></testsuites>')
    result = classify_junit(raw, exit_code=0)
    assert result == {
        "schema": SCHEMA, "status": "PASS", "exit_code": 0,
        "tests": 10, "failures": 0, "errors": 0, "skipped": 2,
        "test_names_or_failure_traces_exported": False,
    }
    assert "SECRET" not in json.dumps(result)
    assert "99999" not in json.dumps(result)


def test_failure_counts_but_never_publish_traceback():
    raw = (b'<testsuite name="privategame" tests="4" failures="1" '
           b'errors="0" skipped="0"><testcase name="user-message">'
           b'<failure message="sensitive-order-here">secret stack trace</failure>'
           b'</testcase></testsuite>')
    r = classify_junit(raw, exit_code=1)
    assert r["status"] == "FAILED_TESTS"
    assert (r["tests"], r["failures"], r["errors"]) == (4, 1, 0)
    for forbidden in ("privategame", "user-message", "sensitive-order", "secret stack"):
        assert forbidden not in json.dumps(r)


def test_collection_error_is_distinct_from_test_failure():
    raw = b'<testsuite tests="1" failures="0" errors="1" skipped="0"></testsuite>'
    assert classify_junit(raw, exit_code=1)["status"] == "COLLECTION_OR_EXECUTION_ERRORS"


def test_unexplained_nonzero_does_not_claim_success():
    raw = b'<testsuite tests="3" failures="0" errors="0" skipped="0"/>'
    assert classify_junit(raw, exit_code=1)["status"] == "PYTEST_NONZERO_NO_FAILURE_DETAILS"
    assert classify_junit(raw, exit_code=0)["status"] == "PASS"


def test_no_data_or_broken_xml_abstains():
    for xml in (None, b'', b'<testsuite', b'<garbage/>',
                b'<testsuite tests="-1" failures="0" errors="0" skipped="0"/>',
                b'<testsuite tests="1" failures="2" errors="0" skipped="0"/>'):
        r = classify_junit(xml, exit_code=1)
        assert r["status"] == "MISSING_OR_INVALID_JUNIT"
        assert r["tests"] == 0


def test_empty_suite_reports_no_tests():
    raw = b'<testsuite tests="0" failures="0" errors="0" skipped="0"/>'
    assert classify_junit(raw, exit_code=5)["status"] == "NO_TESTS"


def test_cross_suite_aggregation():
    raw = (b'<testsuites><testsuite tests="9" failures="1" errors="0" skipped="1"/>'
           b'<testsuite tests="4" failures="0" errors="0" skipped="0"/></testsuites>')
    r = classify_junit(raw, exit_code=1)
    assert r["status"] == "FAILED_TESTS"
    assert r["tests"] == 13
    assert r["skipped"] == 1


def test_runner_pins_100_metadata_and_68_sample_and_never_prints_raw_pytest():
    root = Path(__file__).resolve().parents[1]
    text = (root / "tools/run-public100-baseline68-deep-v2.sh").read_text()
    assert "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb" in text
    assert "public-short-expansion-with-public36.jsonl" in text
    assert "942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d" in text
    assert "--pairs-per-game 16" in text
    assert "--expected-baseline-games 68" in text
    assert "--max-games 68" in text
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in text
    assert "--junitxml=" in text
    assert "private-local" in text
    publisher = (root / "tools/run-public100-baseline68-deep-v2-with-evidence.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in publisher
    assert "private-local" not in publisher
    assert "m2-deep-coverage.json" in publisher
