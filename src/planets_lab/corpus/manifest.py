from __future__ import annotations

import hashlib
import json
from typing import Any

MANIFEST_SCHEMA = "planets-lab.corpus-game.v1"


def settings_hash(settings: dict[str, Any]) -> str:
    raw = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_game_manifest(
    game: dict[str, Any],
    loadinfo: dict[str, Any],
    *,
    tier: str = "B",
    matched_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    info_game = loadinfo.get("game")
    settings = loadinfo.get("settings")
    players = loadinfo.get("players")
    if not isinstance(info_game, dict):
        raise ValueError("loadinfo.game must be an object")
    if not isinstance(settings, dict):
        raise ValueError("loadinfo.settings must be an object")
    if not isinstance(players, list):
        raise ValueError("loadinfo.players must be a list")
    if tier not in {"A", "B", "C"}:
        raise ValueError("tier must be A, B or C")
    game_id = info_game.get("id", game.get("id"))
    if not isinstance(game_id, int) or isinstance(game_id, bool):
        raise ValueError("game id must be an integer")
    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": tier,
        "matched_names": sorted(set(matched_names)),
        "settings_hash": settings_hash(settings),
        "game": info_game,
        "settings": settings,
        "players": players,
        "list_record": game,
    }
