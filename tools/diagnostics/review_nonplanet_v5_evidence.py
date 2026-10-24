#!/usr/bin/env python3
"""Recompute a privacy-safe v5 evidence scorecard from aggregate-only JSON.

Does not access or query DuckDB, member archives, APIs or game entities.
Only writes a new report if *all* source provenance and counters validate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.nonplanet_v5_evidence_review import (  # noqa: E402
    EvidenceReviewAbstain, review_published_v5,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        print("status=ABSTAIN_OUTPUT_EXISTS_OR_COLLIDES")
        return 2
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = review_published_v5(data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, EvidenceReviewAbstain):
        # Untrusted raw input may contain identities/paths, never print it.
        print("status=ABSTAIN_INVALID_SOURCE_AGGREGATE")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print("status=PASS_SOURCE_READINESS_CLASSIFICATION_NOT_HOST_CAUSAL")
    print("baseline_games=68")
    print("frozen_archival_pairs=8550")
    print("real_host_phase_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
