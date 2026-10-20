"""Local-only independent audit of an atomic M2 client metadata bundle.

Private timeline JSON is restricted to a user-owned, chmod600, regular
non-symlink file OUTSIDE the source checkout. No private data, field paths,
timestamps or file names appear in stdout/stderr. Synthetic mode runs the
fully fake Node browser and validates its output in memory, without
persisting its event trace. Never call with private input via runtime-logs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from planets_lab.sim.planetary_client_sequence_audit import (
    ClientSequenceInvalid, safe_metadata_summary,
)
from m2_local_save_readiness_v1 import read_private

MAX_SYNTHETIC_STDOUT = 1024 * 1024


def fake_browser_bundle() -> dict:
    node = shutil.which("node")
    if node is None:
        raise ClientSequenceInvalid("ABSTAIN_NODE_RUNTIME_UNAVAILABLE")
    result = subprocess.run(
        [node, str(ROOT / "tests" / "js" /
                   "test_planets_nu_save_ready_metadata_v1.cjs"),
         "--emit-synthetic-bundle"],
        capture_output=True, timeout=20, cwd=ROOT,
        check=False,
    )
    if (result.returncode != 0
            or len(result.stdout) > MAX_SYNTHETIC_STDOUT):
        raise ClientSequenceInvalid("ABSTAIN_SYNTHETIC_BROWSER_GATE_FAILURE")
    # No child diagnostics are emitted, even if the process failed.
    candidate = json.loads(result.stdout)
    if type(candidate) is not dict:
        raise ClientSequenceInvalid("ABSTAIN_SYNTHETIC_BROWSER_GATE_FAILURE")
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strict local metadata chronology audit, NOT NuHost execution proof"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true",
                      help="run fake browser, never access private captures")
    mode.add_argument("--private-bundle", type=Path,
                      help="absolute local owned chmod600 JSON outside Git checkout")
    args = parser.parse_args(argv)
    print("===== M2 CLIENT SEQUENCE METADATA RECONCILIATION =====")
    try:
        bundle = fake_browser_bundle() if args.synthetic else read_private(args.private_bundle)
        summary = safe_metadata_summary(bundle)
    except (ClientSequenceInvalid, ValueError, TypeError,
            OSError, subprocess.TimeoutExpired, UnicodeError, MemoryError,
            RecursionError):
        print("status: ABSTAIN_INVALID_OR_UNTRUSTED_CLIENT_METADATA")
        print("raw_client_metadata_returned: false")
        return 2
    print("mode: SYNTHETIC_NO_PRIVATE_DATA" if args.synthetic else
          "mode: LOCAL_PRIVATE_METADATA_ONLY")
    print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    print("independent_host_start_witness: false")
    print("independent_server_order_acceptance: false")
    print("nuhost_execution_verified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
