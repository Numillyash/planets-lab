"""Bounded automatic selection of real consecutive embedded-turn windows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from planets_lab.corpus.pq_bounded_window_selection import select_bounded_pq_windows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan bounded approved archive windows, never claim Host parity",
    )
    parser.add_argument("--feature-index", type=Path, required=True)
    parser.add_argument("--frozen-cohort", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--game-id", type=int, required=True)
    parser.add_argument("--player-slot", type=int, required=True)
    parser.add_argument("--first-archive-turn", type=int, default=1)
    parser.add_argument("--max-pairs", type=int, default=48)
    parser.add_argument("--max-accepted", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = select_bounded_pq_windows(
            feature_index=args.feature_index,
            frozen_cohort=args.frozen_cohort,
            archive_dir=args.archive_dir,
            game_id=args.game_id, player_slot=args.player_slot,
            first_archive_turn=args.first_archive_turn,
            max_pairs=args.max_pairs, max_accepted=args.max_accepted,
        )
        output: Path = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        # Do not expose raw archive-derived values/strings in evidence logs.
        print(f"ABSTAIN_PQ_WINDOW_SELECTION: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "ADMISSIBLE_WINDOWS_FOUND" if report["admissible_consecutive_embedded_pairs"]
                  else "NO_CONSECUTIVE_EMBEDDED_PAIR_IN_BOUNDED_SCOPE",
        "checked": report["actually_checked_pairs"],
        "admitted": report["admissible_consecutive_embedded_pairs"],
        "refusal_counts": report["refusal_counts"],
        "causal_verified": False,
        "output": str(output),
    }, sort_keys=True))
    return 0 if report["admissible_consecutive_embedded_pairs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
