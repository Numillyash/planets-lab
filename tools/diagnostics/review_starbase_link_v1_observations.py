#!/usr/bin/env python3
"""Replay already published v5/v6 and starbase count-only projections. No DB."""
from __future__ import annotations

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/planets_lab/corpus/starbase_link_v1_observation_readout.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5", required=True, type=Path)
    parser.add_argument("--v6", required=True, type=Path)
    parser.add_argument("--starbase", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() in (
        args.v5.resolve(), args.v6.resolve(), args.starbase.resolve()
    ):
        print("ABSTAIN_OUTPUT_EXISTS_OR_SOURCE_OVERWRITE")
        return 2
    try:
        spec = spec_from_file_location("_pure_starbase_source_readout_cli", MODULE)
        if spec is None or spec.loader is None:
            raise ValueError("ABSTAIN_SOURCE_MODULE_UNAVAILABLE")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.readout_starbase_link(
            json.loads(args.v5.read_text(encoding="utf-8")),
            json.loads(args.v6.read_text(encoding="utf-8")),
            json.loads(args.starbase.read_text(encoding="utf-8")),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(source, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, AttributeError):
        print("ABSTAIN_STARBASE_SOURCE_READOUT")
        return 2
    print("PASS_STARBASE_OBSERVER_ARCHIVE_PLANET_LINK_NOT_HOST_CAUSAL")
    print("fresh_planet_linked_base_archive_occurrences=" + str(
        source["starbase_observer_archive_occurrences_not_unique_events"]["base_info_current_both_archives"]))
    print("host_diff_verified=false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
