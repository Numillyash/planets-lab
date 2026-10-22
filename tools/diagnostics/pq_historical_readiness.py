"""Read-only CLI: exact frozen cohort x existing feature index, no archive scans."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from planets_lab.corpus.pq_historical_readiness import report_from_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Frozen-cohort PQ/PPQ history readiness, not NuHost causal parity",
    )
    parser.add_argument("--feature-index", required=True, type=Path)
    parser.add_argument("--frozen-cohort", required=True, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = report_from_paths(args.feature_index, args.frozen_cohort)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ABSTAIN_PQ_CORPUS_READINESS: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    # Never write partial output on failed input/scope selection.
    target: Path = args.output
    encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(encoded, encoding="utf-8")
        temp.replace(target)
    except OSError as exc:
        print(f"ABSTAIN_PQ_CORPUS_READINESS: output: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "schema": result["schema"],
        "cohort_game_count": result["cohort_game_count"],
        "observational_candidates": len(result["observational_candidate_ids"]),
        "causal_verified": 0,
        "output": str(target),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
