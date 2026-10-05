from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs

from planets_lab.corpus.api import PlanetsNuPublicApi
from planets_lab.corpus.private_turn_snapshot_cli import (
    _sanitize,
    candidate_sites,
)


class _Headers(dict):
    def get(self, key: str, default: str = "") -> str:
        return str(super().get(key, default))


class _Response:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")
        self.headers = _Headers()

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Opener:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.request = None
        self.timeout = None

    def open(self, request, timeout: float):
        self.request = request
        self.timeout = timeout
        return _Response(self.payload)


def test_loadturn_posts_api_key_in_body_not_url() -> None:
    payload = {
        "success": True,
        "rst": {
            "game": {"id": 686764, "turn": 42},
            "player": {"id": 3},
        },
    }
    client = PlanetsNuPublicApi(allow_direct=True)
    opener = _Opener(payload)
    client._opener = opener

    result = client.load_turn(686764, "super-secret", turn=42)

    assert result == payload
    assert opener.request is not None
    assert opener.request.get_method() == "POST"
    assert opener.request.full_url.endswith("/game/loadturn")
    assert "super-secret" not in opener.request.full_url

    posted = parse_qs(opener.request.data.decode("utf-8"))
    assert posted["gameid"] == ["686764"]
    assert posted["apikey"] == ["super-secret"]
    assert posted["turn"] == ["42"]
    assert posted["forsave"] == ["true"]
    assert posted["activity"] == ["true"]


def test_sanitize_removes_sensitive_keys_recursively() -> None:
    raw = {
        "apikey": "a",
        "savekey": "b",
        "rst": {
            "password": "c",
            "ships": [{"id": 1, "savekey": "d"}],
        },
    }
    assert _sanitize(raw) == {
        "rst": {
            "ships": [{"id": 1}],
        }
    }


def test_candidate_sites_requires_own_plus_two_other_ships(
    tmp_path: Path,
    capsys,
) -> None:
    payload = {
        "rst": {
            "game": {"id": 686764, "turn": 50},
            "player": {"id": 3},
            "ships": [
                {
                    "id": 10,
                    "ownerid": 3,
                    "hullid": 1,
                    "x": 100,
                    "y": 200,
                    "warp": 0,
                    "mission": 3,
                    "enemy": 5,
                    "friendlycode": "abc",
                },
                {
                    "id": 20,
                    "ownerid": 5,
                    "hullid": 2,
                    "x": 100,
                    "y": 200,
                    "warp": 0,
                    "mission": 3,
                    "enemy": 3,
                    "friendlycode": "def",
                },
                {
                    "id": 21,
                    "ownerid": 5,
                    "hullid": 3,
                    "x": 100,
                    "y": 200,
                    "warp": 0,
                    "mission": 1,
                    "enemy": 3,
                    "friendlycode": "999",
                },
                {
                    "id": 30,
                    "ownerid": 6,
                    "hullid": 4,
                    "x": 500,
                    "y": 600,
                },
            ],
        }
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    args = argparse.Namespace(input=path)

    assert candidate_sites(args) == 0
    output = capsys.readouterr().out
    assert "candidate_sites:     1" in output
    assert "OWN ship=10 owner=3" in output
    assert "OTHER ship=20 owner=5" in output
    assert "OTHER ship=21 owner=5" in output
    assert "ship=30" not in output
