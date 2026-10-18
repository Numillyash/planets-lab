#!/usr/bin/env python3
"""Summarize already-created M2 surface context AGGREGATE, no DB read.

Uses exact pinned full baseline68 sample and reproduces public 915
surface residual denominator. --output creates a NEW aggregate-only JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.m2_surface_context_triage import (  # noqa: E402
    analyze_surface_context_aggregate,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.output and args.input.resolve() == args.output.resolve():
        p.error("output cannot overwrite source")
    result = analyze_surface_context_aggregate(
        json.loads(args.input.read_text(encoding="utf-8"))
    )
    print("status:", result["status"])
    print("frozen_selection_sha256:", result["source"]["frozen_selection_sha256"])
    for outcome, entry in result["by_outcome"].items():
        print("outcome_" + outcome + ":", json.dumps(entry, sort_keys=True))
    print(
        "surface_only_residual_magnitude_buckets:",
        json.dumps(result["surface_only_residual_magnitude_buckets"], sort_keys=True)
    )
    print("NuHost_order_execution_verified: false")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(result, target, indent=2, sort_keys=True)
            target.write("\n")
        print("aggregate_summary_written: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
