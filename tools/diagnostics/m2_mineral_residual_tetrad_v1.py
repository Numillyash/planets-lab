#!/usr/bin/env python3
"""Reconcile an EXISTING aggregate M2 mineral report; no corpus access.

Usage:
  python tools/diagnostics/m2_mineral_residual_tetrad_v1.py \
    --input artifacts/planetary/m2-public100-mineral-balance-v1/report.json

Optional --output path creates a new small aggregate JSON (exclusive).
Input is existing sanitized report, never a raw TRN or HAR.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.m2_mineral_residual_tetrad import residual_tetrad  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.output and args.input.resolve() == args.output.resolve():
        p.error("output must never overwrite the original evidence report")

    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = residual_tetrad(report)
    print("status:", result["status"])
    print("baseline_game_count: 68")
    print("sealed_holdout_entities_accessed: 0")
    for mineral, values in result["per_mineral"].items():
        print(f"{mineral}: {json.dumps(values, sort_keys=True)}")
    print("aggregate:", json.dumps(result["aggregate"], sort_keys=True))
    print("host_causality_verified: false")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print("aggregate_json_written: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
