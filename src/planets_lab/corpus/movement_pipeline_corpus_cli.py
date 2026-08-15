from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any

from .field_reconstruction import clear_reconstruction_cache
from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_chunnel_context import (
    aggregate_chunnel_residual_games,
    summarize_chunnel_residual_game,
)
from .movement_differential import (
    aggregate_movement_differential_games,
    summarize_movement_differential_game,
)
from .movement_horwasp_ballistic_context import evaluate_horwasp_ballistic_context
from .movement_residual_context import (
    aggregate_movement_residual_context_games,
    summarize_movement_residual_context_game,
)
from .normalizer import CorpusNormalizationError
from .prepared_cache import load_or_build_prepared_game_cache
from .readiness import clear_readiness_cache

PIPELINE_SCHEMA = "planets-lab.movement-pipeline-corpus.v2"


def _horwasp_stats(rows: list[dict[str, Any]], failed_game_ids: list[int]) -> dict[str, Any]:
    categories: Counter[str] = Counter()
    explained_hulls: Counter[str] = Counter()
    unresolved_hulls: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    settings_hashes: set[str] = set()

    for row in rows:
        settings_hashes.add(str(row["settings_hash"]))
        for key in (
            "residual_before",
            "ballistic_candidates",
            "mite_residual",
            "strong_explained",
            "observed_context_explained",
            "ballistic_unresolved",
            "residual_after_strong",
            "residual_after_observed",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value
        categories.update({str(k): int(v) for k, v in row.get("category_counts", {}).items()})
        explained_hulls.update(
            {str(k): int(v) for k, v in row.get("explained_hull_counts", {}).items()}
        )
        unresolved_hulls.update(
            {str(k): int(v) for k, v in row.get("unresolved_hull_counts", {}).items()}
        )

    return {
        "games_indexed": len(rows),
        "games_failed": len(set(failed_game_ids)),
        "failed_game_ids": sorted(set(failed_game_ids)),
        "settings_hashes": len(settings_hashes),
        **{key: int(value) for key, value in totals.items()},
        "category_counts": dict(sorted(categories.items(), key=lambda item: (-item[1], item[0]))),
        "explained_hull_counts": dict(
            sorted(explained_hulls.items(), key=lambda item: (-item[1], int(item[0])))
        ),
        "unresolved_hull_counts": dict(
            sorted(unresolved_hulls.items(), key=lambda item: (-item[1], int(item[0])))
        ),
    }


def _process_game(
    task: tuple[int, int, dict[str, Any], str, str, bool]
) -> dict[str, Any]:
    (
        position,
        total,
        manifest,
        cache_dir_text,
        prepared_cache_dir_text,
        rebuild_prepared_cache,
    ) = task
    game_id = int(manifest["game_id"])
    settings_hash = str(manifest["settings_hash"])
    archive_path = Path(cache_dir_text) / f"game-{game_id}.zip"
    prepared_cache_path = Path(prepared_cache_dir_text) / f"game-{game_id}.pickle"

    # Release the previous game's large object graph before loading the next one
    # in a long-lived worker. Within this game all stages intentionally reuse it.
    clear_readiness_cache()
    clear_reconstruction_cache()

    started = perf_counter()
    try:
        t0 = perf_counter()
        archive_data = archive_path.read_bytes()
        prepared, prepared_cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_cache_path,
            rebuild=rebuild_prepared_cache,
        )
        snapshots = prepared.snapshots
        load_seconds = perf_counter() - t0
        try:
            prepared_cache_bytes = prepared_cache_path.stat().st_size
        except OSError:
            prepared_cache_bytes = 0

        t0 = perf_counter()
        baseline = summarize_movement_differential_game(
            game_id=game_id,
            settings_hash=settings_hash,
            snapshots=snapshots,
        )
        baseline_seconds = perf_counter() - t0

        t0 = perf_counter()
        residual = summarize_movement_residual_context_game(
            game_id=game_id,
            settings_hash=settings_hash,
            snapshots=snapshots,
        )
        residual_seconds = perf_counter() - t0

        t0 = perf_counter()
        chunnel = summarize_chunnel_residual_game(
            game_id=game_id,
            settings_hash=settings_hash,
            archive_data=archive_data,
            snapshots=snapshots,
        )
        chunnel_seconds = perf_counter() - t0

        t0 = perf_counter()
        horwasp = evaluate_horwasp_ballistic_context(archive_data, snapshots)
        horwasp["game_id"] = game_id
        horwasp["settings_hash"] = settings_hash
        horwasp_seconds = perf_counter() - t0
    except (OSError, ValueError, AssertionError, CorpusNormalizationError) as exc:
        return {
            "status": "failed",
            "position": position,
            "total": total,
            "game_id": game_id,
            "error": f"{type(exc).__name__}: {exc}",
            "timing_seconds": {"total": perf_counter() - started},
        }

    return {
        "status": "ok",
        "position": position,
        "total": total,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "prepared_cache_hit": prepared_cache_hit,
        "prepared_cache_bytes": prepared_cache_bytes,
        "baseline": baseline,
        "residual": residual,
        "chunnel": chunnel,
        "horwasp": horwasp,
        "timing_seconds": {
            "load": round(load_seconds, 3),
            "baseline": round(baseline_seconds, 3),
            "residual": round(residual_seconds, 3),
            "chunnel": round(chunnel_seconds, 3),
            "horwasp": round(horwasp_seconds, 3),
            "total": round(perf_counter() - started, 3),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the movement validation stack with a persistent prepared-game cache. "
            "Games can be processed in parallel with --jobs."
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
        "--rebuild-prepared-cache",
        action="store_true",
        help="Ignore persistent prepared-game cache files and rebuild them.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-pipeline.json"),
    )
    args = parser.parse_args()

    try:
        manifests = load_manifest_jsonl(args.manifest.read_text(encoding="utf-8"))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc))
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
            bool(args.rebuild_prepared_cache),
        )
        for position, manifest in enumerate(manifests, start=1)
    ]
    jobs = max(1, int(args.jobs))

    if jobs == 1:
        results = [_process_game(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(_process_game, tasks, chunksize=1))

    baseline_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    chunnel_rows: list[dict[str, Any]] = []
    horwasp_rows: list[dict[str, Any]] = []
    failed: list[int] = []
    timings: Counter[str] = Counter()
    prepared_cache_hits = 0
    prepared_cache_misses = 0
    prepared_cache_bytes = 0

    for result in results:
        if result["status"] != "ok":
            failed.append(int(result["game_id"]))
            print(json.dumps(result, sort_keys=True))
            continue
        baseline_rows.append(result["baseline"])
        residual_rows.append(result["residual"])
        chunnel_rows.append(result["chunnel"])
        horwasp_rows.append(result["horwasp"])
        if result.get("prepared_cache_hit"):
            prepared_cache_hits += 1
        else:
            prepared_cache_misses += 1
        prepared_cache_bytes += int(result.get("prepared_cache_bytes", 0))
        for key, value in result["timing_seconds"].items():
            timings[key] += float(value)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "position": result["position"],
                    "total": result["total"],
                    "game_id": result["game_id"],
                    "prepared_cache_hit": bool(result.get("prepared_cache_hit")),
                    "prepared_cache_bytes": int(result.get("prepared_cache_bytes", 0)),
                    "baseline_unresolved": result["baseline"]["unresolved"],
                    "external_residual": result["residual"]["residual_unresolved"],
                    "chunnel_residual": result["chunnel"]["residual_after_chunnel"],
                    "horwasp_residual_strong": result["horwasp"]["residual_after_strong"],
                    "timing_seconds": result["timing_seconds"],
                },
                sort_keys=True,
            )
        )

    baseline_stats = aggregate_movement_differential_games(
        baseline_rows, failed_game_ids=failed
    )
    residual_stats = aggregate_movement_residual_context_games(
        residual_rows, failed_game_ids=failed
    )
    chunnel_stats = aggregate_chunnel_residual_games(
        chunnel_rows, failed_game_ids=failed
    )
    horwasp_stats = _horwasp_stats(horwasp_rows, failed)

    output = {
        "schema": PIPELINE_SCHEMA,
        "jobs": jobs,
        "games_requested": total,
        "games_indexed": len(baseline_rows),
        "games_failed": len(set(failed)),
        "failed_game_ids": sorted(set(failed)),
        "prepared_cache": {
            "directory": str(args.prepared_cache_dir),
            "hits": prepared_cache_hits,
            "misses": prepared_cache_misses,
            "bytes": prepared_cache_bytes,
        },
        "timing_seconds_sum": {
            key: round(float(value), 3) for key, value in sorted(timings.items())
        },
        "baseline": baseline_stats,
        "residual": residual_stats,
        "chunnel": chunnel_stats,
        "horwasp": horwasp_stats,
        "games": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    bt = baseline_stats.get("totals", {})
    rt = residual_stats.get("totals", {})
    ct = chunnel_stats.get("totals", {})
    print("===== MOVEMENT PIPELINE SUMMARY =====")
    print(f"jobs:                         {jobs}")
    print(f"games_indexed:                {len(baseline_rows)}")
    print(f"games_failed:                 {len(set(failed))}")
    print(f"prepared_cache_hits:          {prepared_cache_hits}")
    print(f"prepared_cache_misses:        {prepared_cache_misses}")
    print(f"prepared_cache_bytes:         {prepared_cache_bytes}")
    print(f"move_most_candidates:         {bt.get('move_most_candidates', 0)}")
    print(f"baseline_explained:           {bt.get('geometrically_explained', 0)}")
    print(f"baseline_unresolved:          {bt.get('unresolved', 0)}")
    print(f"external_context_explained:   {rt.get('context_explained', 0)}")
    print(f"external_residual:            {rt.get('residual_unresolved', 0)}")
    print(f"chunnel_explained:            {ct.get('chunnel_explained', 0)}")
    print(f"post_chunnel_residual:        {ct.get('residual_after_chunnel', 0)}")
    print(f"horwasp_strong_explained:     {horwasp_stats.get('strong_explained', 0)}")
    print(f"post_horwasp_strong_residual: {horwasp_stats.get('residual_after_strong', 0)}")
    print("timing_seconds_sum:")
    for key, value in output["timing_seconds_sum"].items():
        print(f"  {key}: {value}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
