from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_classic_corpus_parity_audit.py"
spec = importlib.util.spec_from_file_location("combat_classic_corpus_parity_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


BEAMS = [{"id": 7, "crewkill": 20, "damage": 40}]
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
            "beamid": 7,
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
