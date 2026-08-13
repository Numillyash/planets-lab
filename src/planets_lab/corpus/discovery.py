from __future__ import annotations

from typing import Any

from .api import PlanetsNuPublicApi


def finished_games(
    client: PlanetsNuPublicApi,
    account_names: list[str],
) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}
    for account_name in account_names:
        for game in client.games_for_username(account_name.strip()):
            game_id = game.get("id")
            if game.get("status") != 3:
                continue
            if isinstance(game_id, bool) or not isinstance(game_id, int):
                continue
            by_id[game_id] = game
    return [by_id[game_id] for game_id in sorted(by_id, reverse=True)]
