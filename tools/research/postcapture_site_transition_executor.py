#!/usr/bin/env python3
"""Research-only composition layer for one post-VCR queue transition.

This module does not reconstruct corpus state.  It composes three already
separated mechanics layers:

* production atomic ship mutation after a resolved VCR;
* production ordinary STANDARD queue selection for a non-capture predecessor;
* the frozen research O->C forward selector for an immediate capture
  continuation.

The caller remains responsible for rebuilding ordinary pair inputs after the
mutation and for constructing capture candidate states without using the held
out next pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from planets_lab.rules.combat.host_queue import (
    StandardQueueState,
    select_after_ship_mutation,
)
from planets_lab.rules.combat.mutable_queue import ShipQueueMutationResult
from planets_lab.rules.combat.queue import InitialStandardPairInput

from postcapture_o_c_forward_selector import (
    CandidateState,
    SelectionResult as CaptureSelectionResult,
    select_o_then_c_forward,
)


PairKey = tuple[int, int]
PairSides = tuple[int, int]


def canonical_pair(a: int, b: int) -> PairKey:
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


@dataclass(frozen=True, slots=True)
class CaptureContinuationContext:
    order: tuple[int, ...]
    prize_ship_id: int
    captor_ship_id: int
    states: Mapping[int, CandidateState]


@dataclass(frozen=True, slots=True)
class PostVcrSelection:
    status: Literal["resolved", "unresolved", "no_pair"]
    source: Literal["capture_cursor", "ordinary_queue"] | None
    branch: Literal["O", "C"] | None = None
    pair: PairKey | None = None
    predicted_opponent_ship_id: int | None = None
    predicted_left_ship_id: int | None = None
    predicted_right_ship_id: int | None = None
    ordinary_occurrence_index: int | None = None
    reason: str | None = None
    unresolved_ship_id: int | None = None


@dataclass(frozen=True, slots=True)
class ElapsedPairRecord:
    state: StandardQueueState | None
    reason: str | None = None


def record_elapsed_factual_pair(
    state: StandardQueueState,
    *,
    left_ship_id: int,
    right_ship_id: int,
) -> ElapsedPairRecord:
    """Record one already-observed VCR into occurrence/side history.

    This is diagnostic history bookkeeping, not a predictor.  It allows a
    held-out N+1 selector to consume only factual VCRs up through N.
    """

    pair = canonical_pair(left_ship_id, right_ship_id)
    prior = int(state.pair_occurrences.get(pair, 0))
    if prior >= 2:
        return ElapsedPairRecord(
            state=None,
            reason=f"{pair[0]}-{pair[1]}:third_occurrence_unsupported",
        )

    occurrences = dict(state.pair_occurrences)
    first_sides = dict(state.first_pass_sides)
    occurrence = prior + 1
    occurrences[pair] = occurrence

    if occurrence == 1:
        first_sides[pair] = (left_ship_id, right_ship_id)
    else:
        anchor = first_sides.get(pair)
        if anchor is None:
            return ElapsedPairRecord(
                state=None,
                reason=f"{pair[0]}-{pair[1]}:first_pass_sides_missing",
            )
        expected = (anchor[1], anchor[0])
        if (left_ship_id, right_ship_id) != expected:
            return ElapsedPairRecord(
                state=None,
                reason=f"{pair[0]}-{pair[1]}:second_pass_not_reversed",
            )

    return ElapsedPairRecord(
        state=StandardQueueState(
            pair_occurrences=occurrences,
            first_pass_sides=first_sides,
        )
    )


def _capture_selection(
    *,
    mutation: ShipQueueMutationResult,
    context: CaptureContinuationContext,
) -> PostVcrSelection:
    if context.prize_ship_id not in mutation.active_ships:
        return PostVcrSelection(
            status="unresolved",
            source="capture_cursor",
            reason="captured_prize_not_active_after_mutation",
        )

    result: CaptureSelectionResult = select_o_then_c_forward(
        order=context.order,
        prize_ship_id=context.prize_ship_id,
        captor_ship_id=context.captor_ship_id,
        states=context.states,
    )
    if result.status == "unresolved":
        return PostVcrSelection(
            status="unresolved",
            source="capture_cursor",
            branch=result.branch,
            reason=result.reason,
            unresolved_ship_id=result.unresolved_ship_id,
        )
    if result.status == "no_pair" or result.predicted_ship_id is None:
        # Whether Host resumes a parent/global queue after C exhaustion is the
        # next orchestration question.  Do not silently substitute ordinary
        # selection here.
        return PostVcrSelection(
            status="no_pair",
            source="capture_cursor",
            branch=result.branch,
            reason=result.reason or "capture_cursor_exhausted",
        )

    opponent = int(result.predicted_ship_id)
    return PostVcrSelection(
        status="resolved",
        source="capture_cursor",
        branch=result.branch,
        pair=canonical_pair(context.prize_ship_id, opponent),
        predicted_opponent_ship_id=opponent,
    )


def select_after_resolved_vcr(
    *,
    mutation: ShipQueueMutationResult,
    queue_state: StandardQueueState,
    ordinary_pair_inputs: Sequence[InitialStandardPairInput],
    capture_context: CaptureContinuationContext | None = None,
) -> PostVcrSelection:
    """Select the next pair after a resolved ship-vs-ship VCR.

    Capture predecessors are given to the frozen O->C cursor.  Ordinary
    predecessors reuse the production post-mutation STANDARD selector.

    The function intentionally has no fallback from an exhausted capture cursor
    into the ordinary queue because that resumption boundary is not yet
    independently reconstructed.
    """

    if mutation.resolved is not True:
        return PostVcrSelection(
            status="unresolved",
            source=None,
            reason="ship_queue_mutation_unresolved",
        )

    if capture_context is not None:
        return _capture_selection(
            mutation=mutation,
            context=capture_context,
        )

    ordinary = select_after_ship_mutation(
        mutation=mutation,
        pair_inputs=ordinary_pair_inputs,
        state=queue_state,
    )
    if ordinary.engagement_available is None:
        return PostVcrSelection(
            status="unresolved",
            source="ordinary_queue",
            reason=(
                ordinary.unresolved_reasons[0]
                if ordinary.unresolved_reasons
                else "ordinary_queue_unresolved"
            ),
        )
    if ordinary.engagement_available is False or ordinary.pair is None:
        return PostVcrSelection(
            status="no_pair",
            source="ordinary_queue",
            reason=(
                ordinary.unresolved_reasons[0]
                if ordinary.unresolved_reasons
                else "ordinary_queue_exhausted"
            ),
        )

    return PostVcrSelection(
        status="resolved",
        source="ordinary_queue",
        pair=ordinary.pair,
        predicted_left_ship_id=ordinary.left_ship_id,
        predicted_right_ship_id=ordinary.right_ship_id,
        ordinary_occurrence_index=ordinary.occurrence_index,
    )
