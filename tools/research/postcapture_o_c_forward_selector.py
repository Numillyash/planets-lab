#!/usr/bin/env python3
"""Pure O -> C-forward selector core for post-capture research.

This module contains no corpus I/O and no factual N+1 comparator. It consumes
preclassified candidate states in a frozen external order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence


CandidateDisposition = Literal[
    "inactive",
    "same_owner",
    "pair_exhausted",
    "no_request",
    "permission_denied",
    "pair_blocked",
    "eligible",
    "unresolved",
]


@dataclass(frozen=True, slots=True)
class CandidateState:
    ship_id: int
    disposition: CandidateDisposition
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SelectionResult:
    status: Literal["resolved", "unresolved", "no_pair"]
    branch: Literal["O", "C"] | None
    predicted_ship_id: int | None
    unresolved_ship_id: int | None
    reason: str | None
    trace: tuple[dict[str, object], ...]


def _scan_segment(
    *,
    branch: Literal["O", "C"],
    order: Sequence[int],
    indexes: range,
    states: Mapping[int, CandidateState],
) -> SelectionResult | None:
    trace: list[dict[str, object]] = []

    for index in indexes:
        ship_id = int(order[index])
        state = states.get(ship_id)
        if state is None:
            trace.append(
                {
                    "branch": branch,
                    "index": index,
                    "ship_id": ship_id,
                    "disposition": "unresolved",
                    "reason": "candidate_state_missing",
                }
            )
            return SelectionResult(
                status="unresolved",
                branch=branch,
                predicted_ship_id=None,
                unresolved_ship_id=ship_id,
                reason="candidate_state_missing",
                trace=tuple(trace),
            )

        trace.append(
            {
                "branch": branch,
                "index": index,
                "ship_id": ship_id,
                "disposition": state.disposition,
                "reason": state.reason,
            }
        )

        if state.disposition == "eligible":
            return SelectionResult(
                status="resolved",
                branch=branch,
                predicted_ship_id=ship_id,
                unresolved_ship_id=None,
                reason=None,
                trace=tuple(trace),
            )

        if state.disposition == "unresolved":
            return SelectionResult(
                status="unresolved",
                branch=branch,
                predicted_ship_id=None,
                unresolved_ship_id=ship_id,
                reason=state.reason or "candidate_unresolved",
                trace=tuple(trace),
            )

        # Every other disposition is independently skippable.

    return None


def select_o_then_c_forward(
    *,
    order: Sequence[int],
    prize_ship_id: int,
    captor_ship_id: int,
    states: Mapping[int, CandidateState],
) -> SelectionResult:
    if prize_ship_id not in order:
        return SelectionResult(
            status="unresolved",
            branch=None,
            predicted_ship_id=None,
            unresolved_ship_id=prize_ship_id,
            reason="prize_missing_from_order",
            trace=(),
        )
    if captor_ship_id not in order:
        return SelectionResult(
            status="unresolved",
            branch=None,
            predicted_ship_id=None,
            unresolved_ship_id=captor_ship_id,
            reason="captor_missing_from_order",
            trace=(),
        )

    prize_index = order.index(prize_ship_id)
    captor_index = order.index(captor_ship_id)

    if prize_index >= captor_index:
        return SelectionResult(
            status="unresolved",
            branch=None,
            predicted_ship_id=None,
            unresolved_ship_id=None,
            reason="unsupported_right_capture_geometry",
            trace=(),
        )

    o_result = _scan_segment(
        branch="O",
        order=order,
        indexes=range(captor_index + 1, len(order)),
        states=states,
    )
    if o_result is not None:
        return o_result

    c_result = _scan_segment(
        branch="C",
        order=order,
        indexes=range(prize_index + 1, captor_index),
        states=states,
    )
    if c_result is not None:
        return c_result

    return SelectionResult(
        status="no_pair",
        branch=None,
        predicted_ship_id=None,
        unresolved_ship_id=None,
        reason="o_and_c_forward_exhausted",
        trace=(),
    )
