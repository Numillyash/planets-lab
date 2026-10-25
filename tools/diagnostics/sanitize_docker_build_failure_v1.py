#!/usr/bin/env python3
"""Sanitize local Docker build failure evidence without exporting build text.

Only an allowlisted *candidate* category is emitted. Never emit log lines,
paths, hosts, package names, environment, secrets or original exceptions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SCHEMA = "planets-lab.docker-build-failure-safe-diagnostic.v1"
MAX_SCAN_BYTES = 262144
# Order matters: specific transport/storage errors win over generic build step.
PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("HOST_STORAGE_EXHAUSTED", ("no space left on device", "disk quota exceeded", "enospc")),
    ("HOST_MEMORY_OR_PROCESS_KILLED", ("out of memory", "oomkilled", "exit code: 137")),
    ("DOCKER_DAEMON_UNAVAILABLE", ("cannot connect to the docker daemon", "is the docker daemon running",
                                   "error during connect", "permission denied while trying to connect to the docker daemon")),
    ("REGISTRY_RATE_OR_AUTH", ("toomanyrequests", "pull rate limit", "unauthorized: authentication required",
                               "denied: requested access to the resource is denied")),
    ("DNS_RESOLUTION", ("temporary failure resolving", "temporary failure in name resolution",
                        "name resolution failed", "no such host", "could not resolve host")),
    ("TLS_CERTIFICATE", ("certificate verify failed", "x509: certificate",
                         "certificate signed by unknown authority")),
    ("DEPENDENCY_RESOLUTION", ("resolutionimpossible", "no matching distribution found",
                               "could not find a version that satisfies the requirement",
                               "unable to locate package")),
    ("REPOSITORY_OR_ARTIFACT_NOT_FOUND", ("failed to fetch", "404 not found",
                                         "repository does not have a release file")),
    ("DOCKERFILE_OR_BUILD_CONTEXT", ("failed to calculate checksum of ref",
                                     "dockerfile parse error", "failed to read dockerfile")),
    ("TRANSPORT_FAILURE", ("connection reset by peer", "network is unreachable",
                           "network is down", "i/o timeout", "connection timed out")),
)
ALLOWED = {name for name, _ in PATTERNS} | {"UNCLASSIFIED"}


def classify_build_log(text: str) -> str:
    # Conservative heuristic over bounded tail: NOT verified root cause.
    tail = text[-MAX_SCAN_BYTES:].casefold()
    for name, patterns in PATTERNS:
        if any(p in tail for p in patterns):
            return name
    return "UNCLASSIFIED"


def build_safe_diagnostic(log_path: Path, exit_code: int | None = None) -> dict:
    if exit_code is not None and (type(exit_code) is not int or not 1 <= exit_code <= 255):
        raise ValueError("ABSTAIN_BUILD_EXIT_CODE_NOT_FAILED")
    try:
        with log_path.open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - MAX_SCAN_BYTES))
            tail = stream.read(MAX_SCAN_BYTES).decode("utf-8", errors="replace")
        category = classify_build_log(tail)
        log_available = True
    except OSError:
        category = "UNCLASSIFIED"
        log_available = False
    if category not in ALLOWED:
        raise ValueError("ABSTAIN_CLASSIFIER_SCHEMA")
    return {
        "schema": SCHEMA,
        "build_status": "FAILED",
        "build_exit_code": exit_code,
        "build_exit_code_verified": exit_code is not None,
        "diagnostic_category": category,
        "local_log_available": log_available,
        "diagnostic_is_definitive_root_cause": False,
        "corpus_entity_accessed": False,
        "host_order_or_phase_verified": False,
        "raw_build_log_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, help="Only the actual Docker build process exit code, not the outer wrapper exit")
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.input.resolve():
        print("ABSTAIN_BUILD_SAFE_OUTPUT_EXISTS_OR_OVERWRITE")
        return 2
    try:
        result = build_safe_diagnostic(args.input, args.exit_code)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError):
        print("ABSTAIN_BUILD_SAFE_CLASSIFIER")
        return 2
    print("PASS_SANITIZED_BUILD_FAILURE_CATEGORY_ONLY")
    print("build_failure_category=" + result["diagnostic_category"])
    print("root_cause_confirmed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
