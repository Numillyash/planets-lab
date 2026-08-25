from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
from typing import Any

from .columnar_io import write_rows_parquet_arrow
from .compiled_movement import COMPILED_MOVEMENT_SCHEMA
from .compiled_movement_labels import (
    COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA,
    MOVEMENT_CONTEXT_LABEL_COLUMNS,
    compile_movement_context_label_rows,
    movement_context_label_stats,
    query_movement_context_label_catalog_stats,
    refresh_movement_context_label_views,
)
from .field_reconstruction import clear_reconstruction_cache
from .indexer import CorpusIndexError, load_manifest_jsonl
from .prepared_cache import (
    PREPARED_GAME_CACHE_SCHEMA,
    load_or_build_prepared_game_cache,
)
from .readiness import clear_readiness_cache


BUILD_SUMMARY_SCHEMA = "planets-lab.compiled-movement-context-label-build.v1"
_STAT_KEYS = (
    "external_residual_rows",
    "label_issues",
    "chunnel_explained",
    "post_chunnel_residual",
    "horwasp_ballistic_candidates",
    "horwasp_mite_residual",
    "horwasp_strong_explained",
    "horwasp_observed_context_explained",
    "post_horwasp_strong_residual",
    "mine_strong_explained",
    "post_mine_strong_residual",
    "fuel_proration_explained",
    "post_fuel_proration_residual",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


MappingLike = dict[str, Any]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _valid_cached_label_meta(
    path: Path,
    *,
    game_id: int,
    settings_hash: str,
    archive_sha256: str,
    movement_sha256: str,
) -> dict[str, Any] | None:
    value = _read_json(path)
    if value is None:
        return None
    expected = {
        "label_schema": COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA,
        "source_movement_schema": COMPILED_MOVEMENT_SCHEMA,
        "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "archive_sha256": archive_sha256,
        "source_movement_sha256": movement_sha256,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        return None
    if not all(key in value for key in _STAT_KEYS):
        return None
    return value


def _stage_seconds(start: float, end: float) -> float:
    return round(end - start, 3)


def _process_game(task: tuple[int, int, dict[str, Any], str, str, str, bool]) -> dict[str, Any]:
    position, total, manifest, cache_dir_text, prepared_dir_text, compiled_dir_text, rebuild = task
    game_id = int(manifest["game_id"])
    settings_hash = str(manifest["settings_hash"])
    cache_dir = Path(cache_dir_text)
    prepared_dir = Path(prepared_dir_text)
    compiled_dir = Path(compiled_dir_text)
    archive_path = cache_dir / f"game-{game_id}.zip"
    movement_dir = compiled_dir / "mechanics" / "movement_transitions" / f"game_id={game_id}"
    movement_parquet = movement_dir / "part-000.parquet"
    movement_meta_path = movement_dir / "_meta.json"
    label_dir = compiled_dir / "labels" / "movement_context" / f"game_id={game_id}"
    label_parquet = label_dir / "part-000.parquet"
    label_meta_path = label_dir / "_meta.json"

    clear_readiness_cache()
    clear_reconstruction_cache()
    started = perf_counter()
    try:
        movement_meta = _read_json(movement_meta_path)
        if movement_meta is None or not movement_parquet.is_file():
            raise ValueError(f"game {game_id} compiled movement partition is missing")
        if movement_meta.get("compiled_schema") != COMPILED_MOVEMENT_SCHEMA:
            raise ValueError(f"game {game_id} compiled movement schema mismatch")
        if movement_meta.get("settings_hash") != settings_hash:
            raise ValueError(f"game {game_id} settings hash differs from movement partition")

        archive_data = archive_path.read_bytes()
        after_archive = perf_counter()
        archive_sha256 = _sha256(archive_data)
        movement_sha256 = _file_sha256(movement_parquet)
        after_hashes = perf_counter()

        if not rebuild and label_parquet.is_file() and label_meta_path.is_file():
            cached = _valid_cached_label_meta(
                label_meta_path,
                game_id=game_id,
                settings_hash=settings_hash,
                archive_sha256=archive_sha256,
                movement_sha256=movement_sha256,
            )
            if cached is not None:
                finished = perf_counter()
                return {
                    "status": "ok",
                    "position": position,
                    "total": total,
                    "compiled_label_cache_hit": True,
                    "prepared_cache_hit": None,
                    "elapsed_seconds": _stage_seconds(started, finished),
                    "timing_seconds": {
                        "archive_read": _stage_seconds(started, after_archive),
                        "hashes_and_validation": _stage_seconds(after_archive, finished),
                    },
                    **cached,
                }

        prepared_path = prepared_dir / f"game-{game_id}.pickle"
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        after_prepared = perf_counter()
        rows = compile_movement_context_label_rows(
            game_id=game_id,
            archive_data=archive_data,
            prepared=prepared,
            movement_parquet=movement_parquet,
        )
        after_compile = perf_counter()
        stats = movement_context_label_stats(rows)

        expected_residual = int(movement_meta.get("post_external_residual", -1))
        if stats["external_residual_rows"] != expected_residual:
            raise AssertionError(
                f"game {game_id} label source rows {stats['external_residual_rows']} "
                f"!= movement residual {expected_residual}"
            )

        write_rows_parquet_arrow(
            rows=rows,
            columns=MOVEMENT_CONTEXT_LABEL_COLUMNS,
            path=label_parquet,
        )
        after_parquet = perf_counter()
        meta = {
            "label_schema": COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA,
            "source_movement_schema": COMPILED_MOVEMENT_SCHEMA,
            "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
            "game_id": game_id,
            "settings_hash": settings_hash,
            "archive_sha256": archive_sha256,
            "source_movement_sha256": movement_sha256,
            **stats,
            "parquet_bytes": label_parquet.stat().st_size,
        }
        _write_json_atomic(label_meta_path, meta)
        finished = perf_counter()
        return {
            "status": "ok",
            "position": position,
            "total": total,
            "compiled_label_cache_hit": False,
            "prepared_cache_hit": prepared_hit,
            "elapsed_seconds": _stage_seconds(started, finished),
            "timing_seconds": {
                "archive_read": _stage_seconds(started, after_archive),
                "hashes": _stage_seconds(after_archive, after_hashes),
                "prepared": _stage_seconds(after_hashes, after_prepared),
                "compile_labels": _stage_seconds(after_prepared, after_compile),
                "parquet": _stage_seconds(after_compile, after_parquet),
                "metadata": _stage_seconds(after_parquet, finished),
            },
            **meta,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "position": position,
            "total": total,
            "game_id": game_id,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": _stage_seconds(started, perf_counter()),
        }


def _task_weight(task: tuple[int, int, dict[str, Any], str, str, str, bool]) -> int:
    game_id = int(task[2]["game_id"])
    prepared = Path(task[4]) / f"game-{game_id}.pickle"
    archive = Path(task[3]) / f"game-{game_id}.zip"
    for path in (prepared, archive):
        try:
            return path.stat().st_size
        except OSError:
            pass
    return -1


def _collect_valid_label_catalog(compiled_dir: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    root = compiled_dir / "labels" / "movement_context"
    metadata: list[dict[str, Any]] = []
    paths: list[Path] = []
    if not root.is_dir():
        return metadata, paths

    for label_meta_path in sorted(root.glob("game_id=*/_meta.json")):
        label_meta = _read_json(label_meta_path)
        if label_meta is None:
            continue
        try:
            game_id = int(label_meta["game_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if label_meta.get("label_schema") != COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA:
            continue
        if label_meta.get("source_movement_schema") != COMPILED_MOVEMENT_SCHEMA:
            continue
        movement_dir = compiled_dir / "mechanics" / "movement_transitions" / f"game_id={game_id}"
        movement_meta = _read_json(movement_dir / "_meta.json")
        movement_parquet = movement_dir / "part-000.parquet"
        label_parquet = label_meta_path.parent / "part-000.parquet"
        if movement_meta is None or not movement_parquet.is_file() or not label_parquet.is_file():
            continue
        if movement_meta.get("compiled_schema") != COMPILED_MOVEMENT_SCHEMA:
            continue
        if label_meta.get("archive_sha256") != movement_meta.get("archive_sha256"):
            continue
        if label_meta.get("settings_hash") != movement_meta.get("settings_hash"):
            continue
        if label_meta.get("source_movement_sha256") != _file_sha256(movement_parquet):
            continue
        metadata.append(label_meta)
        paths.append(label_parquet)

    paired = sorted(zip(metadata, paths), key=lambda item: int(item[0]["game_id"]))
    return [item[0] for item in paired], [item[1] for item in paired]


def _stats_from_results(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {key: sum(int(row.get(key, 0) or 0) for row in rows) for key in _STAT_KEYS}


def _assert_label_accounting(stats: dict[str, int], *, scope: str) -> None:
    if stats["chunnel_explained"] + stats["post_chunnel_residual"] != stats["external_residual_rows"]:
        raise AssertionError(f"{scope} Chunnel accounting is not closed")
    if stats["horwasp_strong_explained"] + stats["post_horwasp_strong_residual"] != stats["post_chunnel_residual"]:
        raise AssertionError(f"{scope} Horwasp strong accounting is not closed")
    if stats["mine_strong_explained"] + stats["post_mine_strong_residual"] != stats["post_horwasp_strong_residual"]:
        raise AssertionError(f"{scope} mine strong accounting is not closed")
    if stats["fuel_proration_explained"] + stats["post_fuel_proration_residual"] != stats["post_mine_strong_residual"]:
        raise AssertionError(f"{scope} fuel-proration accounting is not closed")


def _print_game_result(row: dict[str, Any]) -> None:
    if row.get("status") != "ok":
        print(json.dumps(row, sort_keys=True), flush=True)
        return
    print(
        json.dumps(
            {
                "status": "ok",
                "position": row["position"],
                "total": row["total"],
                "game_id": row["game_id"],
                "compiled_label_cache_hit": row["compiled_label_cache_hit"],
                "prepared_cache_hit": row["prepared_cache_hit"],
                "external_residual_rows": row["external_residual_rows"],
                "chunnel_explained": row["chunnel_explained"],
                "post_chunnel_residual": row["post_chunnel_residual"],
                "horwasp_strong_explained": row["horwasp_strong_explained"],
                "post_horwasp_strong_residual": row["post_horwasp_strong_residual"],
                "mine_strong_explained": row["mine_strong_explained"],
                "post_mine_strong_residual": row["post_mine_strong_residual"],
                "fuel_proration_explained": row["fuel_proration_explained"],
                "post_fuel_proration_residual": row["post_fuel_proration_residual"],
                "label_issues": row["label_issues"],
                "parquet_bytes": row["parquet_bytes"],
                "elapsed_seconds": row["elapsed_seconds"],
                "timing_seconds": row.get("timing_seconds", {}),
            },
            sort_keys=True,
        ),
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile privacy-safe Chunnel, Horwasp, mine-hit and strict documented "
            "fuel-proration labels over the existing post-external movement residual "
            "Parquet dataset."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall"))
    parser.add_argument(
        "--prepared-cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/prepared-v1"),
    )
    parser.add_argument(
        "--compiled-dir",
        type=Path,
        default=Path("validation/corpus/compiled/v1"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--game-id", type=int, action="append", default=None)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    try:
        manifests = load_manifest_jsonl(args.manifest.read_text(encoding="utf-8"))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc))
        return 2
    if args.game_id:
        requested = set(args.game_id)
        manifests = [row for row in manifests if int(row["game_id"]) in requested]
        found = {int(row["game_id"]) for row in manifests}
        missing = sorted(requested - found)
        if missing:
            print(f"game IDs not found in manifest: {missing}")
            return 2
    if args.limit is not None:
        manifests = manifests[: max(0, args.limit)]

    total = len(manifests)
    tasks = [
        (
            position,
            total,
            dict(manifest),
            str(args.cache_dir),
            str(args.prepared_cache_dir),
            str(args.compiled_dir),
            bool(args.rebuild),
        )
        for position, manifest in enumerate(manifests, start=1)
    ]
    scheduled = sorted(tasks, key=_task_weight, reverse=True)
    jobs = max(1, min(int(args.jobs), max(1, total)))
    started = perf_counter()
    print(
        json.dumps(
            {
                "event": "label_compile_start",
                "games": total,
                "jobs": jobs,
                "scheduled_game_ids": [int(task[2]["game_id"]) for task in scheduled],
            },
            sort_keys=True,
        ),
        flush=True,
    )

    results: list[dict[str, Any]] = []
    if jobs == 1:
        for task in scheduled:
            row = _process_game(task)
            results.append(row)
            _print_game_result(row)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = [executor.submit(_process_game, task) for task in scheduled]
            for future in as_completed(futures):
                row = future.result()
                results.append(row)
                _print_game_result(row)
    results.sort(key=lambda row: int(row.get("position", 0)))

    failures = [row for row in results if row.get("status") != "ok"]
    successes = [row for row in results if row.get("status") == "ok"]
    run_stats = _stats_from_results(successes)
    _assert_label_accounting(run_stats, scope="run")

    catalog_meta, catalog_paths = _collect_valid_label_catalog(args.compiled_dir)
    database_path = args.compiled_dir / "corpus.duckdb"
    if catalog_paths:
        refresh_movement_context_label_views(
            database_path=database_path,
            label_parquet_paths=catalog_paths,
        )
        catalog = query_movement_context_label_catalog_stats(database_path)
        catalog_accounting = {
            "external_residual_rows": catalog["labeled_residual_rows"],
            "chunnel_explained": catalog["chunnel_explained"],
            "post_chunnel_residual": catalog["post_chunnel_residual"],
            "horwasp_strong_explained": catalog["horwasp_strong_explained"],
            "post_horwasp_strong_residual": catalog["post_horwasp_strong_residual"],
            "mine_strong_explained": catalog["mine_strong_explained"],
            "post_mine_strong_residual": catalog["post_mine_strong_residual"],
            "fuel_proration_explained": catalog["fuel_proration_explained"],
            "post_fuel_proration_residual": catalog["post_fuel_proration_residual"],
        }
        _assert_label_accounting(catalog_accounting, scope="catalog labeled rows")
    else:
        catalog = {
            "movement_residual_rows": 0,
            "labeled_residual_rows": 0,
            "unlabeled_residual_rows": 0,
            "label_issues": 0,
            "chunnel_explained": 0,
            "post_chunnel_residual": 0,
            "horwasp_ballistic_candidates": 0,
            "horwasp_mite_residual": 0,
            "horwasp_strong_explained": 0,
            "horwasp_observed_context_explained": 0,
            "post_horwasp_strong_residual": 0,
            "mine_strong_explained": 0,
            "post_mine_strong_residual": 0,
            "fuel_proration_explained": 0,
            "post_fuel_proration_residual": 0,
        }

    summary = {
        "schema": BUILD_SUMMARY_SCHEMA,
        "label_schema": COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA,
        "source_movement_schema": COMPILED_MOVEMENT_SCHEMA,
        "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
        "jobs": jobs,
        "games_requested": total,
        "games_compiled": len(successes),
        "games_failed": len(failures),
        "failed_game_ids": sorted(int(row["game_id"]) for row in failures),
        "compiled_label_cache_hits": sum(
            row.get("compiled_label_cache_hit") is True for row in successes
        ),
        "compiled_label_cache_misses": sum(
            row.get("compiled_label_cache_hit") is False for row in successes
        ),
        "prepared_cache_hits_on_compile": sum(
            row.get("prepared_cache_hit") is True for row in successes
        ),
        "prepared_cache_misses_on_compile": sum(
            row.get("prepared_cache_hit") is False for row in successes
        ),
        "parquet_bytes": sum(int(row.get("parquet_bytes", 0) or 0) for row in successes),
        "wall_seconds": round(perf_counter() - started, 3),
        **run_stats,
        "catalog_games_labeled": len(catalog_meta),
        **{f"catalog_{key}": value for key, value in catalog.items()},
        "catalog_label_parquet_bytes": sum(
            int(row.get("parquet_bytes", 0) or 0) for row in catalog_meta
        ),
        "database": str(database_path),
    }
    build_path = args.compiled_dir / "labels" / "movement_context" / "metadata" / "build.json"
    _write_json_atomic(build_path, summary)

    print("===== COMPILED MOVEMENT LABEL RUN SUMMARY =====", flush=True)
    for key in (
        "jobs",
        "games_compiled",
        "games_failed",
        "compiled_label_cache_hits",
        "compiled_label_cache_misses",
        "prepared_cache_hits_on_compile",
        "prepared_cache_misses_on_compile",
        *_STAT_KEYS,
        "parquet_bytes",
        "wall_seconds",
    ):
        print(f"{key}: {summary[key]}", flush=True)

    print("===== COMPILED MOVEMENT LABEL CATALOG SUMMARY =====", flush=True)
    print(f"catalog_games_labeled: {summary['catalog_games_labeled']}", flush=True)
    for key in catalog:
        print(f"catalog_{key}: {summary[f'catalog_{key}']}", flush=True)
    print(f"catalog_label_parquet_bytes: {summary['catalog_label_parquet_bytes']}", flush=True)
    print(f"database: {database_path}", flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
