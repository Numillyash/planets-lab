#!/usr/bin/env python3
"""Anonymized pytest failure modules: repository-tracked filenames ONLY.

Read a local JUnit XML with potentially private test parametrization, report
only failure/error counts attributed to exact tracked tests/test_*.py files.
No parameter values, test names, traceback, local paths or JUnit contents are
included in the report or stdout. Unmatched entries are UNMAPPED.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

SCHEMA = "planets-lab.pytest-allowlisted-failed-module-counts.v4"
MODULE_PATTERN = re.compile(r"tests/test_[A-Za-z0-9_]+\.py\Z")
MAX_XML_SIZE = 20_000_000


def _module(classname: object, allowlisted: set[str]) -> str | None:
    if type(classname) is not str:
        return None
    parts = classname.split(".")
    if len(parts) == 2 and parts[0] == "tests":
        candidate = "tests/" + parts[1] + ".py"
    elif len(parts) == 1:
        candidate = "tests/" + parts[0] + ".py"
    else:
        return None
    if candidate not in allowlisted or not MODULE_PATTERN.fullmatch(candidate):
        return None
    return candidate


def classify_module_failures(xml: bytes | None, allowlisted: set[str]) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": SCHEMA, "status": "ABSTAIN_INVALID_JUNIT",
        "allowlisted_failed_modules": [],
        "unmapped_failures_or_errors": 0,
        "raw_test_names_or_traces_exported": False,
    }
    if not xml or len(xml) > MAX_XML_SIZE:
        return result
    try:
        root = ET.fromstring(xml)
        if root.tag not in ("testsuites", "testsuite"):
            return result
        modules: dict[str, Counter[str]] = {}
        unmatched = 0
        for case in root.iter("testcase"):
            state = None
            if case.find("error") is not None:
                state = "errors"
            elif case.find("failure") is not None:
                state = "failures"
            if state is None:
                continue
            filename = _module(case.get("classname"), allowlisted)
            if filename is None:
                unmatched += 1
            else:
                modules.setdefault(filename, Counter())[state] += 1
        result["status"] = "PASS_SAFE_FAILURE_COUNTS_ONLY"
        result["allowlisted_failed_modules"] = [
            {"module": key, "failures": count["failures"], "errors": count["errors"]}
            for key, count in sorted(modules.items())
        ]
        result["unmapped_failures_or_errors"] = unmatched
    except ET.ParseError:
        return result
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml", required=True, type=Path)
    p.add_argument("--repository", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    files = subprocess.run(
        ["git", "-C", str(args.repository), "ls-files", "--", "tests/test_*.py"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    safe = {path for path in files if MODULE_PATTERN.fullmatch(path)}
    if not safe:
        print("failure_module_summary=ABSTAIN_NO_TRACKED_TESTS", flush=True)
        return 2
    xml = args.xml.read_bytes() if args.xml.is_file() else None
    result = classify_module_failures(xml, safe)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("failure_module_summary=" + str(result["status"]), flush=True)
    print("failure_module_count=" + str(len(result["allowlisted_failed_modules"])), flush=True)
    print("unmapped_failure_count=" + str(result["unmapped_failures_or_errors"]), flush=True)
    return 0 if result["status"] == "PASS_SAFE_FAILURE_COUNTS_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
