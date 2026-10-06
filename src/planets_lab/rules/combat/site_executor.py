"""Evidence-scoped mutable site queue orchestration.

This module composes carried SiteCombatState with two already bounded queue
mechanisms:

* temporary post-capture O -> C-forward continuation;
* parent STANDARD queue selection.

It does not reconstruct candidate eligibility, diplomacy, combat outcomes or
immediate-C LEFT/RIGHT projection. Those remain caller-supplied evidence-scoped
inputs.

The O branch is intentionally fail-closed by default because independent fresh
coverage currently exists only for C-forward.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from .capture_queue import (
    CaptureCandidateState,
    CaptureQueueSelection,
    select_o_then_c_forward,
)
from .host_queue import StandardQueueStepResult, select_next_plain_standard
from .queue import InitialStandardPairInput
from .site_state import (
    SiteCombatState,
    clear_temporary_capture_order,
    parent_queue_active_ship_ids,
)


PairKey = tuple[int, int]


def _pair_key(a: int, b: int) -> PairKey:
    return (a, b) if a < b else (b, a)


@dataclass(frozen=True, slots=True)
class TemporaryContinuationStep:
    """Result of evaluating the currently open temporary capture order."""

    status: Literal[
        "resolved",
        "parent_resume_required",
        "unresolved",
    ]
    state: SiteCombatState
    branch: Literal["O", "C"] | None = None
    pair: PairKey | None = None
    prize_ship_id: int | None = None
    opponent_ship_id: int | None = None
    reason: str | None = None
    unresolved_ship_id: int | None = None
    selector: CaptureQueueSelection | None = None


@dataclass(frozen=True, slots=True)
class ParentResumeStep:
    """Parent STANDARD queue selection over the carried site state."""

    status: Literal["resolved", "no_pair", "unresolved"]
    state: SiteCombatState
    selection: StandardQueueStepResult
    pair: PairKey | None = None
    left_ship_id: int | None = None
    right_ship_id: int | None = None
    occurrence_index: int | None = None
    reason: str | None = None


def select_temporary_capture_continuation(
    state: SiteCombatState,
    *,
    candidate_states: Mapping[int, CaptureCandidateState],
    allow_unvalidated_o_branch: bool = False,
) -> TemporaryContinuationStep:
    """Evaluate and, when exhausted, clear the open temporary capture order.

    A resolved C-forward result leaves the temporary order open because the
    captured prize is about to fight again.

    A no-pair result clears only the temporary order and returns
    parent_resume_required. The prize remains physically active and remains
    excluded from the parent queue.

    A resolved O result fails closed unless explicitly enabled by a research
    caller because independent fresh O coverage is still absent.
    """

    temporary = state.temporary_capture_order
    if temporary is None:
        return TemporaryContinuationStep(
            status="unresolved",
            state=state,
            reason="temporary_capture_order_missing",
        )

    selected = select_o_then_c_forward(
        order=temporary.order,
        prize_ship_id=temporary.prize_ship_id,
        captor_ship_id=temporary.captor_ship_id,
        states=candidate_states,
    )

    if selected.status == "unresolved":
        return TemporaryContinuationStep(
            status="unresolved",
            state=state,
            branch=selected.branch,
            prize_ship_id=temporary.prize_ship_id,
            reason=selected.reason,
            unresolved_ship_id=selected.unresolved_ship_id,
            selector=selected,
        )

    if selected.status == "no_pair":
        cleared = clear_temporary_capture_order(
            state,
            expected_prize_ship_id=temporary.prize_ship_id,
        )
        return TemporaryContinuationStep(
            status="parent_resume_required",
            state=cleared,
            prize_ship_id=temporary.prize_ship_id,
            reason=selected.reason,
            selector=selected,
        )

    opponent = selected.predicted_ship_id
    if opponent is None:
        return TemporaryContinuationStep(
            status="unresolved",
            state=state,
            branch=selected.branch,
            prize_ship_id=temporary.prize_ship_id,
            reason="capture_selector_resolved_without_opponent",
            selector=selected,
        )

    if selected.branch == "O" and not allow_unvalidated_o_branch:
        return TemporaryContinuationStep(
            status="unresolved",
            state=state,
            branch="O",
            prize_ship_id=temporary.prize_ship_id,
            opponent_ship_id=opponent,
            reason="o_branch_not_independently_covered",
            selector=selected,
        )

    return TemporaryContinuationStep(
        status="resolved",
        state=state,
        branch=selected.branch,
        pair=_pair_key(temporary.prize_ship_id, opponent),
        prize_ship_id=temporary.prize_ship_id,
        opponent_ship_id=opponent,
        selector=selected,
    )


def select_parent_resume(
    state: SiteCombatState,
    *,
    pair_inputs: Sequence[InitialStandardPairInput],
) -> ParentResumeStep:
    """Select the next parent STANDARD engagement from carried site state."""

    active = parent_queue_active_ship_ids(state)
    selected = select_next_plain_standard(
        pair_inputs=pair_inputs,
        active_ship_ids=active,
        state=state.standard_queue_state,
    )

    if selected.engagement_available is None:
        return ParentResumeStep(
            status="unresolved",
            state=state,
            selection=selected,
            pair=selected.pair,
            occurrence_index=selected.occurrence_index,
            reason=(
                selected.unresolved_reasons[0]
                if selected.unresolved_reasons
                else "parent_standard_unresolved"
            ),
        )

    if selected.engagement_available is False or selected.pair is None:
        return ParentResumeStep(
            status="no_pair",
            state=state,
            selection=selected,
            reason=(
                selected.unresolved_reasons[0]
                if selected.unresolved_reasons
                else "parent_standard_exhausted"
            ),
        )

    if selected.left_ship_id is None or selected.right_ship_id is None:
        return ParentResumeStep(
            status="unresolved",
            state=state,
            selection=selected,
            pair=selected.pair,
            occurrence_index=selected.occurrence_index,
            reason="parent_standard_resolved_without_sides",
        )

    return ParentResumeStep(
        status="resolved",
        state=state,
        selection=selected,
        pair=selected.pair,
        left_ship_id=selected.left_ship_id,
        right_ship_id=selected.right_ship_id,
        occurrence_index=selected.occurrence_index,
    )
