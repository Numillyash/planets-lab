from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from .order import standard_battle_priority_key
from .selection import (
    ShipCombatPairDecision,
    ShipCombatPairPhase,
    ShipCombatSideInput,
)


STANDARD_PAIR_MAX_OCCURRENCES = 2


@dataclass(frozen=True, slots=True)
class InitialStandardPairInput:
    """One already-composed pair presented to the initial plain-STANDARD selector.

    ``decision`` must have been produced for exactly ``left``/``right`` after all
    pair-specific dynamic inputs (including directional STANDARD targetability)
    were reconstructed upstream.  This layer does not infer cloak, diplomacy,
    movement, mine or race state.
    """

    left: ShipCombatSideInput
    right: ShipCombatSideInput
    decision: ShipCombatPairDecision


@dataclass(frozen=True, slots=True)
class InitialStandardSelection:
    """Fail-closed result for the first ordinary plain-STANDARD stack choice."""

    engagement_available: bool | None
    eligible_pair_count: int
    pair: tuple[int, int] | None = None
    active_ship_id: int | None = None
    target_ship_id: int | None = None
    left_ship_id: int | None = None
    right_ship_id: int | None = None
    active_priority: tuple[int, int, int] | None = None
    target_priority: tuple[int, int, int] | None = None
    unresolved_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ResolvedInitialStandardCandidate:
    pair: tuple[int, int]
    active_ship_id: int
    target_ship_id: int
    active_priority: tuple[int, int, int]
    target_priority: tuple[int, int, int]

    @property
    def key(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return self.active_priority, self.target_priority


def _pair_key(left_ship_id: int, right_ship_id: int) -> tuple[int, int]:
    return (
        (left_ship_id, right_ship_id)
        if left_ship_id < right_ship_id
        else (right_ship_id, left_ship_id)
    )


def _plain_standard_candidate(
    pair_input: InitialStandardPairInput,
) -> tuple[_ResolvedInitialStandardCandidate | None, str | None]:
    """Project one resolved pair into the bounded plain-STANDARD ordering scope."""

    left = pair_input.left
    right = pair_input.right
    decision = pair_input.decision

    if left.ship_id == right.ship_id:
        return None, "pair_has_duplicate_ship_id"

    if decision.engagement_eligible is None:
        return None, "pair_engagement_unresolved"
    if decision.engagement_eligible is False:
        return None, None
    if decision.phase is not ShipCombatPairPhase.STANDARD:
        return None, "eligible_pair_not_plain_standard"

    left_priority = standard_battle_priority_key(
        ship_id=left.ship_id,
        mission=left.mission,
        primary_enemy=left.primary_enemy,
        friendly_code=left.friendly_code,
    )
    right_priority = standard_battle_priority_key(
        ship_id=right.ship_id,
        mission=right.mission,
        primary_enemy=right.primary_enemy,
        friendly_code=right.friendly_code,
    )
    if left_priority is None or right_priority is None:
        return None, "standard_priority_unresolved"

    if left_priority < right_priority:
        active = left
        target = right
        active_priority = left_priority
        target_priority = right_priority
    else:
        active = right
        target = left
        active_priority = right_priority
        target_priority = left_priority

    # The currently verified initial selector scope is plain STANDARD only.
    # Galactic Power or any other side override is deliberately excluded until
    # stack-level ordering for that branch has its own evidence gate.
    if (
        decision.right_ship_id != active.ship_id
        or decision.left_ship_id != target.ship_id
    ):
        return None, "standard_side_override_or_unresolved"

    return (
        _ResolvedInitialStandardCandidate(
            pair=_pair_key(left.ship_id, right.ship_id),
            active_ship_id=active.ship_id,
            target_ship_id=target.ship_id,
            active_priority=active_priority,
            target_priority=target_priority,
        ),
        None,
    )


def select_initial_plain_standard(
    pair_inputs: Sequence[InitialStandardPairInput],
) -> InitialStandardSelection:
    """Select the first ordinary plain-STANDARD pair from one resolved stack.

    Evidence-scoped ordering established by the C5 exact-set differential:

    1. choose the highest STANDARD Combat Priority ship which has an eligible
       pair in the supplied candidate set;
    2. for that active ship choose its highest-priority eligible target.

    Since smaller :func:`standard_battle_priority_key` tuples are higher
    priority, this is the lexicographic minimum of
    ``(active_priority, target_priority)``.

    The primitive is intentionally strict.  An unresolved pair, an eligible
    pre-standard pair, unsupported priority or a STANDARD side override makes
    the whole initial selection unresolved rather than silently dropping a pair
    which could outrank the apparent winner.  Known blocked pairs are safely
    ignored.  Upstream code remains responsible for presenting all relevant
    pair candidates at one battle location and for resolving pair-specific
    directional targetability before calling this function.
    """

    if not pair_inputs:
        return InitialStandardSelection(
            engagement_available=False,
            eligible_pair_count=0,
            unresolved_reasons=("no_pair_inputs",),
        )

    candidates: list[_ResolvedInitialStandardCandidate] = []
    unresolved: list[str] = []
    seen_pairs: set[tuple[int, int]] = set()

    for pair_input in pair_inputs:
        pair = _pair_key(pair_input.left.ship_id, pair_input.right.ship_id)
        if pair in seen_pairs:
            unresolved.append(f"duplicate_pair_input:{pair[0]}-{pair[1]}")
            continue
        seen_pairs.add(pair)

        candidate, reason = _plain_standard_candidate(pair_input)
        if reason is not None:
            unresolved.append(f"{pair[0]}-{pair[1]}:{reason}")
        elif candidate is not None:
            candidates.append(candidate)

    if unresolved:
        return InitialStandardSelection(
            engagement_available=None,
            eligible_pair_count=len(candidates),
            unresolved_reasons=tuple(unresolved),
        )

    if not candidates:
        return InitialStandardSelection(
            engagement_available=False,
            eligible_pair_count=0,
            unresolved_reasons=("no_eligible_plain_standard_pair",),
        )

    selected = min(candidates, key=lambda candidate: candidate.key)
    return InitialStandardSelection(
        engagement_available=True,
        eligible_pair_count=len(candidates),
        pair=selected.pair,
        active_ship_id=selected.active_ship_id,
        target_ship_id=selected.target_ship_id,
        left_ship_id=selected.target_ship_id,
        right_ship_id=selected.active_ship_id,
        active_priority=selected.active_priority,
        target_priority=selected.target_priority,
    )


def standard_pair_sides_for_occurrence(
    *,
    first_pass_left_ship_id: int,
    first_pass_right_ship_id: int,
    occurrence_index: int,
) -> tuple[int, int] | None:
    """Return queue-aware sides for an ordinary repeated standard pair.

    This helper does **not** decide whether a pair fights again. It only projects
    LEFT/RIGHT after a mutable queue has already selected the first or second
    occurrence of the same ordinary standard ship pair within one
    battle-turn/location.

    Evidence boundary:

    - occurrence 1 keeps the already resolved first-pass sides;
    - occurrence 2 reverses those sides;
    - later occurrences fail closed because the documented Host boundary is at
      most two combats per ship pair and the current ordinary corpus contains no
      third occurrence;
    - the exact second-pass reversal is corpus-observed and differentially
      verified only for the conservative plain-standard repeated-pair scope. It
      is intentionally not folded into the static battle-priority key.
    """

    for name, value in (
        ("first_pass_left_ship_id", first_pass_left_ship_id),
        ("first_pass_right_ship_id", first_pass_right_ship_id),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if first_pass_left_ship_id == first_pass_right_ship_id:
        raise ValueError("first-pass ship ids must be distinct")
    if (
        isinstance(occurrence_index, bool)
        or not isinstance(occurrence_index, int)
        or occurrence_index <= 0
    ):
        raise ValueError("occurrence_index must be a positive integer")

    if occurrence_index == 1:
        return first_pass_left_ship_id, first_pass_right_ship_id
    if occurrence_index == 2:
        return first_pass_right_ship_id, first_pass_left_ship_id
    return None
