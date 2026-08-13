import io
import zipfile

import pytest

from planets_lab.corpus.api import CorpusApiError, PlanetsNuPublicApi
from planets_lab.corpus.archive import archive_members
from planets_lab.corpus.discovery import finished_games
from planets_lab.corpus.manifest import build_game_manifest, settings_hash


class FakeClient:
    def games_for_username(self, name: str):
        if name == "one":
            return [{"id": 20, "status": 3}, {"id": 21, "status": 2}]
        return [{"id": 20, "status": 3}, {"id": 22, "status": 3}]


def test_network_client_requires_proxy(monkeypatch) -> None:
    monkeypatch.delenv("PLANETSNU_PROXY_URL", raising=False)
    with pytest.raises(CorpusApiError, match="PLANETSNU_PROXY_URL"):
        PlanetsNuPublicApi()


def test_finished_game_discovery_filters_and_deduplicates() -> None:
    games = finished_games(FakeClient(), ["one", "two"])
    assert [game["id"] for game in games] == [22, 20]


def test_manifest_keeps_race_slots_but_not_identity() -> None:
    manifest = build_game_manifest(
        {"id": 20, "status": 3},
        {
            "game": {"id": 20, "turn": 88},
            "settings": {"nuionstorms": True},
            "players": [
                {
                    "id": 4,
                    "raceid": 7,
                    "username": "public-name",
                    "accountid": 123,
                    "turnjoined": 1,
                }
            ],
        },
    )
    assert manifest["player_slots"] == [{"id": 4, "raceid": 7, "turnjoined": 1}]
    assert "username" not in repr(manifest)
    assert "accountid" not in repr(manifest)


def test_settings_hash_is_key_order_independent() -> None:
    assert settings_hash({"a": 1, "b": 2}) == settings_hash({"b": 2, "a": 1})


def test_archive_members_validates_zip() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("turns/example.json", "{}")
    assert archive_members(buffer.getvalue()) == ("turns/example.json",)


def test_archive_members_rejects_non_zip() -> None:
    with pytest.raises(ValueError, match="not a ZIP"):
        archive_members(b"not a zip")
