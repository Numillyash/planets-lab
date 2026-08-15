from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
from typing import Any

from .columnar_io import write_rows_parquet_arrow
from .compiled_movement import (
    COMPILED_MOVEMENT_SCHEMA,
    GAME_METADATA_COLUMNS,
    MOVEMENT_COLUMNS,
    compile_movement_rows,
    create_compiled_catalog,
    movement_row_stats,
    query_compiled_stats,
)
from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_topology_diagnostics import extract_map_topology
from .prepared_cache import (
    PREPARED_GAME_CACHE_SCHEMA,
    load_or_build_prepared_game_cache,
)


BUILD_SUMMARY_SCHEMA = "planets-lab.compiled-movement-build.v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_meta(
    path: Path,
    *,
    game_id: int,
    settings_hash: str,
    archive_sha256: str,
) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    if value.get("compiled_schema") != COMPILED_MOVEMENT_SCHEMA:
        return None
    if value.get("prepared_schema") != PREPARED_GAME_CACHE_SCHEMA:
        return None
    if value.get("game_id") != game_id:
        return None
    if value.get("settings_hash") != settings_hash:
        return None
    if value.get("archive_sha256") != archive_sha256:
        return None
    required_topology_keys = {
        "sphere",
        "map_width",
        "map_height",
        "map_shape",
        "topology_stable",
    }
    if not required_topology_keys.issubset(value):
        return None
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _stage_seconds(start: float, end: float) -> float:
    return round(end - start, 3)


def _process_game(task: tuple[int, int, dict[str, Any], str, str, str, bool]) -> dict[str, Any]:
    (
        position,
        total,
        manifest,
        cache_dir_text,
        prepared_dir_text,
        output_dir_text,
        rebuild,
    ) = task
    game_id = int(manifest["game_id"])
    settings_hash = str(manifest["settings_hash"])
    cache_dir = Path(cache_dir_text)
    prepared_dir = Path(prepared_dir_text)
    output_dir = Path(output_dir_text)
    archive_path = cache_dir / f"game-{game_id}.zip"
    partition_dir = output_dir / "mechanics" / "movement_transitions" / f"game_id={game_id}"
    parquet_path = partition_dir / "part-000.parquet"
    meta_path = partition_dir / "_meta.json"

    started = perf_counter()
    try:
        archive_data = archive_path.read_bytes()
        after_read = perf_counter()
        archive_sha256 = _sha256(archive_data)

        if not rebuild and parquet_path.is_file() and meta_path.is_file():
            cached_meta = _read_meta(
                meta_path,
                game_id=game_id,
                settings_hash=settings_hash,
                archive_sha256=archive_sha256,
            )
            if cached_meta is not None:
                finished = perf_counter()
                result = dict(cached_meta)
                result.update(
                    {
                        "status": "ok",
                        "position": position,
                        "total": total,
                        "compiled_cache_hit": True,
                        "prepared_cache_hit": None,
                        "elapsed_seconds": _stage_seconds(started, finished),
                        "timing_seconds": {
                            "archive_read": _stage_seconds(started, after_read),
                            "cache_validation": _stage_seconds(after_read, finished),
                        },
                    }
                )
                return result

        topology = extract_map_topology(archive_data)
        after_topology = perf_counter()
        prepared_path = prepared_dir / f"game-{game_id}.pickle"
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        after_prepared = perf_counter()
        rows = compile_movement_rows(
            game_id=game_id,
            settings_hash=settings_hash,
            prepared=prepared,
            topology=topology,
        )
        after_compile = perf_counter()
        stats = movement_row_stats(rows)
        write_rows_parquet_arrow(
            rows=rows,
            columns=MOVEMENT_COLUMNS,
            path=parquet_path,
        )
        after_parquet = perf_counter()

        meta = {
            "compiled_schema": COMPILED_MOVEMENT_SCHEMA,
            "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
            "game_id": game_id,
            "settings_hash": settings_hash,
            "archive_sha256": archive_sha256,
            "sphere": topology.sphere,
            "map_width": topology.mapwidth,
            "map_height": topology.mapheight,
            "map_shape": str(topology.mapshape) if topology.mapshape is not None else None,
            "topology_stable": topology.stable,
            "snapshots": len(prepared.snapshots),
            **stats,
            "parquet_bytes": parquet_path.stat().st_size,
        }
        _write_json_atomic(meta_path, meta)
        finished = perf_counter()
        return {
            "status": "ok",
            "position": position,
            "total": total,
            "compiled_cache_hit": False,
            "prepared_cache_hit": prepared_hit,
            "elapsed_seconds": _stage_seconds(started, finished),
            "timing_seconds": {
                "archive_read": _stage_seconds(started, after_read),
                "topology": _stage_seconds(after_read, after_topology),
                "prepared": _stage_seconds(after_topology, after_prepared),
                "compile": _stage_seconds(after_prepared, after_compile),
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


def _archive_size(task: tuple[int, int, dict[str, Any], str, str, str, bool]) -> int:
    manifest = task[2]
    cache_dir = Path(task[3])
    game_id = int(manifest["game_id"])
    try:
        return (cache_dir / f"game-{game_id}.zip").stat().st_size
    except OSError:
        return -1


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
                "compiled_cache_hit": row["compiled_cache_hit"],
                "prepared_cache_hit": row["prepared_cache_hit"],
                "sphere": row["sphere"],
                "transition_rows": row["transition_rows"],
                "move_most_candidates": row["move_most_candidates"],
                "post_external_residual": row["post_external_residual"],
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
            "Compile historical movement transitions into partitioned Parquet and "
            "create a DuckDB catalog over the dataset."
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
        "--output-dir",
        type=Path,
        default=Path("validation/corpus/compiled/v1"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--game-id",
        type=int,
        action="append",
        default=None,
        help="Compile only the selected game ID; may be repeated.",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    try:
        manifests = load_manifest_jsonl(args.manifest.read_text(encoding="utf-8"))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc))
        return 2

    if args.game_id:
        requested_ids = set(args.game_id)
        manifests = [row for row in manifests if int(row["game_id"]) in requested_ids]
        found_ids = {int(row["game_id"]) for row in manifests}
        missing_ids = sorted(requested_ids - found_ids)
        if missing_ids:
            print(f"game IDs not found in manifest: {missing_ids}")
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
            str(args.output_dir),
            bool(args.rebuild),
        )
        for position, manifest in enumerate(manifests, start=1)
    ]

    scheduled = sorted(tasks, key=_archive_size, reverse=True)
    jobs = max(1, min(int(args.jobs), max(1, total)))
    started = perf_counter()
    print(
        json.dumps(
            {
                "event": "compile_start",
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

    if successes:
        metadata_dir = args.output_dir / "metadata"
        games_parquet = metadata_dir / "games.parquet"
        games_rows = [
            {
                key: row.get(key)
                for key in (
                    "game_id",
                    "settings_hash",
                    "archive_sha256",
                    "prepared_schema",
                    "compiled_schema",
                    "sphere",
                    "map_width",
                    "map_height",
                    "map_shape",
                    "topology_stable",
                    "snapshots",
                    "transition_rows",
                    "geometry_ready",
                    "move_most_candidates",
                    "baseline_explained",
                    "baseline_unresolved",
                    "external_context_explained",
                    "post_external_residual",
                    "parquet_bytes",
                )
            }
            for row in successes
        ]
        write_rows_parquet_arrow(
            rows=games_rows,
            columns=GAME_METADATA_COLUMNS,
            path=games_parquet,
        )
        database_path = args.output_dir / "corpus.duckdb"
        movement_glob = (
            args.output_dir
            / "mechanics"
            / "movement_transitions"
            / "game_id=*"
            / "part-000.parquet"
        )
        create_compiled_catalog(
            database_path=database_path,
            games_parquet=games_parquet,
            movement_glob=movement_glob,
        )
        stats = query_compiled_stats(database_path)
    else:
        database_path = args.output_dir / "corpus.duckdb"
        stats = {
            "transition_rows": 0,
            "geometry_ready": 0,
            "move_most_candidates": 0,
            "baseline_explained": 0,
            "baseline_unresolved": 0,
            "external_context_explained": 0,
            "post_external_residual": 0,
        }

    if stats["baseline_explained"] + stats["baseline_unresolved"] != stats["move_most_candidates"]:
        raise AssertionError("compiled baseline accounting is not closed")
    if stats["external_context_explained"] + stats["post_external_residual"] != stats["baseline_unresolved"]:
        raise AssertionError("compiled external-context accounting is not closed")

    summary = {
        "schema": BUILD_SUMMARY_SCHEMA,
        "compiled_schema": COMPILED_MOVEMENT_SCHEMA,
        "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
        "jobs": jobs,
        "games_requested": total,
        "games_compiled": len(successes),
        "games_failed": len(failures),
        "failed_game_ids": sorted(int(row["game_id"]) for row in failures),
        "compiled_cache_hits": sum(row.get("compiled_cache_hit") is True for row in successes),
        "compiled_cache_misses": sum(row.get("compiled_cache_hit") is False for row in successes),
        "prepared_cache_hits_on_compile": sum(row.get("prepared_cache_hit") is True for row in successes),
        "prepared_cache_misses_on_compile": sum(row.get("prepared_cache_hit") is False for row in successes),
        "parquet_bytes": sum(int(row.get("parquet_bytes", 0)) for row in successes),
        "wall_seconds": round(perf_counter() - started, 3),
        **stats,
        "database": str(database_path),
    }
    _write_json_atomic(args.output_dir / "metadata" / "build.json", summary)

    print("===== COMPILED MOVEMENT CORPUS SUMMARY =====", flush=True)
    for key in (
        "jobs",
        "games_compiled",
        "games_failed",
        "compiled_cache_hits",
        "compiled_cache_misses",
        "prepared_cache_hits_on_compile",
        "prepared_cache_misses_on_compile",
        "transition_rows",
        "geometry_ready",
        "move_most_candidates",
        "baseline_explained",
        "baseline_unresolved",
        "external_context_explained",
        "post_external_residual",
        "parquet_bytes",
        "wall_seconds",
    ):
        print(f"{key}: {summary[key]}", flush=True)
    print(f"database: {database_path}", flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
