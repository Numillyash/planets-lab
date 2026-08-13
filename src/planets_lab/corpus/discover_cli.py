from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import CorpusApiError, PlanetsNuPublicApi
from .discovery import finished_games
from .manifest import build_game_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("validation/corpus/manifests/finished-games.jsonl"))
    args = parser.parse_args()

    try:
        client = PlanetsNuPublicApi()
        games = finished_games(client, args.names)
        if args.limit:
            games = games[:args.limit]
        records = [build_game_manifest(game, client.load_info(int(game["id"]))) for game in games]
    except (CorpusApiError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"finished_games={len(games)}")
    print(f"manifests={len(records)}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
