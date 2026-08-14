from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .api import CorpusApiError, PlanetsNuPublicApi
from .archive import archive_members


def _default_output(game_id: int) -> Path:
    return Path("validation/corpus/cache/loadall") / f"game-{game_id}.zip"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and validate the finished-game /game/loadall archive."
    )
    parser.add_argument("--game-id", type=int, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="download again even if the cache file already exists",
    )
    args = parser.parse_args()

    if args.game_id <= 0:
        print("game id must be positive", file=sys.stderr)
        return 2

    output = args.output or _default_output(args.game_id)

    try:
        if output.exists() and not args.refresh:
            data = output.read_bytes()
            source = "cache"
        else:
            client = PlanetsNuPublicApi()
            info = client.load_info(args.game_id)
            game = info.get("game", {})
            if game.get("status") != 3:
                raise ValueError("/game/loadall probe requires a finished game (status=3)")
            data = client.load_all_archive(args.game_id)
            source = "network"

        members = archive_members(data)
    except (CorpusApiError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if source == "network":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)

    digest = hashlib.sha256(data).hexdigest()
    summary = {
        "game_id": args.game_id,
        "source": source,
        "output": str(output),
        "bytes": len(data),
        "sha256": digest,
        "members": len(members),
    }
    print(json.dumps(summary, sort_keys=True))
    for member in members[:80]:
        print(member)
    if len(members) > 80:
        print(f"... {len(members) - 80} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
