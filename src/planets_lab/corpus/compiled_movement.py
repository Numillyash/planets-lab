from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.validation.movement_geometry import MovementSample

from .movement_context import (
    GHOST,
    MOVE_MOST_CANDIDATE,
    MovementMissionConvention,
    _classify_owner_record,
    _raw_owner,
    _resolved_owner_from_current,
)
from .movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _resolved_value,
    _settings_warp_well_state_by_turn,
)
from .movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from .movement_topology_diagnostics import MapTopologyEvidence
from .prepared_cache import PREPARED_GAME_CACHE_SCHEMA, PreparedGameCache
from .readiness import READY
from .reconstruction import PerspectiveRecord, group_perspective_records


COMPILED_MOVEMENT_SCHEMA = "planets-lab.compiled-movement.v1"

# Keep this schema deliberately flat and SQL/ML friendly. Private text orders
# such as friendly codes are never exported; only derived intent classes are.
MOVEMENT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("game_id", "BIGINT"),
    ("settings_hash", "VARCHAR"),
    ("sphere", "BOOLEAN"),
    ("map_width", "INTEGER"),
    ("map_height", "INTEGER"),
    ("map_shape", "VARCHAR"),
    ("topology_stable", "BOOLEAN"),
    ("before_archive_turn", "INTEGER"),
    ("after_archive_turn", "INTEGER"),
    ("before_embedded_turn", "INTEGER"),
    ("after_embedded_turn", "INTEGER"),
    ("ship_id", "INTEGER"),
    ("readiness_status", "VARCHAR"),
    ("readiness_issues_json", "VARCHAR"),
    ("resolved_owner_id", "INTEGER"),
    ("owner_context_id", "INTEGER"),
    ("owner_context_issue", "VARCHAR"),
    ("intent_class", "VARCHAR"),
    ("hull_id", "INTEGER"),
    ("x_before", "INTEGER"),
    ("y_before", "INTEGER"),
    ("x_after", "INTEGER"),
    ("y_after", "INTEGER"),
    ("target_x", "INTEGER"),
    ("target_y", "INTEGER"),
    ("warp", "INTEGER"),
    ("observed_dx", "INTEGER"),
    ("observed_dy", "INTEGER"),
    ("observed_distance", "DOUBLE"),
    ("target_distance", "DOUBLE"),
    ("nominal_max_distance", "DOUBLE"),
    ("warp_wells_enabled", "BOOLEAN"),
    ("eligible_warp_well_planets", "INTEGER"),
    ("is_gravitonic_hull", "BOOLEAN"),
    ("baseline_category", "VARCHAR"),
    ("baseline_explained", "BOOLEAN"),
    ("post_baseline_residual", "BOOLEAN"),
    ("observed_tow_target_match", "BOOLEAN"),
    ("storm_context_status", "VARCHAR"),
    ("external_context_category", "VARCHAR"),
    ("external_context_explained", "BOOLEAN"),
    ("post_external_residual", "BOOLEAN"),
)

GAME_METADATA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("game_id", "BIGINT"),
    ("settings_hash", "VARCHAR"),
    ("archive_sha256", "VARCHAR"),
    ("prepared_schema", "VARCHAR"),
    ("compiled_schema", "VARCHAR"),
    ("sphere", "BOOLEAN"),
    ("map_width", "INTEGER"),
    ("map_height", "INTEGER"),
    ("map_shape", "VARCHAR"),
    ("topology_stable", "BOOLEAN"),
    ("snapshots", "INTEGER"),
    ("transition_rows", "BIGINT"),
    ("geometry_ready", "BIGINT"),
    ("move_most_candidates", "BIGINT"),
    ("baseline_explained", "BIGINT"),
    ("baseline_unresolved", "BIGINT"),
    ("external_context_explained", "BIGINT"),
    ("post_external_residual", "BIGINT"),
    ("parquet_bytes", "BIGINT"),
)


def _owner_intent_context(
    group: Sequence[PerspectiveRecord],
    *,
    convention: MovementMissionConvention,
) -> tuple[int | None, str | None, str | None]:
    owner_id, issue = _resolved_owner_from_current(group)
    if issue is not None or owner_id is None:
        return owner_id, None, issue or "before.ship.owner_context.unresolved_owner"
    if owner_id == 0:
        return 0, GHOST, None

    owner_records = tuple(
        record
        for record in group
        if record.is_current and record.player_id == owner_id
    )
    if len(owner_records) != 1:
        return owner_id, None, "before.ship.owner_context.owner_record_count"
    owner_record = owner_records[0]
    if _raw_owner(owner_record) != owner_id:
        return owner_id, None, "before.ship.owner_context.owner_record_mismatch"
    return owner_id, _classify_owner_record(owner_record, convention=convention), None


def _resolved_int(entity: Any, field: str) -> int | None:
    if entity is None:
        return None
    return _intish(_resolved_value(entity, field))


def _sample_from_values(
    *,
    turn: int,
    ship_id: int,
    x: int | None,
    y: int | None,
    target_x: int | None,
    target_y: int | None,
    warp: int | None,
    next_x: int | None,
    next_y: int | None,
    hull_id: int | None,
    gravitonic: bool = False,
) -> MovementSample | None:
    if None in (x, y, target_x, target_y, warp, next_x, next_y):
        return None
    return MovementSample(
        turn=turn,
        ship_id=ship_id,
        x=int(x),
        y=int(y),
        target_x=int(target_x),
        target_y=int(target_y),
        warp=int(warp),
        next_x=int(next_x),
        next_y=int(next_y),
        hull_id=hull_id,
        gravitonic=gravitonic,
    )


def compile_movement_rows(
    *,
    game_id: int,
    settings_hash: str,
    prepared: PreparedGameCache,
    topology: MapTopologyEvidence | None = None,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> list[dict[str, Any]]:
    """Compile one game's movement transition table from prepared corpus state.

    Rows cover every readiness transition, not only ordinary Move Most. Mechanics
    labels are populated only when their prerequisites are satisfied. This keeps
    readiness/facts separate from downstream explanatory labels and makes SQL
    filters reproduce the existing fail-closed validation accounting.

    Topology is preserved as factual context but deliberately does not alter the
    baseline labels in v1. Sphere-aware explanatory labels remain a separate
    validation/mechanics layer so this table continues to reproduce the current
    baseline and external-context stack exactly.
    """

    records = prepared.snapshots
    readiness = prepared.movement_geometry_readiness
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    warp_wells_by_turn, _ = _settings_warp_well_state_by_turn(records)
    eligible_planets_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", {})

    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)
    valid_pairs = {
        (item.before_archive_turn, item.after_archive_turn)
        for item in readiness.results
    }
    tow_targets, _ = _observed_tow_targets(
        entities=entities,
        ship_groups=ship_groups,
        valid_pairs=valid_pairs,
        convention=convention,
    )

    sphere = topology.sphere if topology is not None else None
    map_width = topology.mapwidth if topology is not None else None
    map_height = topology.mapheight if topology is not None else None
    map_shape = (
        str(topology.mapshape)
        if topology is not None and topology.mapshape is not None
        else None
    )
    topology_stable = topology.stable if topology is not None else None

    rows: list[dict[str, Any]] = []
    for transition in readiness.results:
        before = entities.get(("ship", transition.before_archive_turn, transition.entity_id))
        after = entities.get(("ship", transition.after_archive_turn, transition.entity_id))

        resolved_owner_id = _resolved_int(before, "ownerid")
        owner_context_id: int | None = None
        owner_context_issue: str | None = None
        intent_class: str | None = None
        if transition.status == READY:
            group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
            owner_context_id, intent_class, owner_context_issue = _owner_intent_context(
                group,
                convention=convention,
            )

        hull_id = _resolved_int(before, "hullid")
        x = _resolved_int(before, "x")
        y = _resolved_int(before, "y")
        next_x = _resolved_int(after, "x")
        next_y = _resolved_int(after, "y")
        target_x = _resolved_int(before, "targetx")
        target_y = _resolved_int(before, "targety")
        warp = _resolved_int(before, "warp")

        observed_dx = next_x - x if None not in (x, next_x) else None
        observed_dy = next_y - y if None not in (y, next_y) else None
        observed_distance = (
            hypot(float(observed_dx), float(observed_dy))
            if None not in (observed_dx, observed_dy)
            else None
        )
        target_distance = (
            hypot(float(target_x - x), float(target_y - y))
            if None not in (x, y, target_x, target_y)
            else None
        )
        nominal_max_distance = float(warp * warp) if warp is not None and warp >= 0 else None

        is_gravitonic = hull_id in GRAVITONIC_HULL_IDS if hull_id is not None else None
        baseline_category: str | None = None
        baseline_explained: bool | None = None
        post_baseline_residual: bool | None = None
        tow_match: bool | None = None
        storm_context_status: str | None = None
        external_category: str | None = None
        external_explained: bool | None = None
        post_external_residual: bool | None = None

        sample = None
        if transition.status == READY and intent_class == MOVE_MOST_CANDIDATE:
            sample = _sample_from_values(
                turn=transition.before_embedded_turn,
                ship_id=transition.entity_id,
                x=x,
                y=y,
                target_x=target_x,
                target_y=target_y,
                warp=warp,
                next_x=next_x,
                next_y=next_y,
                hull_id=hull_id,
            )

        if sample is not None:
            planets = planets_by_turn.get(transition.before_archive_turn, ())
            baseline_category = _movement_category(sample, planets=planets)
            baseline_explained = baseline_category in GEOMETRY_EXPLAINED_CATEGORIES
            post_baseline_residual = not baseline_explained

            if baseline_explained:
                external_explained = False
                post_external_residual = False
            else:
                key = (transition.before_archive_turn, transition.entity_id)
                tow_match = key in tow_targets
                if tow_match:
                    external_category = "observed_tow_target_match"
                else:
                    effective_sample = sample
                    if is_gravitonic:
                        effective_sample = _sample_from_values(
                            turn=transition.before_embedded_turn,
                            ship_id=transition.entity_id,
                            x=x,
                            y=y,
                            target_x=target_x,
                            target_y=target_y,
                            warp=warp,
                            next_x=next_x,
                            next_y=next_y,
                            hull_id=hull_id,
                            gravitonic=True,
                        ) or sample
                        grav_category = _movement_category(effective_sample, planets=planets)
                        if grav_category in GEOMETRY_EXPLAINED_CATEGORIES:
                            external_category = f"gravitonic_{grav_category}"

                    if external_category is None:
                        storm_turn = transition.after_archive_turn
                        if storm_turn in storm_conflict_turns:
                            storm_context_status = "storm_context_conflict"
                        elif storm_turn in storm_invalid_turns:
                            storm_context_status = "storm_context_invalid"
                        else:
                            storm_category, storm_context_status = _storm_expected_category(
                                effective_sample,
                                storms=storms_by_turn.get(storm_turn, ()),
                                planets=planets,
                            )
                            if storm_category is not None:
                                prefix = "gravitonic_" if is_gravitonic else ""
                                external_category = f"{prefix}{storm_category}"

                external_explained = external_category is not None
                post_external_residual = not external_explained

        rows.append(
            {
                "game_id": game_id,
                "settings_hash": settings_hash,
                "sphere": sphere,
                "map_width": map_width,
                "map_height": map_height,
                "map_shape": map_shape,
                "topology_stable": topology_stable,
                "before_archive_turn": transition.before_archive_turn,
                "after_archive_turn": transition.after_archive_turn,
                "before_embedded_turn": transition.before_embedded_turn,
                "after_embedded_turn": transition.after_embedded_turn,
                "ship_id": transition.entity_id,
                "readiness_status": transition.status,
                "readiness_issues_json": json.dumps(
                    list(transition.issues), separators=(",", ":"), sort_keys=True
                ),
                "resolved_owner_id": resolved_owner_id,
                "owner_context_id": owner_context_id,
                "owner_context_issue": owner_context_issue,
                "intent_class": intent_class,
                "hull_id": hull_id,
                "x_before": x,
                "y_before": y,
                "x_after": next_x,
                "y_after": next_y,
                "target_x": target_x,
                "target_y": target_y,
                "warp": warp,
                "observed_dx": observed_dx,
                "observed_dy": observed_dy,
                "observed_distance": observed_distance,
                "target_distance": target_distance,
                "nominal_max_distance": nominal_max_distance,
                "warp_wells_enabled": warp_wells_by_turn.get(transition.before_archive_turn),
                "eligible_warp_well_planets": len(
                    eligible_planets_by_turn.get(transition.before_archive_turn, frozenset())
                ),
                "is_gravitonic_hull": is_gravitonic,
                "baseline_category": baseline_category,
                "baseline_explained": baseline_explained,
                "post_baseline_residual": post_baseline_residual,
                "observed_tow_target_match": tow_match,
                "storm_context_status": storm_context_status,
                "external_context_category": external_category,
                "external_context_explained": external_explained,
                "post_external_residual": post_external_residual,
            }
        )

    return rows


def movement_row_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "transition_rows": len(rows),
        "geometry_ready": sum(row.get("readiness_status") == READY for row in rows),
        "move_most_candidates": sum(row.get("intent_class") == MOVE_MOST_CANDIDATE for row in rows),
        "baseline_explained": sum(row.get("baseline_explained") is True for row in rows),
        "baseline_unresolved": sum(row.get("post_baseline_residual") is True for row in rows),
        "external_context_explained": sum(
            row.get("external_context_explained") is True for row in rows
        ),
        "post_external_residual": sum(row.get("post_external_residual") is True for row in rows),
    }


def _create_table_sql(table: str, columns: Sequence[tuple[str, str]]) -> str:
    fields = ",\n    ".join(f'"{name}" {kind}' for name, kind in columns)
    return f'CREATE TABLE "{table}" (\n    {fields}\n)'


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def write_rows_parquet(
    *,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[tuple[str, str]],
    path: Path,
    table_name: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    names = tuple(name for name, _ in columns)
    placeholders = ",".join("?" for _ in names)
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(_create_table_sql(table_name, columns))
        if rows:
            connection.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                [tuple(row.get(name) for name in names) for row in rows],
            )
        connection.execute(
            f"COPY \"{table_name}\" TO '{_sql_path(temporary)}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        temporary.replace(path)
    finally:
        connection.close()
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_movement_parquet(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    write_rows_parquet(
        rows=rows,
        columns=MOVEMENT_COLUMNS,
        path=path,
        table_name="movement_transitions",
    )


def write_games_parquet(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    write_rows_parquet(
        rows=rows,
        columns=GAME_METADATA_COLUMNS,
        path=path,
        table_name="games",
    )


def create_compiled_catalog(
    *,
    database_path: Path,
    games_parquet: Path,
    movement_glob: Path,
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("DROP VIEW IF EXISTS movement_residual")
        connection.execute("DROP VIEW IF EXISTS move_most")
        connection.execute("DROP VIEW IF EXISTS movement_transitions")
        connection.execute("DROP VIEW IF EXISTS games")
        connection.execute(
            f"CREATE VIEW games AS SELECT * FROM read_parquet('{_sql_path(games_parquet)}')"
        )
        connection.execute(
            "CREATE VIEW movement_transitions AS "
            f"SELECT * FROM read_parquet('{_sql_path(movement_glob)}', union_by_name=true)"
        )
        connection.execute(
            "CREATE VIEW move_most AS "
            "SELECT * FROM movement_transitions "
            "WHERE readiness_status = 'ready' AND intent_class = 'move_most_candidate'"
        )
        connection.execute(
            "CREATE VIEW movement_residual AS "
            "SELECT * FROM move_most WHERE post_external_residual = true"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS compiled_metadata (key VARCHAR PRIMARY KEY, value VARCHAR)"
        )
        connection.execute("DELETE FROM compiled_metadata")
        connection.executemany(
            "INSERT INTO compiled_metadata VALUES (?, ?)",
            [
                ("compiled_schema", COMPILED_MOVEMENT_SCHEMA),
                ("prepared_schema", PREPARED_GAME_CACHE_SCHEMA),
            ],
        )
    finally:
        connection.close()


def query_compiled_stats(database_path: Path) -> dict[str, int]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT
                count(*) AS transition_rows,
                sum(CASE WHEN readiness_status = 'ready' THEN 1 ELSE 0 END) AS geometry_ready,
                sum(CASE WHEN readiness_status = 'ready' AND intent_class = 'move_most_candidate' THEN 1 ELSE 0 END) AS move_most_candidates,
                sum(CASE WHEN baseline_explained = true THEN 1 ELSE 0 END) AS baseline_explained,
                sum(CASE WHEN post_baseline_residual = true THEN 1 ELSE 0 END) AS baseline_unresolved,
                sum(CASE WHEN external_context_explained = true THEN 1 ELSE 0 END) AS external_context_explained,
                sum(CASE WHEN post_external_residual = true THEN 1 ELSE 0 END) AS post_external_residual
            FROM movement_transitions
            """
        ).fetchone()
    finally:
        connection.close()
    names = (
        "transition_rows",
        "geometry_ready",
        "move_most_candidates",
        "baseline_explained",
        "baseline_unresolved",
        "external_context_explained",
        "post_external_residual",
    )
    return {name: int(value or 0) for name, value in zip(names, row or ())}
