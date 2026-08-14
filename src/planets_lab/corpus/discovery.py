from __future__ import annotations

from typing import Any

from .api import PlanetsNuPublicApi


def _finished_game_from_history_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    game = entry.get("game")
    if not isinstance(game, dict):
        return None
    game_id = game.get("id", entry.get("gameid"))
    if game.get("status") != 3:
        return None
    if isinstance(game_id, bool) or not isinstance(game_id, int):
        return None
    normalized = dict(game)
    normalized["id"] = game_id
    return normalized


def finished_games(
    client: PlanetsNuPublicApi,
    account_ids: list[int],
) -> list[dict[str, Any]]:
    """Discover unique finished games across one or more account histories."""
    by_id: dict[int, dict[str, Any]] = {}
    for account_id in account_ids:
        for entry in client.account_history(account_id):
            game = _finished_game_from_history_entry(entry)
            if game is None:
                continue
            by_id[int(game["id"])] = game

    def sort_key(game: dict[str, Any]) -> tuple[str, int]:
        ended = game.get("dateended")
        return (ended if isinstance(ended, str) else "", int(game["id"]))

    return sorted(by_id.values(), key=sort_key, reverse=True)
