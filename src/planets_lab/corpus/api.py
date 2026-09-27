from __future__ import annotations

import gzip
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import ProxyHandler, Request, build_opener


DEFAULT_API_BASE_URL = "http://api.planets.nu"


class CorpusApiError(RuntimeError):
    pass


class PlanetsNuPublicApi:
    """Small stdlib Planets.nu client for corpus acquisition.

    Server-side Planets.nu access in this project is intentionally proxy-only.
    There is no silent direct-network fallback: callers must configure
    PLANETSNU_PROXY_URL or pass an explicit proxy_url.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        proxy_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("PLANETSNU_API_BASE_URL")
            or DEFAULT_API_BASE_URL
        ).rstrip("/")
        self.proxy_url = proxy_url or os.environ.get("PLANETSNU_PROXY_URL")
        self.timeout = timeout

        if not self.proxy_url:
            raise CorpusApiError(
                "PLANETSNU_PROXY_URL is required for corpus network access"
            )

        proxy_scheme = urlparse(self.proxy_url).scheme.lower()
        if proxy_scheme not in {"http", "https"}:
            raise CorpusApiError(
                "PLANETSNU_PROXY_URL must be an http:// or https:// proxy URL "
                "for the stdlib corpus client"
            )

        self._opener = build_opener(
            ProxyHandler(
                {
                    "http": self.proxy_url,
                    "https": self.proxy_url,
                }
            )
        )

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    def get_bytes(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        request = Request(
            self._url(path, params),
            headers={
                "Accept-Encoding": "gzip",
                "User-Agent": "planets-lab-corpus/0.1",
            },
            method="GET",
        )

        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                data = response.read()
                content_encoding = response.headers.get("Content-Encoding", "")
        except HTTPError as exc:
            raise CorpusApiError(
                f"Planets.nu returned HTTP {exc.code} for {path}"
            ) from exc
        except URLError as exc:
            raise CorpusApiError(
                f"Planets.nu request failed for {path}: {exc.reason}"
            ) from exc

        if content_encoding.lower() == "gzip" or data[:2] == b"\x1f\x8b":
            try:
                data = gzip.decompress(data)
            except OSError as exc:
                raise CorpusApiError(
                    f"Planets.nu returned invalid gzip data for {path}"
                ) from exc

        return data

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        data = self.get_bytes(path, params=params)
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CorpusApiError(
                f"Planets.nu returned invalid JSON for {path}"
            ) from exc

        if isinstance(payload, dict) and payload.get("success") is False:
            raise CorpusApiError(
                str(payload.get("error", f"Planets.nu {path} failed"))
            )
        return payload

    def games_list(
        self,
        *,
        statuses: tuple[int, ...] = (3,),
        game_types: tuple[int, ...] = (2, 3, 4, 6),
        scopes: tuple[int, ...] = (0,),
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Return public games matching the documented /games/list filters."""
        if not statuses or any(value < 0 for value in statuses):
            raise ValueError("statuses must contain non-negative integers")
        if not game_types or any(value <= 0 for value in game_types):
            raise ValueError("game_types must contain positive integers")
        if not scopes or any(value not in {0, 1} for value in scopes):
            raise ValueError("scopes must contain only 0/1")
        if limit < 0:
            raise ValueError("limit must be non-negative")

        payload = self.get_json(
            "games/list",
            params={
                "status": ",".join(str(value) for value in statuses),
                "type": ",".join(str(value) for value in game_types),
                "scope": ",".join(str(value) for value in scopes),
                "limit": limit,
            },
        )
        if not isinstance(payload, list) or not all(
            isinstance(record, dict) for record in payload
        ):
            raise CorpusApiError(
                "Planets.nu games/list response is not a list of objects"
            )
        return payload

    def games_for_username(self, username: str) -> list[dict[str, Any]]:
        """Return the active/current game list exposed by /games/list."""
        payload = self.get_json(
            "games/list",
            params={"username": username.strip()},
        )
        if not isinstance(payload, list) or not all(
            isinstance(record, dict) for record in payload
        ):
            raise CorpusApiError(
                "Planets.nu games/list response is not a list of objects"
            )
        return payload

    def account_history(self, account_id: int) -> list[dict[str, Any]]:
        """Return the account history entries used to discover completed games."""
        if account_id <= 0:
            raise ValueError("account id must be positive")
        payload = self.get_json(
            "account/history",
            params={"accountid": account_id},
        )
        if not isinstance(payload, dict):
            raise CorpusApiError(
                "Planets.nu account/history response is not an object"
            )
        history = payload.get("history")
        if not isinstance(history, list) or not all(
            isinstance(record, dict) for record in history
        ):
            raise CorpusApiError(
                "Planets.nu account/history response has no history object list"
            )
        return history

    def load_info(self, game_id: int) -> dict[str, Any]:
        payload = self.get_json(
            "game/loadinfo",
            params={"gameid": game_id},
        )
        if not isinstance(payload, dict):
            raise CorpusApiError(
                "Planets.nu loadinfo response is not an object"
            )
        if not isinstance(payload.get("game"), dict):
            raise CorpusApiError(
                "Planets.nu loadinfo response has no game object"
            )
        return payload

    def load_all_archive(self, game_id: int) -> bytes:
        """Download the documented all-turn archive for one finished game.

        The official API index documents /game/loadall as a ZIP containing all
        turns of all players in a finished game, but does not fully document the
        response schema. Callers validate ZIP structure before accepting the
        bytes as a corpus artifact.
        """

        return self.get_bytes(
            "game/loadall",
            params={"gameid": game_id},
        )
