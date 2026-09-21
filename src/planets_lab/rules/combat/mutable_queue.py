"""Bounded mutable ship-queue state after one resolved ship-vs-ship combat.

This module bridges already-verified C3 survivor carry-over into the C5 queue.
It deliberately does not choose the next pair, resolve capture ownership, apply
planet combat, or infer terminal combat results.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .sequence import (
    DYNAMIC_CARRY_FIELDS,
    carry_captured_ship_to_next_engagement,
    carry_ship_to_next_engagement,
)


@dataclass(frozen=True, slots=True)
class ShipCaptureTransfer:
    """Explicit post-combat ownership/race attribution for a captured ship."""

    new_owner_id: int
    new_race_id: int
    new_federation_crew_bonus: bool
    new_lizard_crew_bonus: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("new_owner_id", self.new_owner_id),
            ("new_race_id", self.new_race_id),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.new_federation_crew_bonus, bool):
            raise ValueError("new_federation_crew_bonus must be boolean")
        if not isinstance(self.new_lizard_crew_bonus, bool):
            raise ValueError("new_lizard_crew_bonus must be boolean")


@dataclass(frozen=True, slots=True)
class ShipQueueMutationResult:
    """Atomic fail-closed mutation of the active ship map."""

    resolved: bool | None
    active_ships: dict[int, dict[str, Any]]
    removed_ship_ids: tuple[int, ...] = ()
    carried_ship_ids: tuple[int, ...] = ()
    captured_ship_ids: tuple[int, ...] = ()
    unresolved_reasons: tuple[str, ...] = ()


def _active_copy(
    active_ships: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    copied: dict[int, dict[str, Any]] = {}
    for ship_id, raw in active_ships.items():
        if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
            raise ValueError("active ship ids must be positive integers")
        if not isinstance(raw, Mapping):
            raise TypeError(f"active ship {ship_id} state must be a mapping")
        copied[ship_id] = deepcopy(dict(raw))
    return copied


def apply_ship_terminal_batch(
    *,
    active_ships: Mapping[int, Mapping[str, Any]],
    terminals_by_ship_id: Mapping[int, Mapping[str, Any]],
    capture_transfers_by_ship_id: Mapping[int, ShipCaptureTransfer] | None = None,
) -> ShipQueueMutationResult:
    """Apply terminal states for one resolved ship combat atomically.

    The caller supplies the current active ship map and terminal replay/result
    state for every participant whose queue state must be updated. Terminal
    ``destroyed`` and ``captured`` flags must be explicit booleans.

    Supported scope:

    - destroyed ship -> removed from the active map;
    - non-destroyed/non-captured survivor -> carried through the already-tested
      :func:`carry_ship_to_next_engagement` C3 transition;
    - capture without explicit transfer metadata -> unresolved/fail closed;
    - capture with explicit :class:`ShipCaptureTransfer` -> retain the ship,
      apply the documented prize crew and transfer identity to the captor;
    - missing/unknown terminal flags or incomplete survivor carry state ->
      unresolved.

    Failure is atomic. An unresolved capture or malformed survivor prevents all
    sibling terminal mutations from being partially committed.
    """

    baseline = _active_copy(active_ships)
    capture_transfers = dict(capture_transfers_by_ship_id or {})
    if not terminals_by_ship_id:
        raise ValueError("terminals_by_ship_id must not be empty")

    terminal_rows: dict[int, Mapping[str, Any]] = {}
    unresolved: list[str] = []
    for ship_id, terminal in terminals_by_ship_id.items():
        if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
            raise ValueError("terminal ship ids must be positive integers")
        if ship_id not in baseline:
            raise ValueError(f"terminal ship {ship_id} is not active")
        if not isinstance(terminal, Mapping):
            raise TypeError(f"terminal ship {ship_id} state must be a mapping")
        terminal_rows[ship_id] = terminal

        destroyed = terminal.get("destroyed")
        captured = terminal.get("captured")
        if not isinstance(destroyed, bool):
            unresolved.append(f"{ship_id}:destroyed_state_unresolved")
        if not isinstance(captured, bool):
            unresolved.append(f"{ship_id}:captured_state_unresolved")
        elif captured and ship_id not in capture_transfers:
            unresolved.append(f"{ship_id}:capture_branch_unresolved")

        if destroyed is False and captured is False:
            for field in DYNAMIC_CARRY_FIELDS:
                value = terminal.get(field)
                if isinstance(value, bool) or not isinstance(value, int):
                    unresolved.append(f"{ship_id}:survivor_{field}_unresolved")
        elif destroyed is False and captured is True:
            for field in DYNAMIC_CARRY_FIELDS:
                value = terminal.get(field)
                if isinstance(value, bool) or not isinstance(value, int):
                    unresolved.append(f"{ship_id}:captured_{field}_unresolved")

    for ship_id, transfer in capture_transfers.items():
        if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
            raise ValueError("capture transfer ship ids must be positive integers")
        if ship_id not in terminal_rows:
            raise ValueError(f"capture transfer ship {ship_id} has no terminal state")
        if not isinstance(transfer, ShipCaptureTransfer):
            raise TypeError(f"capture transfer ship {ship_id} must use ShipCaptureTransfer")
        if terminal_rows[ship_id].get("captured") is not True:
            raise ValueError(f"capture transfer ship {ship_id} is not captured")

    if unresolved:
        return ShipQueueMutationResult(
            resolved=None,
            active_ships=baseline,
            unresolved_reasons=tuple(unresolved),
        )

    staged = deepcopy(baseline)
    removed: list[int] = []
    carried: list[int] = []
    captured_ids: list[int] = []

    try:
        for ship_id in sorted(terminal_rows):
            terminal = terminal_rows[ship_id]
            if terminal["destroyed"] is True:
                del staged[ship_id]
                removed.append(ship_id)
                continue

            if terminal["captured"] is True:
                transfer = capture_transfers[ship_id]
                staged[ship_id] = carry_captured_ship_to_next_engagement(
                    baseline[ship_id],
                    terminal,
                    new_owner_id=transfer.new_owner_id,
                    new_race_id=transfer.new_race_id,
                    new_federation_crew_bonus=transfer.new_federation_crew_bonus,
                    new_lizard_crew_bonus=transfer.new_lizard_crew_bonus,
                )
                captured_ids.append(ship_id)
                continue

            staged[ship_id] = carry_ship_to_next_engagement(
                baseline[ship_id],
                terminal,
            )
            carried.append(ship_id)
    except (KeyError, TypeError, ValueError) as exc:
        return ShipQueueMutationResult(
            resolved=None,
            active_ships=baseline,
            unresolved_reasons=(
                f"carry_transition_unresolved:{type(exc).__name__}:{exc}",
            ),
        )

    return ShipQueueMutationResult(
        resolved=True,
        active_ships=staged,
        removed_ship_ids=tuple(removed),
        carried_ship_ids=tuple(carried),
        captured_ship_ids=tuple(captured_ids),
    )
