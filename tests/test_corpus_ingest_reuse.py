from __future__ import annotations

import io
import json
import sys
import zipfile

import pytest
from pathlib import Path

import planets_lab.corpus.ingest_manifest_cli as ingest_cli
from planets_lab.corpus.manifest import MANIFEST_SCHEMA


def _manifest(game_id: int = 42) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": "B",
        "settings_hash": "a" * 64,
        "game": {
            "id": game_id,
            "turn": 1,
            "dateended": "2026-09-29T00:00:00",
            "gametype": 2,
            "iscustom": False,
            "isprivate": False,
        },
        "settings": {},
        "player_slots": [{"id": 1, "raceid": 1}],
    }


def _archive(game_id: int = 42) -> bytes:
    payload = {
        "game": {"id": game_id, "turn": 0},
        "player": {"id": 1, "raceid": 1},
        "players": [{"id": 1, "raceid": 1}],
        "planets": [],
        "ships": [],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("player1-turn0.trn", json.dumps(payload))
    return buffer.getvalue()


def _run_ingest(
    monkeypatch,
    *,
    manifest: Path,
    cache_dir: Path,
    index_output: Path,
    stats_output: Path,
    extra: list[str] | None = None,
) -> int:
    argv = [
        "ingest-manifest",
        str(manifest),
        "--offline",
        "--cache-dir",
        str(cache_dir),
        "--index-output",
        str(index_output),
        "--stats-output",
        str(stats_output),
    ]
    if extra:
        argv.extend(extra)
    monkeypatch.setattr(sys, "argv", argv)
    return ingest_cli.main()


def test_ingest_reuses_previous_record_for_immutable_archive(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "game-42.zip").write_bytes(_archive())

    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(_manifest()) + "\n", encoding="utf-8")
    index_output = tmp_path / "games.jsonl"
    stats_output = tmp_path / "stats.json"

    assert _run_ingest(
        monkeypatch,
        manifest=manifest,
        cache_dir=cache_dir,
        index_output=index_output,
        stats_output=stats_output,
    ) == 0

    def must_not_reindex(*args, **kwargs):
        raise AssertionError("immutable cached game should reuse previous index record")

    monkeypatch.setattr(ingest_cli, "index_game_archive", must_not_reindex)

    assert _run_ingest(
        monkeypatch,
        manifest=manifest,
        cache_dir=cache_dir,
        index_output=index_output,
        stats_output=stats_output,
    ) == 0


def test_no_reuse_index_forces_rebuild(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "game-42.zip").write_bytes(_archive())

    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(_manifest()) + "\n", encoding="utf-8")
    index_output = tmp_path / "games.jsonl"
    stats_output = tmp_path / "stats.json"

    assert _run_ingest(
        monkeypatch,
        manifest=manifest,
        cache_dir=cache_dir,
        index_output=index_output,
        stats_output=stats_output,
    ) == 0

    original = ingest_cli.index_game_archive
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(ingest_cli, "index_game_archive", counted)

    assert _run_ingest(
        monkeypatch,
        manifest=manifest,
        cache_dir=cache_dir,
        index_output=index_output,
        stats_output=stats_output,
        extra=["--no-reuse-index"],
    ) == 0
    assert calls == 1



def test_ingest_checkpoints_success_before_interrupt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "game-42.zip").write_bytes(_archive(42))
    (cache_dir / "game-43.zip").write_bytes(_archive(43))

    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(_manifest(42)) + "\n" + json.dumps(_manifest(43)) + "\n",
        encoding="utf-8",
    )
    index_output = tmp_path / "games.jsonl"
    stats_output = tmp_path / "stats.json"

    original = ingest_cli.index_game_archive
    calls = 0

    def interrupt_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return original(*args, **kwargs)

    monkeypatch.setattr(ingest_cli, "index_game_archive", interrupt_second)

    with pytest.raises(KeyboardInterrupt):
        _run_ingest(
            monkeypatch,
            manifest=manifest,
            cache_dir=cache_dir,
            index_output=index_output,
            stats_output=stats_output,
        )

    records = [
        json.loads(line)
        for line in index_output.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stats = json.loads(stats_output.read_text(encoding="utf-8"))

    assert [record["game_id"] for record in records] == [42]
    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 0


def test_ingest_checkpoints_failure_before_interrupt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "game-42.zip").write_bytes(_archive(42))
    (cache_dir / "game-43.zip").write_bytes(_archive(43))

    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(_manifest(42)) + "\n" + json.dumps(_manifest(43)) + "\n",
        encoding="utf-8",
    )
    index_output = tmp_path / "games.jsonl"
    stats_output = tmp_path / "stats.json"

    calls = 0

    def fail_then_interrupt(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("synthetic normalization failure")
        raise KeyboardInterrupt

    monkeypatch.setattr(ingest_cli, "index_game_archive", fail_then_interrupt)

    with pytest.raises(KeyboardInterrupt):
        _run_ingest(
            monkeypatch,
            manifest=manifest,
            cache_dir=cache_dir,
            index_output=index_output,
            stats_output=stats_output,
        )

    stats = json.loads(stats_output.read_text(encoding="utf-8"))

    assert stats["games_indexed"] == 0
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [42]
