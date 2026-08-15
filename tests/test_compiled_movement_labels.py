from __future__ import annotations

import duckdb

from planets_lab.corpus.columnar_io import write_rows_parquet_arrow
from planets_lab.corpus.compiled_movement_labels import (
    MOVEMENT_CONTEXT_LABEL_COLUMNS,
    movement_context_label_stats,
    query_movement_context_label_catalog_stats,
    refresh_movement_context_label_views,
)


def _label_row(
    ship_id: int,
    *,
    chunnel: bool = False,
    strong: bool = False,
    observed: bool = False,
) -> dict[str, object]:
    return {
        "game_id": 7,
        "before_archive_turn": 10,
        "after_archive_turn": 11,
        "ship_id": ship_id,
        "label_issue": None,
        "chunnel_category": "passenger_same_owner" if chunnel else None,
        "chunnel_match_count": 1 if chunnel else 0,
        "chunnel_explained": chunnel,
        "post_chunnel_residual": not chunnel,
        "horwasp_candidate_kind": "ballistic" if strong or observed else None,
        "horwasp_category": (
            "ballistic_launch_normal"
            if strong
            else "ballistic_accelerator_transition_observed"
            if observed
            else None
        ),
        "horwasp_strong_explained": strong,
        "horwasp_observed_context_explained": observed,
        "post_horwasp_strong_residual": (not chunnel) and (not strong),
    }


def test_label_schema_omits_private_source_fields() -> None:
    names = {name for name, _ in MOVEMENT_CONTEXT_LABEL_COLUMNS}
    assert "friendlycode" not in names
    assert "friendly_code" not in names
    assert "heading" not in names
    assert "history" not in names


def test_label_stats_preserve_strong_closure_without_counting_observed_only() -> None:
    rows = [
        _label_row(1, chunnel=True),
        _label_row(2, strong=True),
        _label_row(3, observed=True),
        _label_row(4),
    ]
    stats = movement_context_label_stats(rows)
    assert stats["external_residual_rows"] == 4
    assert stats["chunnel_explained"] == 1
    assert stats["post_chunnel_residual"] == 3
    assert stats["horwasp_strong_explained"] == 1
    assert stats["horwasp_observed_context_explained"] == 1
    assert stats["post_horwasp_strong_residual"] == 2


def test_label_catalog_views_report_partial_coverage_fail_closed(tmp_path) -> None:
    database = tmp_path / "corpus.duckdb"
    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            """
            CREATE VIEW movement_residual AS
            SELECT * FROM (
                VALUES
                    (7::BIGINT, 10::INTEGER, 11::INTEGER, 1::INTEGER),
                    (7::BIGINT, 10::INTEGER, 11::INTEGER, 2::INTEGER),
                    (7::BIGINT, 10::INTEGER, 11::INTEGER, 3::INTEGER)
            ) AS t(game_id, before_archive_turn, after_archive_turn, ship_id)
            """
        )
    finally:
        connection.close()

    label_path = tmp_path / "labels" / "game_id=7" / "part-000.parquet"
    write_rows_parquet_arrow(
        rows=[_label_row(1, chunnel=True), _label_row(2, observed=True)],
        columns=MOVEMENT_CONTEXT_LABEL_COLUMNS,
        path=label_path,
    )
    refresh_movement_context_label_views(
        database_path=database,
        label_parquet_paths=[label_path],
    )

    stats = query_movement_context_label_catalog_stats(database)
    assert stats["movement_residual_rows"] == 3
    assert stats["labeled_residual_rows"] == 2
    assert stats["unlabeled_residual_rows"] == 1
    assert stats["chunnel_explained"] == 1
    assert stats["post_chunnel_residual"] == 1
    assert stats["horwasp_observed_context_explained"] == 1
    assert stats["post_horwasp_strong_residual"] == 1

    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute(
            "SELECT count(*) FROM movement_post_chunnel_residual"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM movement_post_horwasp_strong_residual"
        ).fetchone() == (1,)
    finally:
        connection.close()


def test_compiled_label_cli_imports() -> None:
    from planets_lab.corpus.compiled_movement_labels_corpus_cli import main

    assert callable(main)
