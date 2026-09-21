from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

from planets_lab.corpus.feature_index import feature_row, write_feature_index


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_classic_corpus_parity_audit.py"
spec = importlib.util.spec_from_file_location("combat_classic_corpus_parity_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


BEAMS = [
    {"id": 1, "crewkill": 10, "damage": 3},
    {"id": 2, "crewkill": 15, "damage": 1},
    {"id": 3, "crewkill": 3, "damage": 10},
    {"id": 4, "crewkill": 10, "damage": 25},
    {"id": 5, "crewkill": 9, "damage": 29},
    {"id": 6, "crewkill": 30, "damage": 20},
    {"id": 7, "crewkill": 20, "damage": 40},
]
TORPEDOES = [{"id": 6, "crewkill": 13, "damage": 30, "combatrange": 300}]


def _vcr() -> dict[str, object]:
    common = {
        "beamkillbonus": 1,
        "beamchargerate": 1,
        "torpchargerate": 1,
        "torpmisspercent": 35,
        "crewdefensepercent": 0,
        "hasstarbase": False,
    }
    return {
        "id": 2,
        "turn": 8,
        "seed": 49,
        "battletype": 1,
        "leftownerid": 4,
        "rightownerid": 3,
        "left": {
            **common,
            "objectid": 20,
            "beamcount": 10,
            "launchercount": 2,
            "baycount": 0,
            "hullid": 37,
            "beamid": 7,
            "torpedoid": 6,
            "shield": 100,
            "damage": 0,
            "crew": 525,
            "mass": 275,
            "raceid": 4,
            "torpedos": 5,
            "fighters": 0,
        },
        "right": {
            **common,
            "objectid": 35,
            "beamcount": 0,
            "launchercount": 0,
            "baycount": 0,
            "hullid": 0,
            "beamid": 1,
            "torpedoid": 0,
            "shield": 0,
            "damage": 0,
            "crew": 10000,
            "mass": 100,
            "raceid": 3,
            "torpedos": 0,
            "fighters": 0,
        },
    }


def _turn(player: int, *, settings: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "game": {"id": 123456, "turn": 8},
        "player": {"id": player},
        "settings": settings if settings is not None else {"combatrng": 0},
        "beams": BEAMS,
        "torpedos": TORPEDOES,
        "vcrs": [_vcr()],
    }


def _write_archive(path: Path, turns: list[dict[str, object]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, turn in enumerate(turns, start=1):
            archive.writestr(
                f"player{index}-turn8.trn",
                json.dumps(turn, sort_keys=True).encode("utf-8"),
            )


def _args(path: Path, *, manifest: Path | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        archive=[str(path)],
        archive_dir=path.parent,
        settings_manifest=manifest,
        output=None,
        detail_limit=100,
        include_supported=False,
        feature_index=None,
        feature_profile="all-indexed",
    )


def test_duplicate_observers_collapse_to_one_supported_vcr(tmp_path: Path) -> None:
    path = tmp_path / "game-123456.zip"
    _write_archive(path, [_turn(1), _turn(2)])

    report = audit.run(_args(path))

    assert report["summary"]["raw_vcr_observations"] == 2
    assert report["summary"]["unique_vcrs"] == 1
    assert report["summary"]["replay_supported"] == 1
    assert report["summary"].get("payload_conflicts", 0) == 0
    assert report["summary"]["replay_accounted"] == 1


def test_manifest_supplies_missing_raw_combat_rng(tmp_path: Path) -> None:
    path = tmp_path / "game-123456.zip"
    _write_archive(path, [_turn(1, settings={})])
    manifest = tmp_path / "settings.json"
    manifest.write_text(json.dumps({"123456": 0}), encoding="utf-8")

    report = audit.run(_args(path, manifest=manifest))

    assert report["summary"]["replay_supported"] == 1
    assert report["settings_sources_per_turn_member"] == {"manifest": 1}


def test_raw_manifest_combat_rng_conflict_fails_closed() -> None:
    settings, source, error = audit._resolve_settings(
        game_id=123456,
        raw_settings={"combatrng": 0},
        manifest={123456: {"combatrng": 1}},
    )
    assert settings is None
    assert source == "conflict"
    assert error is not None and "conflicts" in error



def test_all_indexed_feature_selector_preserves_replay_result(tmp_path: Path) -> None:
    archive_path = tmp_path / "game-123456.zip"
    _write_archive(archive_path, [_turn(1), _turn(2)])

    baseline_args = _args(archive_path)
    baseline = audit.run(baseline_args)

    index_path = tmp_path / "game_features.parquet"
    database_path = tmp_path / "corpus.duckdb"
    write_feature_index(
        rows=[
            feature_row(
                game_id=123456,
                feature="game.status",
                value=3,
                known=True,
                source_kind="fixture",
                source_location="fixture",
            )
        ],
        parquet_path=index_path,
        database_path=database_path,
    )

    selected_args = _args(archive_path)
    selected_args.feature_index = index_path
    selected_args.feature_profile = "all-indexed"
    selected = audit.run(selected_args)

    assert selected["summary"] == baseline["summary"]
    assert selected["battle_shapes"] == baseline["battle_shapes"]
    assert selected["games"] == baseline["games"]
    assert selected["settings_sources_per_turn_member"] == (
        baseline["settings_sources_per_turn_member"]
    )
    assert selected["feature_selection"] == {
        "index": str(index_path),
        "profile": "all-indexed",
        "predicate_count": 0,
        "included_game_ids": [123456],
        "excluded_game_ids": [],
        "unknown_game_ids": [],
    }
