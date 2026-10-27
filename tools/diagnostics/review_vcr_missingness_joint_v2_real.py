#!/usr/bin/env python3
"""Safe isolated offline VCR same-turn missingness report; no DuckDB access."""
from __future__ import annotations

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/planets_lab/corpus/vcr_missingness_joint_v2_real_readout.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5", type=Path, required=True)
    parser.add_argument("--v6", type=Path, required=True)
    parser.add_argument("--v1", type=Path, required=True)
    parser.add_argument("--joint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() in (
        args.v5.resolve(), args.v6.resolve(), args.v1.resolve(),
        args.joint.resolve(),
    ):
        print("ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE")
        return 2
    try:
        spec = spec_from_file_location("_independent_real_rng_joint_readout", MODULE)
        if spec is None or spec.loader is None:
            raise ValueError("ABSTAIN_PURE_READOUT_MODULE_MISSING")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.readout_real_vcr_missingness(
            json.loads(args.v5.read_text(encoding="utf-8")),
            json.loads(args.v6.read_text(encoding="utf-8")),
            json.loads(args.v1.read_text(encoding="utf-8")),
            json.loads(args.joint.read_text(encoding="utf-8")),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, TypeError, ValueError, RuntimeError, KeyError, AttributeError):
        print("ABSTAIN_REAL_VCR_MISSINGNESS_SOURCE")
        return 2
    counts = result["selected_archive_group_and_row_missingness_not_host_battles"]
    print("PASS_REAL_FROZEN_VCR_MISSINGNESS_JOINT_NONCAUSAL")
    print("multi_rng_only_groups=" + str(counts["multi_rng_only_groups"]))
    print("multi_rng_missing_archive_rows=" + str(counts["multi_rng_missing_archive_rows"]))
    print("single_rng_only_groups=" + str(counts["singleton_rng_only_groups"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
