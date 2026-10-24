"""Conservative phase-qualified web-circle position classification.

Official: https://help.planets.nu/minefields and
https://help.planets.nu/minefields-examples

Web sweeping evaluates PRE-decay circles; web drain evaluates POST-decay.
This module deliberately does NOT implement the undocumented grid/cell
anchor or exact corner rules. The integer-radius core is a guaranteed
inside subset; the (radius + 2 LY) envelope conservatively protects a
1-LY edge allowance plus possible sub-LY square contact. The middle
region ABSTAINS. An envelope is not the actual Host acceptance radius.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt

from .minefield_placement_candidate import Point

EVIDENCE = "DOCUMENTED_PRE_POST_WEB_CIRCLE_ENVELOPE_TESTED_NOT_HOST_GEOMETRY_VERIFIED"
PRE_DECAY = "PRE_DECAY"
POST_DECAY = "POST_DECAY"
INSIDE_CONFIRMED = "INSIDE_CONFIRMED"
EDGE_ABSTAIN = "EDGE_ABSTAIN"
OUTSIDE_CONFIRMED = "OUTSIDE_CONFIRMED"
MAX_IDENTITY_COORDINATE = 1_000_000
MAX_UNITS = 22500


class WebCircleGeometryAbstain(ValueError):
    """Unknown phase, damaged field record or nonstandard coordinate semantics."""


@dataclass(frozen=True, slots=True)
class WebCircleEnvelopeResult:
    phase: str
    position: Point
    center: Point
    units: int
    radius_integer_ly: int
    distance_squared: int
    conservative_outer_guard_radius_ly: int
    classification: str
    evidence: str = EVIDENCE
    exact_web_cell_raster_verified: bool = False
    actual_host_selection_verified: bool = False
    host_diff_verified: bool = False


def _int(v: object, low: int, high: int) -> bool:
    return type(v) is int and low <= v <= high


def _point(p: object) -> bool:
    return (
        type(p) is Point
        and _int(p.x, -MAX_IDENTITY_COORDINATE, MAX_IDENTITY_COORDINATE)
        and _int(p.y, -MAX_IDENTITY_COORDINATE, MAX_IDENTITY_COORDINATE)
    )


def classify_web_circle_envelope(
    *,
    ship_position: Point,
    field_center: Point,
    field_mine_units: int,
    phase: str,
    exact_integer_positions_and_phase_confirmed: bool,
    standard_field_no_custom_geometry_confirmed: bool,
) -> WebCircleEnvelopeResult:
    """Fail-closed three-way quote only, never converts edge uncertainty to a hit."""
    if (
        exact_integer_positions_and_phase_confirmed is not True
        or standard_field_no_custom_geometry_confirmed is not True
    ):
        raise WebCircleGeometryAbstain("position, phase or standard settings not confirmed")
    if type(phase) is not str or phase not in (PRE_DECAY, POST_DECAY):
        raise WebCircleGeometryAbstain("web geometry requires explicit PRE or POST phase")
    if not _point(ship_position) or not _point(field_center):
        raise WebCircleGeometryAbstain("invalid typed bounded coordinates")
    if not _int(field_mine_units, 1, MAX_UNITS):
        raise WebCircleGeometryAbstain("nonstandard field quantity or radius")
    radius = isqrt(field_mine_units)
    distance2 = (ship_position.x-field_center.x)**2 + (ship_position.y-field_center.y)**2
    guard = radius + 2
    if distance2 <= radius**2:
        classification = INSIDE_CONFIRMED
    elif distance2 < guard**2:
        classification = EDGE_ABSTAIN
    else:
        classification = OUTSIDE_CONFIRMED
    return WebCircleEnvelopeResult(
        phase=phase,
        position=ship_position,
        center=field_center,
        units=field_mine_units,
        radius_integer_ly=radius,
        distance_squared=distance2,
        conservative_outer_guard_radius_ly=guard,
        classification=classification,
    )
