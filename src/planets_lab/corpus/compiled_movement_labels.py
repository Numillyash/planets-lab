from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb

from .compiled_movement import COMPILED_MOVEMENT_SCHEMA
from .movement_chunnel_context import (
    _effective_sample,
    _pre_chunnel_position,
    _sample_from_transition,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from .movement_differential import _entity_map, _planet_tuples_by_turn
from .movement_horwasp_ballistic_context import (
    _classify_ballistic_formula,
    _historical_ballistic_hulls,
    _historical_mite_hulls,
)
from .movement_residual_context import _owner_record, _storm_consensus_by_turn
from .movement_residual_profile import extract_hull_catalog
from .movement_topology_diagnostics import extract_map_topology
from .prepared_cache import PreparedGameCache
from .reconstruction import group_perspective_records


COMPILED_MOVEMENT_CONTEXT_LABEL_SCHEMA = "planets-lab.compiled-movement-context-labels.v1"

# One row for every post-external-context residual movement transition. Raw
# private orders/state used to derive these classifications are intentionally
# absent: no friendly code, heading or Horwasp history is exported.
MOVEMENT_CONTEXT_LABEL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("game_id", "BIGINT"),
    ("before_archive_turn", "INTEGER"),
    ("after_archive_turn", "INTEGER"),
    ("ship_id", "INTEGER"),
    ("label_issue", "VARCHAR"),
    ("chunnel_category", "VARCHAR"),
    ("chunnel_match_count", "INTEGER"),
    ("chunnel_explained", "BOOLEAN"),
    ("post_chunnel_residual", "BOOLEAN"),
    ("horwasp_candidate_kind", "VARCHAR"),
    ("horwasp_category", "VARCHAR"),
    ("horwasp_strong_explained", "BOOLEAN"),
    ("horwasp_observed_context_explained", "BOOLEAN"),
    ("post_horwasp_strong_residual", "BOOLEAN"),
)


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def load_external_residual_keys(movement_parquet: Path) -> tuple[tuple[int, int, int], ...]:
    """Read exact residual transition keys from the compiled movement partition."""

    connection = duckdb.connect(":memory:")
    try:
        rows = connection.execute(
            """
            SELECT before_archive_turn, after_archive_turn, ship_id
            FROM read_parquet(?)
            WHERE post_external_residual = true
            ORDER BY before_archive_turn, after_archive_turn, ship_id
            """,
            [str(movement_parquet)],
        ).fetchall()
    finally:
        connection.close()
    return tuple((int(before), int(after), int(ship)) for before, after, ship in rows)


def compile_movement_context_label_rows(
    *,
    game_id: int,
    archive_data: bytes,
    prepared: PreparedGameCache,
    movement_parquet: Path,
) -> list[dict[str, Any]]:
    """Compile Chunnel and Horwasp labels for existing external residual rows.

    The compiled movement partition is authoritative for which transitions enter
    this layer. Raw/private state is consulted only during this local build to
    derive labels and is never copied into the resulting Parquet file.
    """

    residual_keys = load_external_residual_keys(movement_parquet)
    records = prepared.snapshots
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)

    transition_by_key = {
        (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
        for item in prepared.movement_geometry_readiness.results
    }

    abilities = extract_stable_chunnel_abilities(archive_data)
    events, _ = discover_observed_chunnel_events(records, abilities)
    events_by_turn: dict[int, list[Any]] = defaultdict(list)
    for event in events:
        events_by_turn[event.before_archive_turn].append(event)

    topology = extract_map_topology(archive_data)
    hull_catalog = extract_hull_catalog(archive_data)
    ballistic_hulls = _historical_ballistic_hulls(hull_catalog.hulls)
    mite_hulls = _historical_mite_hulls(hull_catalog.hulls)

    rows: list[dict[str, Any]] = []
    for before_turn, after_turn, ship_id in residual_keys:
        row: dict[str, Any] = {
            "game_id": game_id,
            "before_archive_turn": before_turn,
            "after_archive_turn": after_turn,
            "ship_id": ship_id,
            "label_issue": None,
            "chunnel_category": None,
            "chunnel_match_count": 0,
            "chunnel_explained": False,
            "post_chunnel_residual": True,
            "horwasp_candidate_kind": None,
            "horwasp_category": None,
            "horwasp_strong_explained": False,
            "horwasp_observed_context_explained": False,
            "post_horwasp_strong_residual": True,
        }

        transition = transition_by_key.get((before_turn, after_turn, ship_id))
        if transition is None:
            row["label_issue"] = "prepared_transition_missing"
            rows.append(row)
            continue

        sample = _sample_from_transition(transition, entities)
        if sample is None:
            row["label_issue"] = "movement_sample_unavailable"
            rows.append(row)
            continue

        group = ship_groups.get((before_turn, ship_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id <= 0 or owner is None:
            row["label_issue"] = "owner_private_context_unavailable"
            rows.append(row)
            continue

        planets = planets_by_turn.get(before_turn, ())
        effective = _effective_sample(sample)
        storms: Sequence[Any] = ()
        if after_turn in storm_conflict_turns or after_turn in storm_invalid_turns:
            pre_position = None
        else:
            storms = storms_by_turn.get(after_turn, ())
            pre_position, _ = _pre_chunnel_position(
                effective,
                planets=planets,
                storms=storms,
            )

        matches = [
            event
            for event in events_by_turn.get(before_turn, ())
            if event.destination == sample.observed_destination
            and event.pre_chunnel_position is not None
            and pre_position == event.pre_chunnel_position
        ]
        row["chunnel_match_count"] = len(matches)

        if len(matches) == 1:
            event = matches[0]
            if ship_id == event.initiator_ship_id:
                row["chunnel_category"] = "initiator"
            elif owner_id == event.owner_id:
                row["chunnel_category"] = "passenger_same_owner"
            else:
                row["chunnel_category"] = "passenger_other_owner"
            row["chunnel_explained"] = True
            row["post_chunnel_residual"] = False
            row["post_horwasp_strong_residual"] = False
            rows.append(row)
            continue

        if len(matches) > 1:
            row["chunnel_category"] = "ambiguous_matching_events"

        hull_id = int(sample.hull_id) if sample.hull_id is not None else None
        if hull_id is None:
            row["label_issue"] = "hull_id_unavailable"
            rows.append(row)
            continue

        if hull_id in mite_hulls:
            row["horwasp_candidate_kind"] = "mite"
            row["horwasp_category"] = "mite_residual"
            rows.append(row)
            continue

        if hull_id not in ballistic_hulls:
            rows.append(row)
            continue

        row["horwasp_candidate_kind"] = "ballistic"
        category, strong = _classify_ballistic_formula(
            raw=owner.raw,
            origin=(sample.x, sample.y),
            observed=sample.observed_destination,
            target=(sample.target_x, sample.target_y),
            warp=sample.warp,
            topology=topology,
        )
        if category is None:
            row["horwasp_category"] = "ballistic_unresolved"
        else:
            row["horwasp_category"] = category
            if strong:
                row["horwasp_strong_explained"] = True
                row["post_horwasp_strong_residual"] = False
            else:
                row["horwasp_observed_context_explained"] = True
        rows.append(row)

    if len(rows) != len(residual_keys):
        raise AssertionError("compiled movement context label row accounting is not closed")
    return rows


def movement_context_label_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    stats = {
        "external_residual_rows": len(rows),
        "label_issues": sum(row.get("label_issue") is not None for row in rows),
        "chunnel_explained": sum(row.get("chunnel_explained") is True for row in rows),
        "post_chunnel_residual": sum(row.get("post_chunnel_residual") is True for row in rows),
        "horwasp_ballistic_candidates": sum(
            row.get("horwasp_candidate_kind") == "ballistic" for row in rows
        ),
        "horwasp_mite_residual": sum(
            row.get("horwasp_candidate_kind") == "mite" for row in rows
        ),
        "horwasp_strong_explained": sum(
            row.get("horwasp_strong_explained") is True for row in rows
        ),
        "horwasp_observed_context_explained": sum(
            row.get("horwasp_observed_context_explained") is True for row in rows
        ),
        "post_horwasp_strong_residual": sum(
            row.get("post_horwasp_strong_residual") is True for row in rows
        ),
    }
    if stats["chunnel_explained"] + stats["post_chunnel_residual"] != stats["external_residual_rows"]:
        raise AssertionError("compiled Chunnel label accounting is not closed")
    if stats["horwasp_strong_explained"] + stats["post_horwasp_strong_residual"] != stats["post_chunnel_residual"]:
        raise AssertionError("compiled Horwasp strong label accounting is not closed")
    return stats


def _parquet_source(paths: Sequence[Path]) -> str:
    values = ", ".join(f"'{_sql_path(path)}'" for path in paths)
    return f"read_parquet([{values}], union_by_name=true)"


def refresh_movement_context_label_views(
    *,
    database_path: Path,
    label_parquet_paths: Sequence[Path],
) -> None:
    """Refresh context-label joins without copying Parquet into DuckDB."""

    connection = duckdb.connect(str(database_path))
    try:
        for view in (
            "movement_post_horwasp_strong_residual",
            "movement_post_chunnel_residual",
            "movement_labeled_residual",
            "movement_context_labels",
        ):
            connection.execute(f"DROP VIEW IF EXISTS {view}")

        if not label_parquet_paths:
            return

        connection.execute(
            "CREATE VIEW movement_context_labels AS SELECT * FROM "
            + _parquet_source(label_parquet_paths)
        )
        duplicates = connection.execute(
            """
            SELECT count(*)
            FROM (
                SELECT game_id, before_archive_turn, after_archive_turn, ship_id, count(*) AS n
                FROM movement_context_labels
                GROUP BY game_id, before_archive_turn, after_archive_turn, ship_id
                HAVING n <> 1
            )
            """
        ).fetchone()
        if duplicates and int(duplicates[0]) != 0:
            raise AssertionError("compiled movement context labels contain duplicate transition keys")

        connection.execute(
            """
            CREATE VIEW movement_labeled_residual AS
            SELECT
                m.*,
                l.label_issue,
                l.chunnel_category,
                l.chunnel_match_count,
                l.chunnel_explained,
                l.post_chunnel_residual,
                l.horwasp_candidate_kind,
                l.horwasp_category,
                l.horwasp_strong_explained,
                l.horwasp_observed_context_explained,
                l.post_horwasp_strong_residual
            FROM movement_residual AS m
            LEFT JOIN movement_context_labels AS l
              USING (game_id, before_archive_turn, after_archive_turn, ship_id)
            """
        )
        connection.execute(
            "CREATE VIEW movement_post_chunnel_residual AS "
            "SELECT * FROM movement_labeled_residual WHERE post_chunnel_residual = true"
        )
        connection.execute(
            "CREATE VIEW movement_post_horwasp_strong_residual AS "
            "SELECT * FROM movement_labeled_residual WHERE post_horwasp_strong_residual = true"
        )
    finally:
        connection.close()


def query_movement_context_label_catalog_stats(database_path: Path) -> dict[str, int]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT
                count(*) AS movement_residual_rows,
                count(l.ship_id) AS labeled_residual_rows,
                count(*) - count(l.ship_id) AS unlabeled_residual_rows,
                sum(CASE WHEN l.label_issue IS NOT NULL THEN 1 ELSE 0 END) AS label_issues,
                sum(CASE WHEN l.chunnel_explained = true THEN 1 ELSE 0 END) AS chunnel_explained,
                sum(CASE WHEN l.post_chunnel_residual = true THEN 1 ELSE 0 END) AS post_chunnel_residual,
                sum(CASE WHEN l.horwasp_candidate_kind = 'ballistic' THEN 1 ELSE 0 END) AS horwasp_ballistic_candidates,
                sum(CASE WHEN l.horwasp_candidate_kind = 'mite' THEN 1 ELSE 0 END) AS horwasp_mite_residual,
                sum(CASE WHEN l.horwasp_strong_explained = true THEN 1 ELSE 0 END) AS horwasp_strong_explained,
                sum(CASE WHEN l.horwasp_observed_context_explained = true THEN 1 ELSE 0 END) AS horwasp_observed_context_explained,
                sum(CASE WHEN l.post_horwasp_strong_residual = true THEN 1 ELSE 0 END) AS post_horwasp_strong_residual
            FROM movement_residual AS m
            LEFT JOIN movement_context_labels AS l
              USING (game_id, before_archive_turn, after_archive_turn, ship_id)
            """
        ).fetchone()
    finally:
        connection.close()
    names = (
        "movement_residual_rows",
        "labeled_residual_rows",
        "unlabeled_residual_rows",
        "label_issues",
        "chunnel_explained",
        "post_chunnel_residual",
        "horwasp_ballistic_candidates",
        "horwasp_mite_residual",
        "horwasp_strong_explained",
        "horwasp_observed_context_explained",
        "post_horwasp_strong_residual",
    )
    return {name: int(value or 0) for name, value in zip(names, row or ())}
