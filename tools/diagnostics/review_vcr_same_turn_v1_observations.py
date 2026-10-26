#!/usr/bin/env python3
"""Read ONLY three previously published count-only fixtures, never DuckDB."""
from __future__ import annotations

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/planets_lab/corpus/vcr_same_turn_v1_observation_readout.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5", type=Path, required=True)
    parser.add_argument("--v6", type=Path, required=True)
    parser.add_argument("--same-turn", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() in (
        args.v5.resolve(), args.v6.resolve(), args.same_turn.resolve()
    ):
        print("ABSTAIN_OUTPUT_ALREADY_EXISTS_OR_SOURCE_OVERWRITE")
        return 2
    try:
        spec = spec_from_file_location("_safe_vcr_same_turn_readout_cli", MODULE)
        if spec is None or spec.loader is None:
            raise ValueError("ABSTAIN_MODULE_UNAVAILABLE")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.readout_vcr_same_turn(
            json.loads(args.v5.read_text(encoding="utf-8")),
            json.loads(args.v6.read_text(encoding="utf-8")),
            json.loads(args.same_turn.read_text(encoding="utf-8")),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as dst:
            json.dump(result, dst, sort_keys=True, indent=2)
            dst.write("\n")
    except (OSError, ValueError, TypeError, AttributeError, KeyError, RuntimeError):
        # No raw source strings, paths, hashes, or exception text exposed.
        print("ABSTAIN_VCR_SAME_TURN_READOUT")
        return 2
    counts = result["selected_same_turn_source_groups_not_host_battles"]
    print("PASS_VCR_SAME_TURN_SOURCE_CONSENSUS_NONCAUSAL")
    print("multi_observer_groups=" + str(counts["multi_observer_groups"]))
    print("strict_complete_equal=" + str(counts["strict_complete_equal"]))
    print("strict_inputs_incomplete=" + str(counts["strict_inputs_incomplete"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
