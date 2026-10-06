"""Evidence-scoped carried state for one ship-combat site.

This module is the first stateful composition layer above the already tested
atomic queue primitives. It deliberately does not resolve combat outcomes or
reconstruct pair eligibility. Callers still supply factual or independently
resolved terminal state and pair inputs.

The state distinguishes three concepts that must not be conflated:

* physically active ships;
* parent STANDARD queue membership;
* a temporary post-capture order for one captured prize.

A captured prize remains physically active but is removed from the parent queue
for the current site. It may temporarily receive an immediate capture-order
continuation. Exhausting that temporary order clears only the temporary order;
it does not reinsert the prize into the parent queue.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .host_queue import StandardQueueState
from .mutable_queue import (
    ShipCaptureTransfer,
    ShipQueueMutationResult,
    apply_ship_terminal_batch,
)
from .queue import STANDARD_PAIR_MAX_OCCURRENCES


PairKey = tuple[int, int]
PairSides = tuple[int, int]


def _pair_key(a: int, b: int) -> PairKey:
    if (
        isinstance(a, bool)
        or not isinstance(a, int)
        or a <= 0
        or isinstance(b, bool)
        or not isinstance(b, int)
        or b <= 0
        or a == b
    ):
        raise ValueError("pair ids must be distinct positive integers")
    return (a, b) if a < b else (b, a)


def _copy_active(
    active_ships: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    copied: dict[int, dict[str, Any]] = {}
    for ship_id, raw in active_ships.items():
        if (
            isinstance(ship_id, bool)
            or not isinstance(ship_id, int)
            or ship_id <= 0
        ):
            raise ValueError("active ship ids must be positive integers")
        if not isinstance(raw, Mapping):
            raise TypeError(f"active ship {ship_id} state must be a mapping")
        copied[ship_id] = deepcopy(dict(raw))
    return copied


@dataclass(frozen=True, slots=True)
class TemporaryCaptureOrder:
    """Temporary post-capture order anchored by prize and captor positions."""

    prize_ship_id: int
    captor_ship_id: int
    order: tuple[int, ...]

    def __post_init__(self) -> None:
        _pair_key(self.prize_ship_id, self.captor_ship_id)
        if (
            not isinstance(self.order, tuple)
            or len(self.order) < 2
            or any(
                isinstance(ship_id, bool)
                or not isinstance(ship_id, int)
                or ship_id <= 0
                for ship_id in self.order
            )
        ):
            raise ValueError("capture order must contain positive ship ids")
        if len(set(self.order)) != len(self.order):
            raise ValueError("capture order must not contain duplicate ship ids")
        if self.prize_ship_id not in self.order:
            raise ValueError("captured prize must be present in capture order")
        if self.captor_ship_id not in self.order:
            raise ValueError("captor must be present in capture order")


@dataclass(frozen=True, slots=True)
class SiteCombatState:
    """Carried mutable-queue state for one combat site."""

    active_ships: Mapping[int, Mapping[str, Any]]
    standard_queue_state: StandardQueueState = field(
        default_factory=StandardQueueState
    )
    parent_queue_excluded_ship_ids: frozenset[int] = frozenset()
    temporary_capture_order: TemporaryCaptureOrder | None = None

    def __post_init__(self) -> None:
        active = _copy_active(self.active_ships)
        object.__setattr__(self, "active_ships", active)

        excluded: set[int] = set()
        for ship_id in self.parent_queue_excluded_ship_ids:
            if (
                isinstance(ship_id, bool)
                or not isinstance(ship_id, int)
                or ship_id <= 0
            ):
                raise ValueError(
                    "parent queue exclusions must be positive ship ids"
                )
            if ship_id not in active:
                raise ValueError(
                    f"parent queue excluded ship {ship_id} is not active"
                )
            excluded.add(ship_id)
        object.__setattr__(
            self,
            "parent_queue_excluded_ship_ids",
            frozenset(excluded),
        )

        temporary = self.temporary_capture_order
        if temporary is not None:
            if temporary.prize_ship_id not in active:
                raise ValueError("temporary captured prize is not active")
            if temporary.captor_ship_id not in active:
                raise ValueError("temporary capture-order captor is not active")
            if temporary.prize_ship_id not in excluded:
                raise ValueError(
                    "temporary captured prize must be excluded from parent queue"
                )


@dataclass(frozen=True, slots=True)
class SiteTerminalTransition:
    """Atomic result of applying one factual/resolved combat terminal batch."""

    resolved: bool | None
    state: SiteCombatState
    mutation: ShipQueueMutationResult


def parent_queue_active_ship_ids(state: SiteCombatState) -> frozenset[int]:
    """Return physical active ships that remain eligible for parent selection."""

    return frozenset(
        ship_id
        for ship_id in state.active_ships
        if ship_id not in state.parent_queue_excluded_ship_ids
    )


def apply_site_terminal_batch(
    state: SiteCombatState,
    *,
    terminals_by_ship_id: Mapping[int, Mapping[str, Any]],
    capture_transfers_by_ship_id: Mapping[int, ShipCaptureTransfer] | None = None,
) -> SiteTerminalTransition:
    """Apply one resolved combat terminal batch to carried site state.

    Capture mutation is delegated to apply_ship_terminal_batch. On a resolved
    capture, each captured prize is permanently removed from the parent queue
    for the current site while remaining physically active. Destroyed ships are
    removed from the parent exclusion set automatically.

    Temporary capture-order replacement/clearing is explicit and performed by
    open_temporary_capture_order / clear_temporary_capture_order.
    """

    mutation = apply_ship_terminal_batch(
        active_ships=state.active_ships,
        terminals_by_ship_id=terminals_by_ship_id,
        capture_transfers_by_ship_id=capture_transfers_by_ship_id,
    )
    if mutation.resolved is not True:
        return SiteTerminalTransition(
            resolved=mutation.resolved,
            state=state,
            mutation=mutation,
        )

    active_ids = set(mutation.active_ships)
    excluded = set(state.parent_queue_excluded_ship_ids) & active_ids
    excluded.update(mutation.captured_ship_ids)

    temporary = state.temporary_capture_order
    if temporary is not None and (
        temporary.prize_ship_id not in active_ids
        or temporary.captor_ship_id not in active_ids
    ):
        temporary = None

    next_state = SiteCombatState(
        active_ships=mutation.active_ships,
        standard_queue_state=state.standard_queue_state,
        parent_queue_excluded_ship_ids=frozenset(excluded),
        temporary_capture_order=temporary,
    )
    return SiteTerminalTransition(
        resolved=True,
        state=next_state,
        mutation=mutation,
    )


def record_factual_site_pair(
    state: SiteCombatState,
    *,
    left_ship_id: int,
    right_ship_id: int,
) -> SiteCombatState:
    """Record one elapsed factual pair for history-anchored validation."""

    pair = _pair_key(left_ship_id, right_ship_id)
    occurrences = dict(state.standard_queue_state.pair_occurrences)
    first_sides = dict(state.standard_queue_state.first_pass_sides)

    prior = int(occurrences.get(pair, 0))
    occurrence = prior + 1
    if occurrence > STANDARD_PAIR_MAX_OCCURRENCES:
        raise ValueError(
            f"{pair[0]}-{pair[1]}:occurrence_out_of_supported_range"
        )

    if occurrence == 1:
        first_sides[pair] = (left_ship_id, right_ship_id)
    elif occurrence == 2:
        anchor = first_sides.get(pair)
        if anchor is None:
            raise ValueError(
                f"{pair[0]}-{pair[1]}:first_pass_sides_missing"
            )
        if (left_ship_id, right_ship_id) != (anchor[1], anchor[0]):
            raise ValueError(
                f"{pair[0]}-{pair[1]}:second_pass_not_reversed"
            )

    occurrences[pair] = occurrence
    return SiteCombatState(
        active_ships=state.active_ships,
        standard_queue_state=StandardQueueState(
            pair_occurrences=occurrences,
            first_pass_sides=first_sides,
        ),
        parent_queue_excluded_ship_ids=state.parent_queue_excluded_ship_ids,
        temporary_capture_order=state.temporary_capture_order,
    )


def open_temporary_capture_order(
    state: SiteCombatState,
    *,
    prize_ship_id: int,
    captor_ship_id: int,
    order: Sequence[int],
) -> SiteCombatState:
    """Open or replace the temporary order for a newly captured prize."""

    if prize_ship_id not in state.active_ships:
        raise ValueError("captured prize is not physically active")
    if captor_ship_id not in state.active_ships:
        raise ValueError("captor is not physically active")
    if prize_ship_id not in state.parent_queue_excluded_ship_ids:
        raise ValueError(
            "captured prize must already be excluded from parent queue"
        )

    temporary = TemporaryCaptureOrder(
        prize_ship_id=prize_ship_id,
        captor_ship_id=captor_ship_id,
        order=tuple(order),
    )
    return SiteCombatState(
        active_ships=state.active_ships,
        standard_queue_state=state.standard_queue_state,
        parent_queue_excluded_ship_ids=state.parent_queue_excluded_ship_ids,
        temporary_capture_order=temporary,
    )


def clear_temporary_capture_order(
    state: SiteCombatState,
    *,
    expected_prize_ship_id: int | None = None,
) -> SiteCombatState:
    """Clear an exhausted temporary order without parent reinsertion."""

    temporary = state.temporary_capture_order
    if temporary is None:
        if expected_prize_ship_id is not None:
            raise ValueError("no temporary capture order to clear")
        return state

    if (
        expected_prize_ship_id is not None
        and temporary.prize_ship_id != expected_prize_ship_id
    ):
        raise ValueError("temporary capture prize does not match expectation")

    return SiteCombatState(
        active_ships=state.active_ships,
        standard_queue_state=state.standard_queue_state,
        parent_queue_excluded_ship_ids=state.parent_queue_excluded_ship_ids,
        temporary_capture_order=None,
    )
