"""Bounded mutable ship-queue state after one resolved ship-vs-ship combat.

This module bridges already-verified C3 survivor carry-over into the C5 queue.
It deliberately does not choose the next pair, resolve capture ownership, apply
planet combat, or infer terminal combat results.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .sequence import carry_ship_to_next_engagement


@dataclass(frozen=True, slots=True)
class ShipQueueMutationResult:
    """Atomic fail-closed mutation of the active ship map."""

    resolved: bool | None
    active_ships: dict[int, dict[str, Any]]
    removed_ship_ids: tuple[int, ...] = ()
    carried_ship_ids: tuple[int, ...] = ()
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
) -> ShipQueueMutationResult:
    """Apply terminal states for one resolved ship combat atomically.

    The caller supplies the current active ship map and terminal replay/result
    state for every participant whose queue state must be updated.  Terminal
    ``destroyed`` and ``captured`` flags must be explicit booleans.

    Supported scope:

    - destroyed ship -> removed from the active map;
    - non-destroyed/non-captured survivor -> carried through the already-tested
      :func:`carry_ship_to_next_engagement` C3 transition;
    - capture -> unresolved, because ownership/hostility continuation has not yet
      passed a C5 queue gate;
    - missing/unknown terminal flags or carry failure -> unresolved.

    Failure is atomic.  An unresolved capture or malformed survivor prevents all
    sibling terminal mutations from being partially committed.
    """

    baseline = _active_copy(active_ships)
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
        elif captured:
            unresolved.append(f"{ship_id}:capture_branch_unresolved")

    if unresolved:
        return ShipQueueMutationResult(
            resolved=None,
            active_ships=baseline,
            unresolved_reasons=tuple(unresolved),
        )

    staged = deepcopy(baseline)
    removed: list[int] = []
    carried: list[int] = []

    try:
        for ship_id in sorted(terminal_rows):
            terminal = terminal_rows[ship_id]
            if terminal["destroyed"] is True:
                del staged[ship_id]
                removed.append(ship_id)
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
    )
