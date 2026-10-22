"""One pre-approved public PQ/PPQ T-1→T pair only; zero entity output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from planets_lab.corpus.pq_window_field_sufficiency import scan_single_pq_window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Two-member PQ/PPQ shape audit, NOT Host parity")
    parser.add_argument("--feature-index", required=True, type=Path)
    parser.add_argument("--frozen-cohort", required=True, type=Path)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--game-id", required=True, type=int)
    parser.add_argument("--player-slot", required=True, type=int)
    parser.add_argument("--turn-before", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = scan_single_pq_window(
            feature_index=args.feature_index,
            frozen_cohort=args.frozen_cohort,
            archive_dir=args.archive_dir,
            game_id=args.game_id, player_id=args.player_slot,
            t_before=args.turn_before,
        )
        target: Path = args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(target)
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(f"ABSTAIN_PQ_ARCHIVAL_WINDOW: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "game_id": report["game_id"], "before": report["before_archive_turn"],
        "after": report["after_archive_turn"],
        "shape_available": report["observational_shape_available"],
        "causal_verified": False, "output": str(target),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
