"""Pure minefield potential-conflict graph, NOT Host mine destruction.

Source: https://help.planets.nu/minefields (Mine Destruction).
- Normal vs web, and web vs web, do NOT mutually destroy.
- Ordinary normal/normal owners with mutual Safe Passage can overlap.
- Other overlapping foreign normal/normal fields are candidates for
  Host mine-destroys-mine resolution in ascending field ID order.
This classifies geometric candidates ONLY; it does not determine exact
detonations, survivor identity, removed units, Host orders or chronology.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point

EVIDENCE = "DOCUMENTED_MINE_OVERLAP_CANDIDATES_TESTED_NOT_HOST_DIFF_VERIFIED"
MAX_FIELDS = 128   # bounded candidate graph, NOT Host's field limit
MAX_ID = 2_147_483_647
MAX_COORD_ABS = 1_000_000
MAX_RADII = frozenset((100, 150))


class MineOverlapAbstain(ValueError):
    """Source completeness, tangency, custom rules or chronology unresolved."""


@dataclass(frozen=True, slots=True)
class MinefieldPairAssessment:
    first_field_id: int
    second_field_id: int
    first_owner_id: int
    second_owner_id: int
    distance_squared: int
    combined_integer_radius: int
    classification: str
    # DISJOINT, WEB_NONDESTRUCTIVE, SAME_OWNER_NONDESTRUCTIVE,
    # MUTUAL_SAFE_PASSAGE_NONDESTRUCTIVE, HOSTILE_NORMAL_OVERLAP_CANDIDATE
    candidate_host_conflict: bool
    mine_units_destroyed: None = None
    field_destroyed: bool = False


@dataclass(frozen=True, slots=True)
class MineConflictComponent:
    field_ids: tuple[int, ...]
    candidate_edges: tuple[tuple[int, int], ...]
    category: str  # ISOLATED_PAIR or COUPLED_MULTIFIELD
    host_resolution_verified: bool = False


@dataclass(frozen=True, slots=True)
class MineOverlapGraph:
    assessments: tuple[MinefieldPairAssessment, ...]
    components: tuple[MineConflictComponent, ...]
    total_fields: int
    total_pairs_examined: int
    conflict_candidate_pairs: int
    isolated_conflict_pair_components: int
    coupled_multifield_components: int
    evidence: str = EVIDENCE
    host_mine_units_destroyed: None = None
    actual_field_roster_mutated: bool = False
    host_phase_order_verified: bool = False
    host_conflicts_resolved: bool = False
    host_diff_verified: bool = False


def _integer(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


def _point(p: object) -> bool:
    return type(p) is Point and _integer(p.x, -MAX_COORD_ABS, MAX_COORD_ABS) and _integer(
        p.y, -MAX_COORD_ABS, MAX_COORD_ABS
    )


def _complete_fields(values: object, *, max_radius: int) -> tuple[LocatedMinefield, ...]:
    if not isinstance(values, (list, tuple)) or len(values) > MAX_FIELDS:
        raise MineOverlapAbstain("complete bounded field roster required")
    result: list[LocatedMinefield] = []
    ids: set[int] = set()
    for f in values:
        if type(f) is not LocatedMinefield or not (
            _integer(f.field_id, 1, MAX_ID) and _integer(f.owner_id, 1, MAX_ID)
            and _point(f.center)
            and _integer(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise MineOverlapAbstain("untyped/nonstandard field source")
        if f.field_id in ids:
            raise MineOverlapAbstain("duplicate minefield ID")
        ids.add(f.field_id)
        result.append(f)
    return tuple(sorted(result, key=lambda f: f.field_id))


def _safe_passage_map(
    values: object, *, normal_owners: set[int],
) -> dict[tuple[int, int], bool]:
    if not isinstance(values, Mapping):
        raise MineOverlapAbstain("complete mutual-safe-passage map required")
    try:
        m = dict(values)
    except (TypeError, ValueError) as exc:
        raise MineOverlapAbstain("malformed diplomacy map") from exc
    owners = sorted(normal_owners)
    expected = {
        (first, second)
        for i, first in enumerate(owners)
        for second in owners[i + 1:]
    }
    if set(m) != expected or any(
        type(key) is not tuple or len(key) != 2
        or not all(_integer(part, 1, MAX_ID) for part in key)
        or type(value) is not bool
        for key, value in m.items()
    ):
        raise MineOverlapAbstain("mutual Safe Passage must be exact for every normal-owner pair")
    return m


def _components(
    hostile_edges: list[tuple[int, int]],
) -> tuple[MineConflictComponent, ...]:
    adjacency: dict[int, set[int]] = {}
    for a, b in hostile_edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    seen: set[int] = set()
    components: list[MineConflictComponent] = []
    for origin in sorted(adjacency):
        if origin in seen:
            continue
        todo = [origin]
        vertices: set[int] = set()
        while todo:
            current = todo.pop()
            if current in seen:
                continue
            seen.add(current)
            vertices.add(current)
            todo.extend(sorted(adjacency[current] - seen, reverse=True))
        edges = tuple(sorted((a, b) for a, b in hostile_edges if a in vertices and b in vertices))
        nodes = tuple(sorted(vertices))
        components.append(MineConflictComponent(
            field_ids=nodes,
            candidate_edges=edges,
            category="ISOLATED_PAIR" if len(nodes) == 2 and len(edges) == 1
            else "COUPLED_MULTIFIELD",
        ))
    return tuple(sorted(components, key=lambda c: c.field_ids))


def classify_conditional_mine_overlaps(
    *,
    fields: Sequence[LocatedMinefield],
    mutual_safe_passage_by_normal_owner_pair: Mapping[tuple[int, int], bool],
    max_radius: int,
    complete_phase_current_field_roster_confirmed: bool,
    exact_centers_units_and_types_confirmed: bool,
    exact_mutual_diplomacy_confirmed: bool,
    ordinary_no_protofield_or_custom_interactions_confirmed: bool,
    no_intervening_host_field_mutations_confirmed: bool,
) -> MineOverlapGraph:
    """Atomic immutable candidate-only pair and connected-component ledger.

    A tangent at integer radii is an explicit ABSTAIN because Host
    overlap semantics at zero common area are not proved by docs.
    """
    if any(flag is not True for flag in (
        complete_phase_current_field_roster_confirmed,
        exact_centers_units_and_types_confirmed,
        exact_mutual_diplomacy_confirmed,
        ordinary_no_protofield_or_custom_interactions_confirmed,
        no_intervening_host_field_mutations_confirmed,
    )):
        raise MineOverlapAbstain("unverified source snapshot/Host-interaction context")
    if type(max_radius) is not int or max_radius not in MAX_RADII:
        raise MineOverlapAbstain("untyped/custom maximum minefield radius")
    roster = _complete_fields(fields, max_radius=max_radius)
    safe = _safe_passage_map(
        mutual_safe_passage_by_normal_owner_pair,
        normal_owners={f.owner_id for f in roster if not f.is_web},
    )
    assessments: list[MinefieldPairAssessment] = []
    hostile: list[tuple[int, int]] = []
    for i, a in enumerate(roster):
        for b in roster[i + 1:]:
            radius = isqrt(a.mine_units) + isqrt(b.mine_units)
            distance2 = (a.center.x - b.center.x) ** 2 + (a.center.y - b.center.y) ** 2
            if distance2 == radius * radius:
                raise MineOverlapAbstain("exact tangent; Host overlap semantics unverified")
            if distance2 > radius * radius:
                status = "DISJOINT"
            elif a.is_web or b.is_web:
                status = "WEB_NONDESTRUCTIVE"
            elif a.owner_id == b.owner_id:
                status = "SAME_OWNER_NONDESTRUCTIVE"
            elif safe[tuple(sorted((a.owner_id, b.owner_id)))]:
                status = "MUTUAL_SAFE_PASSAGE_NONDESTRUCTIVE"
            else:
                status = "HOSTILE_NORMAL_OVERLAP_CANDIDATE"
                hostile.append((a.field_id, b.field_id))
            assessments.append(MinefieldPairAssessment(
                a.field_id, b.field_id, a.owner_id, b.owner_id,
                distance2, radius, status,
                status == "HOSTILE_NORMAL_OVERLAP_CANDIDATE",
            ))
    components = _components(hostile)
    assert len(hostile) == sum(len(c.candidate_edges) for c in components)
    return MineOverlapGraph(
        assessments=tuple(assessments),
        components=components,
        total_fields=len(roster),
        total_pairs_examined=len(assessments),
        conflict_candidate_pairs=len(hostile),
        isolated_conflict_pair_components=sum(c.category == "ISOLATED_PAIR" for c in components),
        coupled_multifield_components=sum(c.category == "COUPLED_MULTIFIELD" for c in components),
    )
