#!/usr/bin/env python3
"""Local, offline-only /game/save legacy field-diff analysis.

Usage:
  PYTHONPATH=src python tools/diagnostics/nu_save_payload_diff_v1.py \
      --input /path/to/local-redacted-capture.json \
      --output /path/to/private-analysis.json

Never commit or publish the input or the generated private analysis:
both can contain real owned-game state and previously hidden commands.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from planets_lab.data.nu_save_payload import analyze_save_capture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        help="Optional PRIVATE file with full changed values")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyze_save_capture(payload)
    summary = report["summary"]
    print(f"status: {report['status']}")
    print(f"retained_saves: {summary['retained_saves']}")
    print(f"earlier_saves_not_retained: {summary['earlier_saves_not_retained']}")
    print(f"unique_entities_observed: {summary['unique_entities_observed']}")
    print(f"field_changes_between_reobserved_entities: "
          f"{summary['field_changes_between_reobserved_entities']}")
    print(f"http_200_explicit_success_true: "
          f"{summary['http_200_explicit_success_true']}")
    print(f"http_200_explicit_success_false: "
          f"{summary['http_200_explicit_success_false']}")
    print(f"http_200_success_unknown_or_null: "
          f"{summary['http_200_success_unknown_or_null']}")
    print("NuHost_order_mapping_verified: False")
    if args.output:
        if args.output.resolve() == args.input.resolve():
            parser.error("output must not overwrite the input capture")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("private_analysis: written (contains real game values; never publish)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
