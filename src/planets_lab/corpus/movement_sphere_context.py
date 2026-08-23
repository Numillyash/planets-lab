from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from planets_lab.validation.movement_geometry import MovementSample

from .movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _movement_category,
    _planet_tuples_by_turn,
)
from .movement_topology_diagnostics import (
    MapTopologyEvidence,
    _wrapped_planets_near,
    sphere_adjusted_sample,
)
from .prepared_cache import PreparedGameCache


MOVEMENT_EFFECTIVE_TOPOLOGY_SCHEMA = "planets-lab.compiled-movement-effective-topology.v1"

# Independent historical seam evidence establishes this one effective toroidal
# period. The raw loadinfo/archive topology remains 2150x2150 and is preserved
# unchanged in compiled factual columns. Never generalize this to mapwidth+20.
_SCOPED_EFFECTIVE_WRAP_PERIODS: Mapping[int, tuple[int, int]] = {
    591478: (2170, 2170),
}
_SCOPED_RAW_WRAP_PERIODS: Mapping[int, tuple[int, int]] = {
    591478: (2150, 2150),
}


def effective_sphere_topology(
    *,
    game_id: int | None,
    topology: MapTopologyEvidence,
) -> MapTopologyEvidence:
    """Return an evidence-scoped effective topology without mutating raw facts.

    The override is intentionally fail-closed: exact game id, sphere flag,
    stable raw topology and the independently audited raw dimensions must all
    match before the effective period is exposed.
    """

    if game_id is None:
        return topology
    effective = _SCOPED_EFFECTIVE_WRAP_PERIODS.get(int(game_id))
    expected_raw = _SCOPED_RAW_WRAP_PERIODS.get(int(game_id))
    if effective is None or expected_raw is None:
        return topology
    if topology.sphere is not True or topology.stable is not True:
        return topology
    if (topology.mapwidth, topology.mapheight) != expected_raw:
        return topology
    return replace(
        topology,
        mapwidth=effective[0],
        mapheight=effective[1],
    )


def _row_sample(row: Mapping[str, Any]) -> MovementSample | None:
    required = (
        "ship_id",
        "before_embedded_turn",
        "x_before",
        "y_before",
        "target_x",
        "target_y",
        "warp",
        "x_after",
        "y_after",
    )
    if any(row.get(key) is None for key in required):
        return None
    return MovementSample(
        turn=int(row["before_embedded_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
        gravitonic=row.get("is_gravitonic_hull") is True,
    )


def _compiled_topology_context(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[int, MapTopologyEvidence] | None:
    if not rows:
        return None

    first = rows[0]
    game_id = first.get("game_id")
    if isinstance(game_id, bool) or not isinstance(game_id, int):
        return None

    facts = (
        first.get("sphere"),
        first.get("map_width"),
        first.get("map_height"),
        first.get("map_shape"),
        first.get("topology_stable"),
    )
    for row in rows[1:]:
        if row.get("game_id") != game_id:
            raise ValueError(
                f"compiled movement rows mix game ids: expected {game_id}, "
                f"got {row.get('game_id')!r}"
            )
        row_facts = (
            row.get("sphere"),
            row.get("map_width"),
            row.get("map_height"),
            row.get("map_shape"),
            row.get("topology_stable"),
        )
        if row_facts != facts:
            raise ValueError(f"compiled movement topology facts are inconsistent for game {game_id}")

    sphere, width, height, shape, stable = facts
    topology = MapTopologyEvidence(
        sphere=sphere if isinstance(sphere, bool) else None,
        mapwidth=int(width) if isinstance(width, int) and not isinstance(width, bool) else None,
        mapheight=int(height) if isinstance(height, int) and not isinstance(height, bool) else None,
        mapshape=shape if isinstance(shape, (int, str)) and not isinstance(shape, bool) else None,
        first_member="compiled-row-facts",
        last_member="compiled-row-facts",
        stable=stable is True,
        first_candidates={},
        last_candidates={},
    )
    return game_id, topology


def effective_sphere_category(
    sample: MovementSample,
    *,
    game_id: int,
    topology: MapTopologyEvidence,
    planets: Sequence[tuple[int, int, int]],
) -> str | None:
    """Return an explanatory category only when scoped sphere geometry closes it."""

    effective = effective_sphere_topology(game_id=game_id, topology=topology)
    if effective is topology:
        return None
    if effective.mapwidth is None or effective.mapheight is None:
        return None

    adjusted = sphere_adjusted_sample(
        sample,
        width=int(effective.mapwidth),
        height=int(effective.mapheight),
    )
    wrapped_planets = _wrapped_planets_near(
        (sample.x, sample.y),
        planets,
        width=int(effective.mapwidth),
        height=int(effective.mapheight),
    )
    category = _movement_category(adjusted, planets=wrapped_planets)
    if category not in GEOMETRY_EXPLAINED_CATEGORIES:
        return None

    prefix = "effective_sphere_gravitonic_" if sample.gravitonic else "effective_sphere_"
    return f"{prefix}{category}"


def apply_effective_sphere_context_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prepared: PreparedGameCache,
    game_id: int | None = None,
    topology: MapTopologyEvidence | None = None,
) -> list[dict[str, Any]]:
    """Close only rows still unresolved after existing L1 external contexts.

    Baseline, tow, gravitonic and ion-storm classifications remain authoritative.
    This pass is monotonic and revisits only ``post_external_residual`` rows, so
    existing explanatory categories are never stolen or renamed. When explicit
    topology is omitted, the pass reconstructs only the already-exported raw
    topology facts from this single-game compiled row set.
    """

    if game_id is None or topology is None:
        context = _compiled_topology_context(rows)
        if context is None:
            return [dict(row) for row in rows]
        game_id, topology = context

    effective = effective_sphere_topology(game_id=game_id, topology=topology)
    if effective is topology:
        return [dict(row) for row in rows]

    entities = _entity_map(prepared.snapshots)
    planets_by_turn = _planet_tuples_by_turn(entities)

    result: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if row.get("post_external_residual") is not True:
            result.append(row)
            continue
        if row.get("game_id") not in (None, game_id):
            raise ValueError(
                f"compiled movement row game mismatch: expected {game_id}, "
                f"got {row.get('game_id')!r}"
            )

        sample = _row_sample(row)
        if sample is None:
            result.append(row)
            continue

        planets = planets_by_turn.get(int(row["before_archive_turn"]), ())
        category = effective_sphere_category(
            sample,
            game_id=game_id,
            topology=topology,
            planets=planets,
        )
        if category is not None:
            row["external_context_category"] = category
            row["external_context_explained"] = True
            row["post_external_residual"] = False
        result.append(row)

    return result
