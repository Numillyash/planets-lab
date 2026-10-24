"""Conditional isolated hostile minefield *transition* audit, not a NuHost solver.

Official: https://help.planets.nu/minefields (Mine Destruction).
It says hostile overlapping normal fields detonate until at least one is
eliminated; it does NOT specify per-field integer unit-loss formula.
This module audits externally supplied typed before/after stage snapshots
for compatibility only; never simulates or attributes mine loss to Host.

Do NOT import a PHost formula as if it belonged to NuHost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .mine_overlap_candidate_graph import (
    MAX_FIELDS, MAX_ID, MAX_COORD_ABS, MAX_RADII,
    MineOverlapAbstain, classify_conditional_mine_overlaps,
)

EVIDENCE = "DOCUMENTED_ISOLATED_CONFLICT_TRANSITION_AUDIT_SYNTHETIC_NOT_HOST_DIFF_VERIFIED"
PRE_STAGE = "IMMEDIATELY_BEFORE_MINES_DESTROY_MINES"
POST_STAGE = "IMMEDIATELY_AFTER_MINES_DESTROY_MINES"


class MineConflictTransitionAbstain(ValueError):
    """Unusable evidence boundary, coupled conflict or ambiguous outcome."""


@dataclass(frozen=True, slots=True)
class IsolatedMineConflictTransitionAudit:
    field_ids: tuple[int, int]
    turn_number: int
    pre_units: tuple[int, int]
    post_units: tuple[int | None, int | None]
    observed_net_unit_change_by_field: tuple[int, int]
    outcome: str
    # COMPATIBLE_ONE_ELIMINATED, CONTRADICTED_BOTH_SURVIVE,
    # CONTRADICTED_SURVIVOR_GROWTH
    eliminated_field_id: int | None
    surviving_field_id: int | None
    unrelated_field_count: int
    pre_field_count: int
    post_field_count: int
    evidence: str = EVIDENCE
    actual_host_collision_causally_verified: bool = False
    host_unit_loss_formula_verified: bool = False
    host_order_execution_verified: bool = False
    host_diff_verified: bool = False
    state_mutated: bool = False


def _strict_int(x: object, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi


def _valid_point(value: object) -> bool:
    return (
        type(value) is Point
        and _strict_int(value.x, -MAX_COORD_ABS, MAX_COORD_ABS)
        and _strict_int(value.y, -MAX_COORD_ABS, MAX_COORD_ABS)
    )


def _validated_after_roster(
    roster: object, *, max_radius: int,
) -> dict[int, LocatedMinefield]:
    if not isinstance(roster, (tuple, list)) or len(roster) > MAX_FIELDS:
        raise MineConflictTransitionAbstain("complete bounded post-stage roster required")
    fields: dict[int, LocatedMinefield] = {}
    for f in roster:
        if type(f) is not LocatedMinefield or not (
            _strict_int(f.field_id, 1, MAX_ID)
            and _strict_int(f.owner_id, 1, MAX_ID)
            and _valid_point(f.center)
            and _strict_int(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise MineConflictTransitionAbstain("malformed post-stage field")
        if f.field_id in fields:
            raise MineConflictTransitionAbstain("duplicate post-stage ID")
        fields[f.field_id] = f
    return fields


def audit_isolated_hostile_mine_transition(
    *,
    before_fields: Sequence[LocatedMinefield],
    after_fields: Sequence[LocatedMinefield],
    mutual_safe_passage_by_normal_owner_pair: Mapping[tuple[int, int], bool],
    max_radius: int,
    turn_number: int,
    before_stage: str,
    after_stage: str,
    complete_before_roster_provenance_confirmed: bool,
    complete_after_roster_provenance_confirmed: bool,
    stage_adjacency_and_no_other_mutations_confirmed: bool,
    exact_unchanged_diplomacy_and_owner_confirmed: bool,
    ordinary_standard_no_protofield_or_custom_rules_confirmed: bool,
    independently_authenticated_host_stage_receipts_confirmed: bool,
) -> IsolatedMineConflictTransitionAudit:
    """Audit a single *candidate* component with one hostile normal pair.

    An asserted phase flag is caller-supplied metadata, not an authenticated
    receipt by this library. Positive result is only *compatible*, never a
    host-validated loss formula or DIFF_VERIFIED. Contradiction flags are
    conditional on the claimed source boundary and are NOT a NuHost bug proof.
    """
    if any(flag is not True for flag in (
        complete_before_roster_provenance_confirmed,
        complete_after_roster_provenance_confirmed,
        stage_adjacency_and_no_other_mutations_confirmed,
        exact_unchanged_diplomacy_and_owner_confirmed,
        ordinary_standard_no_protofield_or_custom_rules_confirmed,
        independently_authenticated_host_stage_receipts_confirmed,
    )):
        raise MineConflictTransitionAbstain("unwitnessed Host boundary or incomplete source")
    if type(before_stage) is not str or before_stage != PRE_STAGE:
        raise MineConflictTransitionAbstain("wrong before-stage identifier")
    if type(after_stage) is not str or after_stage != POST_STAGE:
        raise MineConflictTransitionAbstain("wrong after-stage identifier")
    if not _strict_int(turn_number, 1, MAX_ID):
        raise MineConflictTransitionAbstain("turn identifier not typed positive")
    if type(max_radius) is not int or max_radius not in MAX_RADII:
        raise MineConflictTransitionAbstain("nonstandard field radius")

    try:
        before_graph = classify_conditional_mine_overlaps(
            fields=before_fields,
            mutual_safe_passage_by_normal_owner_pair=mutual_safe_passage_by_normal_owner_pair,
            max_radius=max_radius,
            complete_phase_current_field_roster_confirmed=True,
            exact_centers_units_and_types_confirmed=True,
            exact_mutual_diplomacy_confirmed=True,
            ordinary_no_protofield_or_custom_interactions_confirmed=True,
            no_intervening_host_field_mutations_confirmed=True,
        )
    except MineOverlapAbstain as exc:
        raise MineConflictTransitionAbstain(f"before-stage graph ABSTAIN: {exc}") from exc

    if (
        before_graph.conflict_candidate_pairs != 1
        or before_graph.isolated_conflict_pair_components != 1
        or before_graph.coupled_multifield_components != 0
        or len(before_graph.components) != 1
    ):
        raise MineConflictTransitionAbstain(
            "exactly one independent hostile normal-field pair required"
        )
    ids = before_graph.components[0].field_ids
    if len(ids) != 2:
        raise MineConflictTransitionAbstain("unexpected candidate component size")
    # Before was already fully validated by the #296 public API above.
    before = {f.field_id: f for f in before_fields}
    after = _validated_after_roster(after_fields, max_radius=max_radius)
    if any(field_id not in before for field_id in after):
        raise MineConflictTransitionAbstain("unknown/new post-stage field ID")
    for fid in before:
        if fid in ids:
            continue
        if fid not in after or before[fid] != after[fid]:
            raise MineConflictTransitionAbstain(
                "unrelated field changed; stage isolation not trustworthy"
            )
    for fid in ids:
        if fid in after:
            prev, curr = before[fid], after[fid]
            if (
                curr.owner_id != prev.owner_id
                or curr.center != prev.center
                or curr.is_web != prev.is_web
            ):
                raise MineConflictTransitionAbstain(
                    "conflict field owner/type/center changed across boundary"
                )

    first, second = ids
    a = after.get(first)
    b = after.get(second)
    if a is None and b is None:
        raise MineConflictTransitionAbstain(
            "both disappeared: exact dual-elimination and ID-reuse chronology unresolved"
        )
    if a is not None and b is not None:
        status = "CONTRADICTED_BOTH_SURVIVE"
        killed = survivor = None
    else:
        killed = first if a is None else second
        survivor = second if a is None else first
        surviving = after[survivor]
        if surviving.mine_units > before[survivor].mine_units:
            status = "CONTRADICTED_SURVIVOR_GROWTH"
        elif surviving.mine_units == before[survivor].mine_units:
            raise MineConflictTransitionAbstain(
                "survivor has no observed loss; unknown countermining details"
            )
        else:
            status = "COMPATIBLE_ONE_ELIMINATED"

    observed = (
        before[first].mine_units - (a.mine_units if a is not None else 0),
        before[second].mine_units - (b.mine_units if b is not None else 0),
    )
    return IsolatedMineConflictTransitionAudit(
        field_ids=(first, second),
        turn_number=turn_number,
        pre_units=(before[first].mine_units, before[second].mine_units),
        post_units=(a.mine_units if a is not None else None,
                    b.mine_units if b is not None else None),
        observed_net_unit_change_by_field=observed,
        outcome=status,
        eliminated_field_id=killed,
        surviving_field_id=survivor,
        unrelated_field_count=len(before) - 2,
        pre_field_count=len(before),
        post_field_count=len(after),
    )
