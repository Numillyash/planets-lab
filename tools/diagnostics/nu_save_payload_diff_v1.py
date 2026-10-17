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

from planets_lab.data.nu_save_payload import analyze_save_capture, analyze_har_save_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        help="Optional PRIVATE file with full changed values")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    is_bundle = payload.get("schema") == "planets-lab.har-save-capture-bundle.v1"
    report = analyze_har_save_bundle(payload) if is_bundle else analyze_save_capture(payload)
    summary = report["summary"]
    print(f"status: {report['status']}")
    if is_bundle:
        print(f"sessions: {summary['sessions']}")
        print(f"save_requests: {summary['save_requests']}")
        print(f"field_changes_between_reobserved_entities: {summary['changed_fields']}")
        print(f"record_observations_by_kind: {summary['record_observations_by_kind']}")
        print(f"changed_fields_by_kind: {summary['changed_fields_by_kind']}")
        print(f"nonzero_transfer_ship_snapshots: {summary['nonzero_transfer_ship_snapshots']}")
        print(f"distinct_nonzero_transfer_signatures: {summary['distinct_nonzero_transfer_signatures']}")
        print("starbase_build_starts_with_simultaneous_planet_costs: "
              f"{summary['starbase_build_starts_with_simultaneous_planet_costs']}")
        print("native_or_colonist_tax_rate_field_changes: "
              f"{summary['native_or_colonist_tax_rate_field_changes']}")
    else:
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
