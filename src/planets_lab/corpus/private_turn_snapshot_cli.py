from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi
from planets_lab.data.nu_loadturn import NuLoadTurnError, import_loadturn


SENSITIVE_KEYS = frozenset({"apikey", "password", "savekey"})
DEFAULT_OUTPUT_DIR = Path("data/raw/private-turns")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if str(key).lower() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _load_api_key(path: Path | None) -> str:
    if path is not None:
        value = path.read_text(encoding="utf-8").strip()
    else:
        value = os.environ.get("PLANETSNU_API_KEY", "").strip()
    if not value:
        raise ValueError(
            "Planets.nu API key missing; set PLANETSNU_API_KEY or use --api-key-file"
        )
    return value


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, dict)]


def _resolved_identity(payload: dict[str, Any]) -> tuple[int, int, int]:
    rst = _require_dict(payload.get("rst"), "rst")
    game = _require_dict(rst.get("game"), "rst.game")
    player = _require_dict(rst.get("player"), "rst.player")
    game_id = game.get("id")
    turn = game.get("turn")
    player_id = player.get("id")
    for value, label in (
        (game_id, "rst.game.id"),
        (turn, "rst.game.turn"),
        (player_id, "rst.player.id"),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer")
    return int(game_id), int(turn), int(player_id)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def fetch(args: argparse.Namespace) -> int:
    api_key = _load_api_key(args.api_key_file)
    client = PlanetsNuPublicApi(
        proxy_url=args.proxy_url,
        allow_direct=args.direct,
        timeout=args.timeout,
    )
    try:
        payload = client.load_turn(
            args.game_id,
            api_key,
            turn=args.turn,
            for_save=True,
        )
    finally:
        del api_key

    sanitized = _sanitize(payload)
    if not isinstance(sanitized, dict):
        raise ValueError("sanitized loadturn payload is not an object")
    game_id, turn, player_id = _resolved_identity(sanitized)
    if game_id != args.game_id:
        raise ValueError(
            f"loadturn game mismatch: requested={args.game_id} actual={game_id}"
        )

    # Validate that the snapshot is usable by the canonical project importer.
    state = import_loadturn(sanitized, game_id=game_id, turn=turn)
    state.validate()

    encoded = _canonical_bytes(sanitized)
    digest = hashlib.sha256(encoded).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = (
        args.output_dir
        / f"game-{game_id}-turn-{turn}-player-{player_id}-{digest[:12]}.json"
    )
    output.write_bytes(encoded)
    output.chmod(0o600)

    rst = _require_dict(sanitized.get("rst"), "rst")
    counts = {
        name: len(_records(rst.get(name)))
        for name in ("planets", "ships", "starbases", "vcrs")
    }

    print("===== PRIVATE LOADTURN SNAPSHOT =====")
    print(f"game_id:            {game_id}")
    print(f"turn:               {turn}")
    print(f"source_player_slot: {player_id}")
    print(f"planets:            {counts['planets']}")
    print(f"ships:              {counts['ships']}")
    print(f"starbases:          {counts['starbases']}")
    print(f"vcrs:               {counts['vcrs']}")
    print(f"snapshot_sha256:    {digest}")
    print(f"canonical_import:   PASS")
    print(f"raw_private_path:   {output}")
    print("raw_private_publish: DISABLED")
    return 0


def _intish(row: dict[str, Any], key: str) -> int | None:
    value = row.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ship_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _intish(row, "id"),
        "ownerid": _intish(row, "ownerid"),
        "hullid": _intish(row, "hullid"),
        "x": _intish(row, "x"),
        "y": _intish(row, "y"),
        "warp": _intish(row, "warp"),
        "targetx": _intish(row, "targetx"),
        "targety": _intish(row, "targety"),
        "mission": _intish(row, "mission"),
        "enemy": _intish(row, "enemy"),
        "friendlycode": row.get("friendlycode"),
        "damage": _intish(row, "damage"),
        "crew": _intish(row, "crew"),
        "name": row.get("name"),
    }


def candidate_sites(args: argparse.Namespace) -> int:
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("snapshot must contain a JSON object")
    game_id, turn, player_id = _resolved_identity(payload)
    rst = _require_dict(payload.get("rst"), "rst")
    ships = [_ship_projection(row) for row in _records(rst.get("ships"))]

    sites: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for ship in ships:
        x = ship.get("x")
        y = ship.get("y")
        if isinstance(x, int) and isinstance(y, int):
            sites[(x, y)].append(ship)

    candidates: list[dict[str, Any]] = []
    for (x, y), site_ships in sorted(sites.items()):
        own = [row for row in site_ships if row.get("ownerid") == player_id]
        hostile = [
            row
            for row in site_ships
            if isinstance(row.get("ownerid"), int)
            and row.get("ownerid") not in {0, player_id}
        ]
        hostile_owners = {
            int(row["ownerid"])
            for row in hostile
            if isinstance(row.get("ownerid"), int)
        }
        if own and len(hostile) >= 2:
            candidates.append(
                {
                    "x": x,
                    "y": y,
                    "own": own,
                    "other": hostile,
                    "other_owner_ids": sorted(hostile_owners),
                }
            )

    print("===== PRIVATE CAPTURE CANDIDATE SITES =====")
    print(f"game_id:             {game_id}")
    print(f"turn:                {turn}")
    print(f"source_player_slot:  {player_id}")
    print(f"candidate_sites:     {len(candidates)}")
    if not candidates:
        print("status:              NO_CURRENT_MULTI_SHIP_SITE")
        return 0

    for index, site in enumerate(candidates, start=1):
        print()
        print(
            f"--- site {index}: ({site['x']}, {site['y']}) "
            f"other_owners={site['other_owner_ids']} ---"
        )
        for label, rows in (("OWN", site["own"]), ("OTHER", site["other"])):
            for row in sorted(rows, key=lambda item: int(item.get("id") or 0)):
                print(
                    f"{label} ship={row.get('id')} owner={row.get('ownerid')} "
                    f"hull={row.get('hullid')} warp={row.get('warp')} "
                    f"mission={row.get('mission')} enemy={row.get('enemy')} "
                    f"fc={row.get('friendlycode')!r} "
                    f"damage={row.get('damage')} crew={row.get('crew')} "
                    f"name={row.get('name')!r}"
                )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch or inspect a private Planets.nu loadturn snapshot without "
            "publishing private raw state."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--game-id", type=int, required=True)
    fetch_parser.add_argument("--turn", type=int)
    fetch_parser.add_argument("--api-key-file", type=Path)
    fetch_parser.add_argument("--proxy-url")
    fetch_parser.add_argument("--direct", action="store_true")
    fetch_parser.add_argument("--timeout", type=float, default=30.0)
    fetch_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    fetch_parser.set_defaults(func=fetch)

    inspect_parser = subparsers.add_parser("candidate-sites")
    inspect_parser.add_argument("--input", type=Path, required=True)
    inspect_parser.set_defaults(func=candidate_sites)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, CorpusApiError, NuLoadTurnError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
