#!/usr/bin/env python3
"""Offline frozen VCR temporal replay from already-public sanitized counts."""
from __future__ import annotations

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/planets_lab/corpus/vcr_temporal_v1_observation_readout.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5", type=Path, required=True)
    parser.add_argument("--v6", type=Path, required=True)
    parser.add_argument("--vcr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() in (
        args.v5.resolve(), args.v6.resolve(), args.vcr.resolve()
    ):
        print("ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE")
        return 2
    try:
        spec = spec_from_file_location("_pure_vcr_temporal_readout_cli", MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("ABSTAIN_VCR_READOUT_MODULE_UNAVAILABLE")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.readout_vcr_temporal(
            json.loads(args.v5.read_text(encoding="utf-8")),
            json.loads(args.v6.read_text(encoding="utf-8")),
            json.loads(args.vcr.read_text(encoding="utf-8")),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RuntimeError):
        # Never echo untrusted file content, names or exception strings.
        print("ABSTAIN_VCR_TEMPORAL_READOUT")
        return 2
    values = result["vcr_observer_archive_rows_not_unique_battles"]
    print("PASS_VCR_FROZEN_TEMPORAL_INPUT_SOURCE_NOT_HOST_CAUSAL")
    print("exact_turn_and_both_participants=" +
          str(values["exact_turn_and_both_participants"]))
    print("exact_turn_and_full_typed_owners=" +
          str(values["exact_turn_and_participants_and_owners"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
