#!/usr/bin/env python3
"""Extract count-only, public-safe pytest status from a LOCAL JUnit XML.

Never copies test case names, failures, paths, stdout, messages or tracebacks
from the LOCAL XML into runtime-logs. Only numeric counts + fixed status codes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

SCHEMA = "planets-lab.public100-deep-pytest-counts.v1"
STATUS = ("PASS", "FAILED_TESTS", "COLLECTION_OR_EXECUTION_ERRORS",
          "NO_TESTS", "MISSING_OR_INVALID_JUNIT", "PYTEST_NONZERO_NO_FAILURE_DETAILS")


def classify_junit(xml: bytes | None, *, exit_code: int) -> dict[str, object]:
    if type(exit_code) is not int or not 0 <= exit_code <= 255:
        raise ValueError("invalid pytest exit code")
    result: dict[str, object] = {
        "schema": SCHEMA,
        "status": "MISSING_OR_INVALID_JUNIT",
        "exit_code": exit_code,
        "tests": 0, "failures": 0, "errors": 0, "skipped": 0,
        "test_names_or_failure_traces_exported": False,
    }
    if not xml:
        return result
    try:
        root = ET.fromstring(xml)
        if root.tag == "testsuite":
            suites = [root]
        elif root.tag == "testsuites":
            suites = list(root.findall("testsuite"))
        else:
            return result
        if not suites:
            return result
        counts = {k: 0 for k in ("tests", "failures", "errors", "skipped")}
        for s in suites:
            for k in counts:
                raw = s.get(k)
                if raw is None or not raw.isascii() or not raw.isdecimal():
                    return result
                value = int(raw)
                if value < 0 or value > 10_000_000:
                    return result
                counts[k] += value
        if (counts["tests"] < counts["failures"] + counts["errors"] + counts["skipped"]
                or counts["tests"] > 10_000_000):
            return result
        result.update(counts)
    except (ValueError, ET.ParseError):
        return result

    if counts["errors"]:
        result["status"] = "COLLECTION_OR_EXECUTION_ERRORS"
    elif counts["failures"]:
        result["status"] = "FAILED_TESTS"
    elif counts["tests"] == 0:
        result["status"] = "NO_TESTS"
    elif exit_code != 0:
        result["status"] = "PYTEST_NONZERO_NO_FAILURE_DETAILS"
    else:
        result["status"] = "PASS"
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml", required=True, type=Path)
    p.add_argument("--exit-code", required=True, type=int)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    # Read only local diagnostic, not published (other than safe counts).
    xml = args.xml.read_bytes() if args.xml.is_file() else None
    safe = classify_junit(xml, exit_code=args.exit_code)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(safe, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("pytest_status=" + str(safe["status"]))
    print("pytest_cases=" + str(safe["tests"]))
    print("pytest_failures=" + str(safe["failures"]))
    print("pytest_errors=" + str(safe["errors"]))
    print("pytest_skipped=" + str(safe["skipped"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
