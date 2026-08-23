from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any

from planets_lab.rules.ion_storm import integer_drag_delta
from planets_lab.validation.movement_geometry import MovementSample

from .movement_differential import _entity_map, _planet_tuples_by_turn, _warp_well_destination
from .movement_residual_context import (
    StormRecord,
    _navigation_endpoint,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from .movement_sphere_context import apply_effective_sphere_context_rows
from .prepared_cache import PreparedGameCache


# Retain the historical symbol name because compiled cache metadata already uses
# it. v2 covers the ordered post-compile L1 external-context pass implemented in
# this module: authoritative storm mode first, then scoped effective sphere
# geometry only for rows that remain unresolved.
MOVEMENT_STORM_CONTEXT_SCHEMA = "planets-lab.compiled-movement-storm-context.v2"


def _classic_constant_storm_offset(
    storms: Sequence[StormRecord],
    *,
    x: int,
    y: int,
) -> tuple[tuple[int, int] | None, str]:
    """Resolve documented classic ion-storm drag with constant in-circle voltage.

    Classic ion storms have one effective circular area whose published voltage
    applies throughout the circle. This deliberately changes only the voltage
    coverage model; drag distance/vector and multi-storm sequential displacement
    reuse the already validated implementation primitives.
    """

    effective_x = x
    effective_y = y
    total_dx = 0
    total_dy = 0
    affected = False

    roots = sorted(
        (storm for storm in storms if storm.parent_id == 0),
        key=lambda item: item.id,
    )
    for storm in roots:
        if storm.radius <= 0:
            continue
        if hypot(effective_x - storm.x, effective_y - storm.y) >= storm.radius:
            continue
        if storm.voltage < 150.0:
            continue

        affected = True
        if storm.voltage >= 400.0:
            return None, "extreme_voltage"

        dx, dy = integer_drag_delta(storm.warp, storm.heading)
        effective_x += dx
        effective_y += dy
        total_dx += dx
        total_dy += dy

    if not affected:
        return (0, 0), "not_affected"
    return (total_dx, total_dy), "resolved_drag"


def storm_expected_category_for_mode(
    sample: MovementSample,
    *,
    storms: Sequence[StormRecord],
    planets: Sequence[tuple[int, int, int]],
    nuionstorms: bool | None,
) -> tuple[str | None, str]:
    """Classify ion-storm displacement using the game's authoritative storm mode.

    ``nuionstorms=True`` is the cloudy model already implemented by
    ``_storm_expected_category``. ``False`` is the classic constant-voltage
    model. Unknown mode is fail-closed so compiled corpus builds never silently
    reinterpret storm geometry.
    """

    if nuionstorms is True:
        return _storm_expected_category(sample, storms=storms, planets=planets)
    if nuionstorms is None:
        return None, "storm_mode_unknown"

    offset, status = _classic_constant_storm_offset(storms, x=sample.x, y=sample.y)
    if offset is None or offset == (0, 0):
        return None, status

    base = _navigation_endpoint(sample)
    shifted = (base[0] + offset[0], base[1] + offset[1])
    if sample.observed_destination == shifted:
        return "ion_storm_drag", status

    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=shifted,
        planets=planets,
    )
    if ambiguous:
        return None, "warp_well_ambiguous"
    if well is not None and sample.observed_destination == well:
        return "ion_storm_drag_warp_well_match", status
    return None, status


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


def apply_mode_aware_storm_context_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prepared: PreparedGameCache,
    nuionstorms: bool | None,
) -> list[dict[str, Any]]:
    """Apply ordered L1 post-compile external context without stealing labels.

    The existing compiled movement pass remains authoritative for baseline,
    observed tow, gravitonic movement, and already-explained storm rows. This
    function first revisits only post-external residual rows with authoritative
    ion-storm mode, then applies evidence-scoped effective sphere geometry to
    whatever remains unresolved. Existing explanatory categories are preserved.
    """

    records = prepared.snapshots
    entities = _entity_map(records)
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, conflict_turns, invalid_turns = _storm_consensus_by_turn(records)

    result: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if row.get("post_external_residual") is not True:
            result.append(row)
            continue

        sample = _row_sample(row)
        if sample is None:
            result.append(row)
            continue

        after_turn = int(row["after_archive_turn"])
        if after_turn in conflict_turns:
            row["storm_context_status"] = "storm_context_conflict"
            result.append(row)
            continue
        if after_turn in invalid_turns:
            row["storm_context_status"] = "storm_context_invalid"
            result.append(row)
            continue

        planets = planets_by_turn.get(int(row["before_archive_turn"]), ())
        category, status = storm_expected_category_for_mode(
            sample,
            storms=storms_by_turn.get(after_turn, ()),
            planets=planets,
            nuionstorms=nuionstorms,
        )
        row["storm_context_status"] = status
        if category is not None:
            prefix = "gravitonic_" if row.get("is_gravitonic_hull") is True else ""
            row["external_context_category"] = f"{prefix}{category}"
            row["external_context_explained"] = True
            row["post_external_residual"] = False
        result.append(row)

    if nuionstorms is None:
        return result
    return apply_effective_sphere_context_rows(result, prepared=prepared)
