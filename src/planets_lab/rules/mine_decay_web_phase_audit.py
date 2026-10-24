"""Isolated full-roster mine-decay transition audit with PRE/POST web envelopes.

Official: https://help.planets.nu/minefields and
https://help.planets.nu/minefields-examples .
A hypothetical exact isolated natural-decay stage is checked against a
separately supplied post-stage field roster, then ONE selected web
field/ship location is classified for PRE sweep versus POST drain.

Not a historical turn-pair validator, not independent authentication of
Host phase boundaries, and not a web sweep/drain simulator. Unknown half
rounding, phase context and near-edge square raster remain ABSTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .mine_natural_decay import (
    MineDecayAbstain, MinefieldState, simulate_isolated_natural_mine_decay,
)
from .web_circle_phase_envelope import (
    WebCircleGeometryAbstain, PRE_DECAY, POST_DECAY,
    EDGE_ABSTAIN, classify_web_circle_envelope,
)

EVIDENCE = "SYNTHETIC_CONDITIONAL_DECAY_PHASE_PAIR_AUDIT_NOT_HOST_VERIFIED"
SOURCE_SYNTHETIC = "SYNTHETIC_ISOLATED_PHASE_ASSERTION"
SOURCE_EXTERNAL = "EXTERNAL_PHASE_BOUNDARY_ASSERTION_NOT_AUTHENTICATED"
MAX_FIELDS = 128
MAX_ID = 2_147_483_647
MAX_COORD = 1_000_000


class MineDecayPhaseAuditAbstain(ValueError):
    """Incomplete or untrustworthy phase roster, geometry or rounding."""


@dataclass(frozen=True, slots=True)
class MineDecayFieldDelta:
    field_id: int
    units_before: int
    expected_units_after: int
    observed_units_after: int
    is_web: bool
    matches_conditional_formula: bool


@dataclass(frozen=True, slots=True)
class MineDecayWebPhaseAudit:
    source_kind: str
    selected_web_field_id: int
    field_deltas: tuple[MineDecayFieldDelta, ...]
    conditional_arithmetic_outcome: str  # EXACT_MATCH or SOURCE_MISMATCH
    total_units_before: int
    total_units_expected_after: int
    total_units_observed_after: int
    total_units_expected_natural_loss: int
    pre_web_geometry_class: str | None
    post_web_geometry_class: str | None
    geometry_outcome: str  # PHASE_PAIR_CLASSIFIED, EDGE_ABSTAIN, NOT_EVALUATED_MISMATCH, FIELD_EXHAUSTED
    evidence: str = EVIDENCE
    source_phase_authenticated: bool = False
    actual_host_decay_verified: bool = False
    actual_web_sweep_verified: bool = False
    actual_web_drain_verified: bool = False
    host_diff_verified: bool = False
    source_or_host_state_mutated: bool = False


def _i(x: object, low: int, high: int) -> bool:
    return type(x) is int and low <= x <= high


def _pt(p: object) -> bool:
    return type(p) is Point and _i(p.x, -MAX_COORD, MAX_COORD) and _i(
        p.y, -MAX_COORD, MAX_COORD,
    )


def _roster(source: object, *, max_radius: int, label: str) -> dict[int, LocatedMinefield]:
    if not isinstance(source, (list, tuple)) or len(source) > MAX_FIELDS:
        raise MineDecayPhaseAuditAbstain(f"complete bounded {label} roster required")
    result: dict[int, LocatedMinefield] = {}
    for f in source:
        if type(f) is not LocatedMinefield or not (
            _i(f.field_id, 1, MAX_ID)
            and _i(f.owner_id, 1, MAX_ID)
            and _pt(f.center)
            and _i(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise MineDecayPhaseAuditAbstain(f"invalid {label} field record")
        if f.field_id in result:
            raise MineDecayPhaseAuditAbstain(f"duplicate {label} field identity")
        result[f.field_id] = f
    return result


def audit_conditional_natural_decay_web_phase_pair(
    *,
    fields_before_decay: Sequence[LocatedMinefield],
    fields_after_decay: Sequence[LocatedMinefield],
    nebula_intersects_by_field_id: Mapping[int, bool],
    selected_web_field_id: int,
    ship_position: Point,
    max_radius: int,
    source_kind: str,
    complete_before_and_after_field_rosters_confirmed: bool,
    phase_adjacent_natural_decay_only_confirmed: bool,
    exact_static_centers_owners_types_confirmed: bool,
    exact_per_field_nebula_membership_confirmed: bool,
    ordinary_density_and_no_special_host_modifiers_confirmed: bool,
) -> MineDecayWebPhaseAudit:
    """Audits a caller-asserted phase pair WITHOUT independent source proof.

    Caller flags do not create authenticated Host phase witnesses.
    For real archival T-1 -> T observations, the required isolation premise
    must NOT be asserted: intervening Host phases and accepted orders unknown.
    An arithmetic mismatch never implies NuHost disagreement.
    """
    if any(flag is not True for flag in (
        complete_before_and_after_field_rosters_confirmed,
        phase_adjacent_natural_decay_only_confirmed,
        exact_static_centers_owners_types_confirmed,
        exact_per_field_nebula_membership_confirmed,
        ordinary_density_and_no_special_host_modifiers_confirmed,
    )):
        raise MineDecayPhaseAuditAbstain("full isolated phase and source provenance missing")
    if type(source_kind) is not str or source_kind not in (
        SOURCE_SYNTHETIC, SOURCE_EXTERNAL,
    ):
        raise MineDecayPhaseAuditAbstain("untyped/unsupported source kind (archive turn pair is not phase pair)")
    if type(max_radius) is not int or max_radius not in (100, 150):
        raise MineDecayPhaseAuditAbstain("standard mine radius not source-confirmed")
    if not _i(selected_web_field_id, 1, MAX_ID) or not _pt(ship_position):
        raise MineDecayPhaseAuditAbstain("invalid selected field or ship position")
    before = _roster(fields_before_decay, max_radius=max_radius, label="pre-decay")
    after = _roster(fields_after_decay, max_radius=max_radius, label="post-decay")
    if selected_web_field_id not in before or not before[selected_web_field_id].is_web:
        raise MineDecayPhaseAuditAbstain("selected pre-decay web field missing")
    if any(k not in before for k in after):
        raise MineDecayPhaseAuditAbstain("new/reused post-stage ID: non-isolated phase")
    for fid, a in after.items():
        b = before[fid]
        if (a.owner_id, a.center, a.is_web) != (b.owner_id, b.center, b.is_web):
            raise MineDecayPhaseAuditAbstain("field identity, owner, center or type changed")
    if not isinstance(nebula_intersects_by_field_id, Mapping):
        raise MineDecayPhaseAuditAbstain("complete per-field nebula context required")
    try:
        nebula = dict(nebula_intersects_by_field_id)
    except (TypeError, ValueError) as exc:
        raise MineDecayPhaseAuditAbstain("invalid nebula context") from exc
    if (
        set(nebula) != set(before)
        or any(not _i(k, 1, MAX_ID) or type(v) is not bool for k, v in nebula.items())
    ):
        raise MineDecayPhaseAuditAbstain("untyped/incomplete nebula field matrix")

    states = tuple(MinefieldState(fid, f.owner_id, f.mine_units, f.is_web)
                   for fid, f in sorted(before.items()))
    try:
        expected = simulate_isolated_natural_mine_decay(
            fields=states,
            nebula_intersects_by_field_id=nebula,
            max_radius=max_radius,
            turns=1,
            isolated_decay_only_confirmed=True,
            standard_density_confirmed=True,
        )
    except MineDecayAbstain as exc:
        raise MineDecayPhaseAuditAbstain(f"isolated decay arithmetic ABSTAIN: {exc}") from exc

    events = expected.turns[0].events
    deltas = tuple(MineDecayFieldDelta(
        field_id=e.field_id,
        units_before=e.units_before,
        expected_units_after=e.units_after,
        observed_units_after=after[e.field_id].mine_units if e.field_id in after else 0,
        is_web=e.is_web,
        matches_conditional_formula=(
            e.units_after == (after[e.field_id].mine_units if e.field_id in after else 0)
        ),
    ) for e in events)
    exact = all(d.matches_conditional_formula for d in deltas)
    expected_final = expected.final_units
    actual_final = sum(f.mine_units for f in after.values())
    if expected.initially_present_units != expected_final + expected.total_natural_units_lost:
        raise MineDecayPhaseAuditAbstain("conditional decay conservation violated")

    pre_geom = post_geom = None
    if not exact:
        geometry_outcome = "NOT_EVALUATED_MISMATCH"
    else:
        try:
            pre = classify_web_circle_envelope(
                ship_position=ship_position,
                field_center=before[selected_web_field_id].center,
                field_mine_units=before[selected_web_field_id].mine_units,
                phase=PRE_DECAY,
                exact_integer_positions_and_phase_confirmed=True,
                standard_field_no_custom_geometry_confirmed=True,
            )
            pre_geom = pre.classification
            if selected_web_field_id in after:
                post = classify_web_circle_envelope(
                    ship_position=ship_position,
                    field_center=after[selected_web_field_id].center,
                    field_mine_units=after[selected_web_field_id].mine_units,
                    phase=POST_DECAY,
                    exact_integer_positions_and_phase_confirmed=True,
                    standard_field_no_custom_geometry_confirmed=True,
                )
                post_geom = post.classification
        except WebCircleGeometryAbstain as exc:
            raise MineDecayPhaseAuditAbstain(f"web envelope ABSTAIN: {exc}") from exc
        if pre_geom == EDGE_ABSTAIN or post_geom == EDGE_ABSTAIN:
            geometry_outcome = "EDGE_ABSTAIN"
        elif selected_web_field_id not in after:
            geometry_outcome = "FIELD_EXHAUSTED"
        else:
            geometry_outcome = "PHASE_PAIR_CLASSIFIED"

    return MineDecayWebPhaseAudit(
        source_kind=source_kind,
        selected_web_field_id=selected_web_field_id,
        field_deltas=deltas,
        conditional_arithmetic_outcome="EXACT_MATCH" if exact else "SOURCE_MISMATCH",
        total_units_before=expected.initially_present_units,
        total_units_expected_after=expected_final,
        total_units_observed_after=actual_final,
        total_units_expected_natural_loss=expected.total_natural_units_lost,
        pre_web_geometry_class=pre_geom,
        post_web_geometry_class=post_geom,
        geometry_outcome=geometry_outcome,
    )
