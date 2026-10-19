"""Local-only /game/save capture triage; never print source request payloads.

Usage:
  python tools/diagnostics/m2_local_save_readiness_v1.py --synthetic
  python tools/diagnostics/m2_local_save_readiness_v1.py --private-input /outside/repo/capture.json

Raw private inputs MUST stay outside the repository and runtime-logs.
For Linux, keep files user-owned and chmod 600. The CLI prints only a
fixed allowlisted aggregate with NO source field names/values/URLs/IDs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from planets_lab.sim.planetary_save_evidence_readiness import (
    SaveEvidenceInvalid, public_aggregate,
)

MAX_PRIVATE_INPUT_BYTES = 32 * 1024 * 1024


def synthetic_report() -> dict:
    """A fake browser capture, not a user report or authenticated receipt."""
    return {
        "schema": "planets-lab.save-payload-capture.v1",
        "status": "CLIENT_PAYLOAD_CAPTURE_NOT_NUHOST_ORDER_ACK",
        "observed_save_calls_retained": 4,
        "observations": [
            {
                "transport": "xhr", "method": "POST",
                "request": {"encoding": "form", "body": {
                    "gameid": "SYNTHETIC_ONLY", "savekey": "<REDACTED_CREDENTIAL>",
                }},
                "http_status": 200,
                "response": {"encoding": "json", "body": {
                    "success": True, "other": "synthetic-ok",
                }},
            },
            {
                "transport": "fetch", "method": "POST",
                "request": {"encoding": "json", "body": {"turn": {"synthetic": True}}},
                "http_status": 200,
                "response": {"encoding": "json", "body": {"success": False}},
            },
            {
                "transport": "xhr", "method": "POST",
                "request": {"encoding": "unavailable", "body": "<REQUEST_BODY_UNAVAILABLE>"},
                "http_status": 429,
                "response": None,
            },
            {
                "transport": "xhr", "method": "POST",
                "request": {"encoding": "form", "body": {"some": "<OMITTED_NODE_LIMIT>"}},
                "http_status": 200,
                "response": {"encoding": "json", "body": {"result": "unknown"}},
            },
        ],
        "route_counters": {"save": 6, "turnready": 1},
        "redaction_scope": "KNOWN_CREDENTIAL_FIELD_NAMES_ONLY_REVIEW_BEFORE_SHARING",
        "no_extra_requests": True,
        "verified_NuHost_order_mapping": False,
    }


def read_private(path: Path) -> dict:
    """Open user-owned restricted local file without following symlinks."""
    # No file paths, IDs, exceptions or input values are ever echoed.
    try:
        file_path = path.resolve(strict=True)
        if file_path.is_relative_to(ROOT.resolve()):
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        if path.is_symlink():
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or info.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
                    or info.st_size <= 0
                    or info.st_size > MAX_PRIVATE_INPUT_BYTES):
                raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
            with os.fdopen(fd, "rb", closefd=False) as reader:
                data = reader.read(MAX_PRIVATE_INPUT_BYTES + 1)
            if len(data) > MAX_PRIVATE_INPUT_BYTES:
                raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        finally:
            os.close(fd)
        parsed = json.loads(data)
        if type(parsed) is not dict:
            raise SaveEvidenceInvalid("invalid_or_unsafe_capture")
        return parsed
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise SaveEvidenceInvalid("invalid_or_unsafe_capture") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate-only LOCAL capture triage; no Host execution proof"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--synthetic", action="store_true",
                       help="Use built-in fake report; safe for public runtime evidence")
    modes.add_argument("--private-input", type=Path,
                       help="Only local user-owned chmod600 JSON outside repository")
    args = parser.parse_args(argv)
    print("===== M2 LOCAL SAVE EVIDENCE READINESS =====")
    try:
        if args.synthetic:
            result = public_aggregate(synthetic_report())
        else:
            result = public_aggregate(read_private(args.private_input))
    except (SaveEvidenceInvalid, ValueError, TypeError, RecursionError, MemoryError):
        print("status: ABSTAIN_PRIVATE_CAPTURE_INVALID_OR_UNSAFE")
        print("private_capture_data_emitted: false")
        return 2
    print("mode: SYNTHETIC_NO_PRIVATE_DATA" if args.synthetic else "mode: LOCAL_PRIVATE_AGGREGATE_ONLY")
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    print("raw_payload_emitted: false")
    print("server_order_receipt_verified: false")
    print("nuhost_execution_verified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
