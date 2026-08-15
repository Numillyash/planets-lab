from __future__ import annotations

import json

from planets_lab.corpus.compiled_movement import COMPILED_MOVEMENT_SCHEMA
from planets_lab.corpus.compiled_movement_corpus_cli import (
    _collect_catalog_metadata,
    _stats_from_results,
)
from planets_lab.corpus.prepared_cache import PREPARED_GAME_CACHE_SCHEMA


def _meta(game_id: int, *, transition_rows: int, move_most: int) -> dict[str, object]:
    baseline_unresolved = move_most // 4
    baseline_explained = move_most - baseline_unresolved
    post_external = baseline_unresolved // 2
    external_explained = baseline_unresolved - post_external
    return {
        "game_id": game_id,
        "settings_hash": f"settings-{game_id}",
        "archive_sha256": f"sha-{game_id}",
        "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
        "compiled_schema": COMPILED_MOVEMENT_SCHEMA,
        "sphere": game_id == 591478,
        "map_width": 2150 if game_id == 591478 else None,
        "map_height": 2150 if game_id == 591478 else None,
        "map_shape": "1" if game_id == 591478 else None,
        "topology_stable": True,
        "snapshots": 10,
        "transition_rows": transition_rows,
        "geometry_ready": transition_rows - 1,
        "move_most_candidates": move_most,
        "baseline_explained": baseline_explained,
        "baseline_unresolved": baseline_unresolved,
        "external_context_explained": external_explained,
        "post_external_residual": post_external,
        "parquet_bytes": 1234 + game_id,
    }


def test_partial_rebuild_catalog_metadata_preserves_other_partitions(tmp_path) -> None:
    output_dir = tmp_path / "compiled" / "v1"
    for game_id in (591478, 680910):
        partition = output_dir / "mechanics" / "movement_transitions" / f"game_id={game_id}"
        partition.mkdir(parents=True)
        (partition / "part-000.parquet").write_bytes(b"parquet-placeholder")
        (partition / "_meta.json").write_text(
            json.dumps(_meta(game_id, transition_rows=100 + game_id % 10, move_most=80)),
            encoding="utf-8",
        )

    rows = _collect_catalog_metadata(output_dir)

    assert [row["game_id"] for row in rows] == [591478, 680910]


def test_run_stats_are_scoped_to_current_results() -> None:
    current = _meta(591478, transition_rows=64045, move_most=55352)
    stats = _stats_from_results([current])

    assert stats["transition_rows"] == 64045
    assert stats["move_most_candidates"] == 55352
