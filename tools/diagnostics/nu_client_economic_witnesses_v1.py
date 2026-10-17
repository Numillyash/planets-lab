#!/usr/bin/env python3
"""Offline M2 client-economic witness extraction from locally redacted HAR.

Usage, from cloned repository:
  python tools/diagnostics/nu_client_economic_witnesses_v1.py \
    --input /private/save_bundle_clean.json \
    --also-input /private/save_bundle_clean2.json \
    --output /private/client_economic_witnesses.json

Only aggregate counts are printed. The optional output includes game
IDs and numeric game data, so review and keep it private. No network
calls, no raw HARs, no login and no changes to Planets.nu.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from planets_lab.data.nu_save_client_economic_witnesses import (
    analyze_client_economic_evidence,
)

BUNDLE_SCHEMA = "planets-lab.har-save-capture-bundle.v1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--also-input", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path,
                        help="Optional PRIVATE JSON with noncredential game data")
    args = parser.parse_args()

    inputs = [args.input, *args.also_input]
    if args.output and any(args.output.resolve() == p.resolve() for p in inputs):
        parser.error("output must not overwrite an input file")

    # Input order is NOT interpreted as event order. The witness model
    # uses per-request timestamps where same-turn groups overlap.
    sessions = []
    for p in inputs:
        bundle = json.loads(p.read_text(encoding="utf-8"))
        if bundle.get("schema") != BUNDLE_SCHEMA:
            parser.error("input must be a locally redacted save HAR bundle")
        sessions.extend(bundle["sessions"])

    report = analyze_client_economic_evidence({
        "schema": BUNDLE_SCHEMA, "sessions": sessions,
    })
    summary = report["summary"]
    print(f"status: {report['status']}")
    for field in (
        "input_saves", "unique_game_player_turn_windows",
        "overlap_windows", "saves_with_witnessed_order",
        "windows_abstained",
    ):
        print(f"{field}: {summary[field]}")
    for event, count in summary["event_counts"].items():
        print(f"{event}: {count}")
    print("NuHost_order_execution_verified: False")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print("Private numeric evidence written. Do not commit or publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
