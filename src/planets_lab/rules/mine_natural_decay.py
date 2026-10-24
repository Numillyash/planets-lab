"""Conservative *isolated* standard NuHost minefield natural-decay ledger.

Rule source: https://help.planets.nu/minefields (Mine Decay):
    round(units * 0.95) - 1 in open space
    round(units * 0.85) - 1 when intersecting a Nebula
    floor(sqrt(units)) for integer radius.

The public rule does not resolve exact half-integer rounding. Such cases
ABSTAIN, rather than silently assuming Python banker/half-up rounding.
These are DOCUMENTED formulas and TESTED conditional arithmetic, not a
Host-verified phase or an actual turn execution. This never resolves
lay/sweep/scoop, intersecting hostile fields, density, mine hits, movement,
owner switches, cloaking or the Host phase order.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

STANDARD_MAX_RADII = frozenset((100, 150))
OPEN_SPACE_RATE = 5
NEBULA_RATE = 15
EVIDENCE = "DOCUMENTED_AND_TESTED_CONDITIONAL_NOT_HOST_DIFF_VERIFIED"


class MineDecayAbstain(ValueError):
    """Required source/phase/rounding input is absent or unsupported."""


@dataclass(frozen=True, slots=True)
class MinefieldState:
    field_id: int
    owner_id: int
    mine_units: int
    is_web: bool


@dataclass(frozen=True, slots=True)
class NaturalDecayEvent:
    field_id: int
    owner_id: int
    is_web: bool
    was_in_nebula: bool
    units_before: int
    units_after: int
    units_lost: int
    radius_before: int
    radius_after: int
    field_exhausted: bool


@dataclass(frozen=True, slots=True)
class NaturalDecayTurn:
    turn_index: int
    fields_before: tuple[MinefieldState, ...]
    fields_after: tuple[MinefieldState, ...]
    events: tuple[NaturalDecayEvent, ...]
    units_before: int
    units_after: int
    natural_units_lost: int


@dataclass(frozen=True, slots=True)
class NaturalDecaySequence:
    turns: tuple[NaturalDecayTurn, ...]
    fields_final: tuple[MinefieldState, ...]
    initially_present_units: int
    final_units: int
    total_natural_units_lost: int
    evidence: str = EVIDENCE
    host_causal_verified: bool = False
    full_host_mine_lifecycle_verified: bool = False
    host_phase_order_verified: bool = False


def _positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def _validated_fields(
    fields: Sequence[MinefieldState], *, max_radius: int,
) -> tuple[MinefieldState, ...]:
    if type(max_radius) is not int or max_radius not in STANDARD_MAX_RADII:
        raise MineDecayAbstain("nonstandard, dense or unknown radius limit")
    if not isinstance(fields, (list, tuple)):
        raise MineDecayAbstain("complete explicitly ordered field roster required")
    result: list[MinefieldState] = []
    seen: set[int] = set()
    for item in fields:
        if type(item) is not MinefieldState:
            raise MineDecayAbstain("untyped or unsupported field record")
        if (
            not _positive_integer(item.field_id)
            or not _positive_integer(item.owner_id)
            or not _positive_integer(item.mine_units)
            or type(item.is_web) is not bool
            or item.mine_units > max_radius * max_radius
        ):
            raise MineDecayAbstain("unsupported field identifier, owner, mine units or density")
        if item.field_id in seen:
            raise MineDecayAbstain("duplicate field identity")
        seen.add(item.field_id)
        result.append(item)
    return tuple(sorted(result, key=lambda item: item.field_id))


def _retained_after_natural_decay(units: int, *, intersects_nebula: bool) -> int:
    rate = NEBULA_RATE if intersects_nebula else OPEN_SPACE_RATE
    numerator = units * (100 - rate)
    quotient, remainder = divmod(numerator, 100)
    if remainder == 50:
        raise MineDecayAbstain("Host tie rounding of documented decay is unverified")
    nearest = quotient + (1 if remainder > 50 else 0)
    return max(0, nearest - 1)


def simulate_isolated_natural_mine_decay(
    *,
    fields: Sequence[MinefieldState],
    nebula_intersects_by_field_id: Mapping[int, bool],
    max_radius: int = 150,
    turns: int = 1,
    isolated_decay_only_confirmed: bool,
    standard_density_confirmed: bool,
) -> NaturalDecaySequence:
    """All-or-nothing bounded natural decay; never inserts a Host phase.

    Every *initially present* field requires a pinned per-turn Nebula
    intersection value. Values for fields exhausted by earlier turns must
    still exist in the input but are not used after exhaustion. No implicit
    geometric inference, Host phase placement or environment/ship actions.
    """
    if isolated_decay_only_confirmed is not True:
        raise MineDecayAbstain("mine laying/sweeping/scooping/interactions not excluded")
    if standard_density_confirmed is not True:
        raise MineDecayAbstain("dense or custom minefield rules unsupported")
    if type(turns) is not int or not 1 <= turns <= 12:
        raise MineDecayAbstain("only 1..12 complete isolated turns supported")
    roster = _validated_fields(fields, max_radius=max_radius)
    if not isinstance(nebula_intersects_by_field_id, Mapping):
        raise MineDecayAbstain("explicit per-field Nebula context required")
    initial_ids = {f.field_id for f in roster}
    if set(nebula_intersects_by_field_id) != initial_ids:
        raise MineDecayAbstain("Nebula context must match the exact initial field roster")
    for field_id, value in nebula_intersects_by_field_id.items():
        if not _positive_integer(field_id) or type(value) is not bool:
            raise MineDecayAbstain("Nebula flags must be exact boolean, not inferred")

    current = roster
    snapshots: list[NaturalDecayTurn] = []
    first_units = sum(f.mine_units for f in roster)
    for turn_index in range(1, turns + 1):
        next_fields: list[MinefieldState] = []
        events: list[NaturalDecayEvent] = []
        for old in current:
            nebula = nebula_intersects_by_field_id[old.field_id]
            remaining = _retained_after_natural_decay(old.mine_units, intersects_nebula=nebula)
            event = NaturalDecayEvent(
                field_id=old.field_id,
                owner_id=old.owner_id,
                is_web=old.is_web,
                was_in_nebula=nebula,
                units_before=old.mine_units,
                units_after=remaining,
                units_lost=old.mine_units - remaining,
                radius_before=isqrt(old.mine_units),
                radius_after=isqrt(remaining),
                field_exhausted=remaining == 0,
            )
            events.append(event)
            if remaining > 0:
                next_fields.append(
                    MinefieldState(
                        field_id=old.field_id,
                        owner_id=old.owner_id,
                        mine_units=remaining,
                        is_web=old.is_web,
                    )
                )
        after = tuple(next_fields)
        before_count = sum(f.mine_units for f in current)
        after_count = sum(f.mine_units for f in after)
        loss = sum(e.units_lost for e in events)
        if before_count != after_count + loss:
            raise MineDecayAbstain("natural mine-unit conservation failed")
        snapshots.append(NaturalDecayTurn(
            turn_index=turn_index,
            fields_before=current,
            fields_after=after,
            events=tuple(events),
            units_before=before_count,
            units_after=after_count,
            natural_units_lost=loss,
        ))
        current = after
    final_count = sum(f.mine_units for f in current)
    total_lost = sum(turn.natural_units_lost for turn in snapshots)
    if first_units != final_count + total_lost:
        raise MineDecayAbstain("multiturn natural mine-unit conservation failed")
    return NaturalDecaySequence(
        turns=tuple(snapshots),
        fields_final=current,
        initially_present_units=first_units,
        final_units=final_count,
        total_natural_units_lost=total_lost,
    )
