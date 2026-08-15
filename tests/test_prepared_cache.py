import io
import json
import zipfile

from planets_lab.corpus.field_reconstruction import (
    clear_reconstruction_cache,
    reconstruct_fields,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.readiness import (
    MOVEMENT_GEOMETRY,
    clear_readiness_cache,
    evaluate_readiness,
)


def _turn_payload(turn: int, x: int) -> dict:
    return {
        "game": {"id": 7, "turn": turn},
        "player": {"id": 1, "raceid": 1},
        "players": [{"id": 1, "raceid": 1}],
        "settings": {"nowarpwells": False},
        "planets": [],
        "ships": [
            {
                "id": 10,
                "ownerid": 1,
                "hullid": 3,
                "x": x,
                "y": 100,
                "warp": 5,
                "targetx": 125,
                "targety": 100,
                "mission": 0,
                "friendlycode": "abc",
                "infoturn": turn,
            }
        ],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
    }


def _archive(*, final_x: int = 125) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("player1-turn10.trn", json.dumps(_turn_payload(10, 100)))
        archive.writestr("player1-turn11.trn", json.dumps(_turn_payload(11, final_x)))
    return buffer.getvalue()


def test_prepared_cache_builds_then_reuses_and_seeds_process_caches(tmp_path) -> None:
    cache_path = tmp_path / "game-7.pickle"
    data = _archive()

    clear_reconstruction_cache()
    clear_readiness_cache()
    first, first_hit = load_or_build_prepared_game_cache(
        data,
        game_id=7,
        cache_path=cache_path,
    )
    assert first_hit is False
    assert cache_path.is_file()
    assert reconstruct_fields(first.snapshots) is first.reconstruction
    assert (
        evaluate_readiness(first.snapshots, MOVEMENT_GEOMETRY)
        is first.movement_geometry_readiness
    )

    clear_reconstruction_cache()
    clear_readiness_cache()
    second, second_hit = load_or_build_prepared_game_cache(
        data,
        game_id=7,
        cache_path=cache_path,
    )
    assert second_hit is True
    assert reconstruct_fields(second.snapshots) is second.reconstruction
    assert (
        evaluate_readiness(second.snapshots, MOVEMENT_GEOMETRY)
        is second.movement_geometry_readiness
    )


def test_prepared_cache_invalidates_when_archive_changes(tmp_path) -> None:
    cache_path = tmp_path / "game-7.pickle"
    original, original_hit = load_or_build_prepared_game_cache(
        _archive(final_x=125),
        game_id=7,
        cache_path=cache_path,
    )
    assert original_hit is False

    changed, changed_hit = load_or_build_prepared_game_cache(
        _archive(final_x=124),
        game_id=7,
        cache_path=cache_path,
    )
    assert changed_hit is False
    assert changed.archive_sha256 != original.archive_sha256
