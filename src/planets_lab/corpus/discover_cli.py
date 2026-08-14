from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import CorpusApiError, PlanetsNuPublicApi
from .discovery import finished_games
from .manifest import build_game_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover completed Planets.nu games from account histories."
    )
    parser.add_argument("account_ids", nargs="+", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/manifests/finished-games.jsonl"),
    )
    args = parser.parse_args()

    if any(account_id <= 0 for account_id in args.account_ids):
        print("account ids must be positive", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit <= 0:
        print("limit must be positive", file=sys.stderr)
        return 2

    try:
        client = PlanetsNuPublicApi()
        games = finished_games(client, args.account_ids)
        if args.limit is not None:
            games = games[: args.limit]
        records = [
            build_game_manifest(game, client.load_info(int(game["id"])))
            for game in games
        ]
    except (CorpusApiError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    print(f"accounts={len(set(args.account_ids))}")
    print(f"finished_games={len(games)}")
    print(f"manifests={len(records)}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
