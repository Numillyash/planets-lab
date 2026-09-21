"""Bounded ordinary STANDARD queue orchestration.

This module composes already-verified C5 primitives without reconstructing
pair mechanics itself:

- caller-supplied pair decisions remain the source of pair eligibility;
- inactive or exhausted pairs are removed from the current queue view;
- the canonical initial plain-STANDARD selector chooses the next pair;
- pair occurrence history supplies the already-verified second-pass side flip.

Terminal-state mutation remains in the mutable_queue module. A convenience
adapter accepts a resolved ShipQueueMutationResult, but callers must still
supply pair inputs recomposed for the post-mutation state.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

from .mutable_queue import ShipQueueMutationResult
from .queue import (
    STANDARD_PAIR_MAX_OCCURRENCES,
    InitialStandardPairInput,
    InitialStandardSelection,
    select_initial_plain_standard,
    standard_pair_sides_for_occurrence,
)


PairKey = tuple[int, int]
PairSides = tuple[int, int]


def _pair_key(left_ship_id: int, right_ship_id: int) -> PairKey:
    return (
        (left_ship_id, right_ship_id)
        if left_ship_id < right_ship_id
        else (right_ship_id, left_ship_id)
    )


def _validate_pair(pair: PairKey) -> PairKey:
    if (
        not isinstance(pair, tuple)
        or len(pair) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in pair
        )
        or pair[0] == pair[1]
    ):
        raise ValueError("pair keys must contain two distinct positive ship ids")
    return _pair_key(pair[0], pair[1])


@dataclass(frozen=True, slots=True)
class StandardQueueState:
    """History needed to interpret repeated ordinary STANDARD pair selection."""

    pair_occurrences: Mapping[PairKey, int] = field(default_factory=dict)
    first_pass_sides: Mapping[PairKey, PairSides] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for raw_pair, count in self.pair_occurrences.items():
            pair = _validate_pair(raw_pair)
            if pair != raw_pair:
                raise ValueError("pair occurrence keys must be canonical")
            if isinstance(count, bool) or not isinstance(count, int) or not (
                0 <= count <= STANDARD_PAIR_MAX_OCCURRENCES
            ):
                raise ValueError(
                    "pair occurrence counts must be integers in the supported range"
                )

        for raw_pair, sides in self.first_pass_sides.items():
            pair = _validate_pair(raw_pair)
            if pair != raw_pair:
                raise ValueError("first-pass side keys must be canonical")
            if (
                not isinstance(sides, tuple)
                or len(sides) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                    for value in sides
                )
                or sides[0] == sides[1]
            ):
                raise ValueError(
                    "first-pass sides must contain two distinct positive ship ids"
                )
            if set(sides) != set(pair):
                raise ValueError(
                    "first-pass sides must describe the same canonical pair"
                )


@dataclass(frozen=True, slots=True)
class StandardQueueStepResult:
    """Fail-closed projection of the next ordinary STANDARD queue step."""

    engagement_available: bool | None
    selection: InitialStandardSelection | None = None
    pair: PairKey | None = None
    occurrence_index: int | None = None
    left_ship_id: int | None = None
    right_ship_id: int | None = None
    inactive_pair_count: int = 0
    exhausted_pair_count: int = 0
    unresolved_reasons: tuple[str, ...] = ()


def select_next_plain_standard(
    *,
    pair_inputs: Sequence[InitialStandardPairInput],
    active_ship_ids: Collection[int],
    state: StandardQueueState | None = None,
) -> StandardQueueStepResult:
    """Select the next ordinary STANDARD pair from the current active ship set.

    pair_inputs must already contain pair decisions recomposed for the current
    pre-engagement state. This function never reuses terminal VCR state to infer
    pair mechanics.

    Pairs touching an inactive ship are ignored. Pairs that already fought
    twice are exhausted and cannot re-enter the queue. Every remaining pair is
    passed unchanged to the canonical plain-STANDARD selector.

    For a first occurrence the canonical selector's LEFT/RIGHT assignment is
    used and becomes the history anchor. For a second occurrence the stored
    first-pass sides are required and the verified reversal helper is applied.
    """

    queue_state = state or StandardQueueState()

    active: set[int] = set()
    for ship_id in active_ship_ids:
        if (
            isinstance(ship_id, bool)
            or not isinstance(ship_id, int)
            or ship_id <= 0
        ):
            raise ValueError("active_ship_ids must contain positive integers")
        active.add(ship_id)

    if not active:
        return StandardQueueStepResult(
            engagement_available=False,
            unresolved_reasons=("no_active_ships",),
        )

    current_inputs: list[InitialStandardPairInput] = []
    inactive_pairs = 0
    exhausted_pairs = 0

    for pair_input in pair_inputs:
        pair = _pair_key(pair_input.left.ship_id, pair_input.right.ship_id)
        if (
            pair_input.left.ship_id not in active
            or pair_input.right.ship_id not in active
        ):
            inactive_pairs += 1
            continue
        if (
            int(queue_state.pair_occurrences.get(pair, 0))
            >= STANDARD_PAIR_MAX_OCCURRENCES
        ):
            exhausted_pairs += 1
            continue
        current_inputs.append(pair_input)

    if not current_inputs:
        return StandardQueueStepResult(
            engagement_available=False,
            inactive_pair_count=inactive_pairs,
            exhausted_pair_count=exhausted_pairs,
            unresolved_reasons=("no_remaining_plain_standard_pair_inputs",),
        )

    selection = select_initial_plain_standard(current_inputs)
    if selection.engagement_available is not True:
        return StandardQueueStepResult(
            engagement_available=selection.engagement_available,
            selection=selection,
            inactive_pair_count=inactive_pairs,
            exhausted_pair_count=exhausted_pairs,
            unresolved_reasons=selection.unresolved_reasons,
        )

    if (
        selection.pair is None
        or selection.left_ship_id is None
        or selection.right_ship_id is None
    ):
        return StandardQueueStepResult(
            engagement_available=None,
            selection=selection,
            inactive_pair_count=inactive_pairs,
            exhausted_pair_count=exhausted_pairs,
            unresolved_reasons=("selected_standard_pair_missing_sides",),
        )

    pair = _pair_key(*selection.pair)
    prior_occurrences = int(queue_state.pair_occurrences.get(pair, 0))
    occurrence_index = prior_occurrences + 1

    if occurrence_index == 1:
        sides = (selection.left_ship_id, selection.right_ship_id)
    elif occurrence_index == 2:
        first_pass = queue_state.first_pass_sides.get(pair)
        if first_pass is None:
            return StandardQueueStepResult(
                engagement_available=None,
                selection=selection,
                pair=pair,
                occurrence_index=occurrence_index,
                inactive_pair_count=inactive_pairs,
                exhausted_pair_count=exhausted_pairs,
                unresolved_reasons=(
                    f"{pair[0]}-{pair[1]}:first_pass_sides_missing",
                ),
            )
        if (selection.left_ship_id, selection.right_ship_id) != tuple(first_pass):
            return StandardQueueStepResult(
                engagement_available=None,
                selection=selection,
                pair=pair,
                occurrence_index=occurrence_index,
                inactive_pair_count=inactive_pairs,
                exhausted_pair_count=exhausted_pairs,
                unresolved_reasons=(
                    f"{pair[0]}-{pair[1]}:first_pass_side_history_conflict",
                ),
            )
        projected = standard_pair_sides_for_occurrence(
            first_pass_left_ship_id=first_pass[0],
            first_pass_right_ship_id=first_pass[1],
            occurrence_index=occurrence_index,
        )
        if projected is None:
            return StandardQueueStepResult(
                engagement_available=None,
                selection=selection,
                pair=pair,
                occurrence_index=occurrence_index,
                inactive_pair_count=inactive_pairs,
                exhausted_pair_count=exhausted_pairs,
                unresolved_reasons=(
                    f"{pair[0]}-{pair[1]}:occurrence_projection_unresolved",
                ),
            )
        sides = projected
    else:
        return StandardQueueStepResult(
            engagement_available=None,
            selection=selection,
            pair=pair,
            occurrence_index=occurrence_index,
            inactive_pair_count=inactive_pairs,
            exhausted_pair_count=exhausted_pairs,
            unresolved_reasons=(
                f"{pair[0]}-{pair[1]}:occurrence_out_of_supported_range",
            ),
        )

    return StandardQueueStepResult(
        engagement_available=True,
        selection=selection,
        pair=pair,
        occurrence_index=occurrence_index,
        left_ship_id=sides[0],
        right_ship_id=sides[1],
        inactive_pair_count=inactive_pairs,
        exhausted_pair_count=exhausted_pairs,
    )


def select_after_ship_mutation(
    *,
    mutation: ShipQueueMutationResult,
    pair_inputs: Sequence[InitialStandardPairInput],
    state: StandardQueueState | None = None,
) -> StandardQueueStepResult:
    """Select after resolved membership mutation using freshly composed pairs."""

    if mutation.resolved is not True:
        return StandardQueueStepResult(
            engagement_available=None,
            unresolved_reasons=(
                "ship_queue_mutation_unresolved",
                *mutation.unresolved_reasons,
            ),
        )
    return select_next_plain_standard(
        pair_inputs=pair_inputs,
        active_ship_ids=mutation.active_ships.keys(),
        state=state,
    )


def record_standard_queue_step(
    state: StandardQueueState,
    step: StandardQueueStepResult,
) -> StandardQueueState:
    """Return queue history after one selected STANDARD engagement is committed."""

    if (
        step.engagement_available is not True
        or step.pair is None
        or step.occurrence_index is None
        or step.left_ship_id is None
        or step.right_ship_id is None
    ):
        raise ValueError(
            "only a fully resolved STANDARD queue step can be recorded"
        )

    pair = _validate_pair(step.pair)
    current = int(state.pair_occurrences.get(pair, 0))
    if step.occurrence_index != current + 1:
        raise ValueError("queue step occurrence is inconsistent with history")

    occurrences = dict(state.pair_occurrences)
    occurrences[pair] = step.occurrence_index
    first_pass_sides = dict(state.first_pass_sides)

    if step.occurrence_index == 1:
        first_pass_sides[pair] = (step.left_ship_id, step.right_ship_id)
    elif pair not in first_pass_sides:
        raise ValueError("second occurrence requires recorded first-pass sides")

    return StandardQueueState(
        pair_occurrences=occurrences,
        first_pass_sides=first_pass_sides,
    )
