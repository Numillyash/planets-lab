"""Read-only bounded multi-game public PPQ owner-current observational survey."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from planets_lab.corpus.pq_control_multigame_observation import survey_frozen_public_ppq


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Allowed public PPQ 6-game bounded identity survey; NOT Host parity",
    )
    parser.add_argument("--feature-index", type=Path, required=True)
    parser.add_argument("--frozen-cohort", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--perspective", type=int, default=1)
    parser.add_argument("--first-archive-turn", type=int, default=1)
    parser.add_argument("--max-pairs-per-game", type=int, default=48)
    parser.add_argument("--max-accepted-per-game", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = survey_frozen_public_ppq(
            feature_index=args.feature_index,
            frozen_cohort=args.frozen_cohort,
            archive_dir=args.archive_dir,
            player_slot=args.perspective,
            first_archive_turn=args.first_archive_turn,
            max_pairs_per_game=args.max_pairs_per_game,
            max_accepted_per_game=args.max_accepted_per_game,
        )
        output: Path = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(output.suffix + ".tmp")
        tmp.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(output)
    except (OSError, ValueError, TypeError) as exc:
        # Do NOT print messages potentially derived from an archive.
        print(f"ABSTAIN_PQ_FROZEN_MULTIGAME_SURVEY: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "OBSERVATIONAL_SOURCE_COVERAGE_ONLY",
        "scoped_games": report["scoped_games"],
        "qualified_games": report["games_with_qualified_observations"],
        "qualified_windows": report["owner_current_source_qualified_pairs"],
        "new_own_ship_identity_games": report["games_with_newly_visible_owned_fresh_ship_identity"],
        "host_verified": False,
        "output": str(output),
    }, sort_keys=True))
    return 0 if report["games_with_qualified_observations"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
