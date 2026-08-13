from __future__ import annotations

import hashlib
import json
from typing import Any

MANIFEST_SCHEMA = "planets-lab.corpus-game.v1"

PLAYER_SLOT_FIELDS = (
    "id",
    "raceid",
    "status",
    "statusturn",
    "turnjoined",
    "finishrank",
    "activehulls",
    "activeadvantages",
)


def settings_hash(settings: dict[str, Any]) -> str:
    raw = json.dumps(
        settings,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _player_slots(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: player[key] for key in PLAYER_SLOT_FIELDS if key in player}
        for player in players
    ]


def build_game_manifest(
    game: dict[str, Any],
    loadinfo: dict[str, Any],
    *,
    tier: str = "B",
    matched_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    del matched_names
    info_game = loadinfo.get("game")
    settings = loadinfo.get("settings")
    players = loadinfo.get("players")
    if not isinstance(info_game, dict):
        raise ValueError("loadinfo.game must be an object")
    if not isinstance(settings, dict):
        raise ValueError("loadinfo.settings must be an object")
    if not isinstance(players, list) or not all(isinstance(player, dict) for player in players):
        raise ValueError("loadinfo.players must be a list of objects")
    if tier not in {"A", "B", "C"}:
        raise ValueError("tier must be A, B or C")
    game_id = info_game.get("id", game.get("id"))
    if isinstance(game_id, bool) or not isinstance(game_id, int):
        raise ValueError("game id must be an integer")
    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": tier,
        "settings_hash": settings_hash(settings),
        "game": info_game,
        "settings": settings,
        "player_slots": _player_slots(players),
    }
