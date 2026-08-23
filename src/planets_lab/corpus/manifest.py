from __future__ import annotations

import hashlib
import json
from typing import Any

MANIFEST_SCHEMA = "planets-lab.corpus-game.v2"

# Manifest game metadata is allowlisted deliberately. The public loadinfo.game
# payload can contain fields such as `password`; copying the object wholesale
# would make future API additions silently persistent in Git-tracked manifests.
GAME_METADATA_FIELDS = (
    "id",
    "name",
    "status",
    "statusname",
    "turn",
    "datecreated",
    "dateended",
    "gametype",
    "iscustom",
    "isprivate",
    "ispublic",
    "scenario",
    "scenarioid",
    "scenarioname",
    "maptype",
    "maptypeid",
    "wincondition",
    "winconditionid",
)

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


def _game_metadata(game: dict[str, Any]) -> dict[str, Any]:
    return {key: game[key] for key in GAME_METADATA_FIELDS if key in game}


def _player_slots(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: player[key] for key in PLAYER_SLOT_FIELDS if key in player}
        for player in players
    ]


def sanitize_manifest_record(record: dict[str, Any]) -> dict[str, Any]:
    """Rewrite an existing v1/v2 manifest record into the current privacy-safe schema."""

    game_id = record.get("game_id")
    settings = record.get("settings")
    game = record.get("game")
    player_slots = record.get("player_slots")
    tier = record.get("tier")

    if isinstance(game_id, bool) or not isinstance(game_id, int):
        raise ValueError("manifest game_id must be an integer")
    if not isinstance(settings, dict):
        raise ValueError("manifest settings must be an object")
    if not isinstance(game, dict):
        raise ValueError("manifest game must be an object")
    if not isinstance(player_slots, list) or not all(
        isinstance(player, dict) for player in player_slots
    ):
        raise ValueError("manifest player_slots must be a list of objects")
    if tier not in {"A", "B", "C"}:
        raise ValueError("manifest tier must be A, B or C")

    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": tier,
        "settings_hash": settings_hash(settings),
        "game": _game_metadata(game),
        "settings": settings,
        "player_slots": _player_slots(player_slots),
    }


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
        "game": _game_metadata(info_game),
        "settings": settings,
        "player_slots": _player_slots(players),
    }
