#!/usr/bin/env python3
"""Replay two *already published* sanitized evidence reports. No DuckDB access.

Example:
 python3 -I -S tools/diagnostics/review_minefield_v6_observations.py \
    --v5 tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json \
    --v6 tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json \
    --output /tmp/v6-safe-source-readout.json
"""
from __future__ import annotations

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/planets_lab/corpus/minefield_v6_observation_readout.py"


def _readout():
    # Deliberately do not import planets_lab.corpus: its package __init__
    # depends on DuckDB, while this offline diagnostic uses only stdlib.
    spec = spec_from_file_location("_pure_mine_v6_readout_cli", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("ABSTAIN_PURE_MODULE_IMPORT")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5", type=Path, required=True)
    parser.add_argument("--v6", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.resolve() in (
        args.v5.resolve(), args.v6.resolve()
    ):
        print("ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE")
        return 2
    try:
        module = _readout()
        v5 = json.loads(args.v5.read_text(encoding="utf-8"))
        v6 = json.loads(args.v6.read_text(encoding="utf-8"))
        result = module.readout_v6_joint(v5, v6)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except (ValueError, OSError, TypeError, KeyError, RuntimeError):
        # Never print untrusted data or private file paths.
        print("ABSTAIN_V6_SOURCE_READOUT")
        return 2
    print("PASS_FROZEN_COHORT_JOINT_OBSERVATION_NOT_CAUSAL")
    print("runtime_source=" + result["provenance"]["source_commit"])
    print("joint_changed_archive_occurrences=" +
          str(result["minefield_observation_occurrences_not_unique_events"]["joint_units_changed"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
