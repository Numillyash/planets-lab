"""Evidence-scoped input construction for the mutable site executor.

This module adapts already collected factual pre-state into inputs consumed by
SiteCombatState/site_executor.  It deliberately has no corpus I/O and no
knowledge of held-out comparator rows.

Evidence boundary:

* same-turn diplomacy controls are truncated through the current factual VCR;
* current physical owner is assembled separately from T-1 order state;
* owner changes in ordinary candidate/parent inputs fail closed;
* post-capture candidate classification consumes only carried state and
  pre-existing T-1/order/diplomacy evidence;
* O-branch promotion and immediate-C LEFT/RIGHT projection are not implemented
  here.  site_executor keeps O fail-closed and side projection remains a
  research-harness concern;
* terminal combat outcome is not produced here and remains an injected factual
  dependency in the current validation stage.

The eligibility-specific primitives are callback-injected on purpose.  Their
current evidence implementations still live in research diagnostics; keeping
those callbacks outside this module prevents reusable mainline code from
importing tools/diagnostics while centralizing the evidence-safe assembly
plumbing.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from .capture_queue import CaptureCandidateState
from .queue import InitialStandardPairInput
from .selection import ShipCombatSideInput, decide_ship_combat_pair
from .site_state import SiteCombatState, parent_queue_active_ship_ids


class EvidenceInputUnresolved(ValueError):
    """Required pre-state evidence is missing or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class CurrentOwnerTMinus1OrderContext:
    ship_id: int
    current_owner_id: int
    tminus1_owner_id: int
    raw: Mapping[str, Any]
    prediction: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CaptureCandidateAdapterResult:
    candidate_states: Mapping[int, CaptureCandidateState]
    diagnostics: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ParentStandardInputAdapterResult:
    pair_inputs: tuple[InitialStandardPairInput, ...]
    diagnostics: Mapping[str, Any]


def _pair_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return int(value)


def filter_diplomacy_controls_through_vcr(
    controls: Mapping[Any, Any],
    *,
    target_battle_turn: int,
    through_vcr_id: int,
) -> dict[Any, set[Any]]:
    """Drop future same-turn diplomacy evidence before predicting N+1.

    Rows from other turns are preserved exactly as in the validated diagnostic
    calibration.  Within target_battle_turn, only VCR ids <= through_vcr_id are
    admissible.
    """

    filtered: dict[Any, set[Any]] = {}
    for key, rows in controls.items():
        try:
            iterable = set(rows)
        except TypeError as exc:
            raise EvidenceInputUnresolved(
                "diplomacy_control_rows_not_iterable"
            ) from exc

        kept: set[Any] = set()
        for row in iterable:
            if (
                isinstance(row, tuple)
                and len(row) >= 2
                and isinstance(row[0], int)
                and not isinstance(row[0], bool)
                and isinstance(row[1], int)
                and not isinstance(row[1], bool)
                and row[0] == target_battle_turn
                and row[1] > through_vcr_id
            ):
                continue
            kept.add(row)
        filtered[key] = kept
    return filtered


def assemble_current_owner_tminus1_order_context(
    *,
    state: SiteCombatState,
    predictions: Mapping[int, Mapping[str, Any]],
    ship_id: int,
) -> CurrentOwnerTMinus1OrderContext:
    """Assemble current physical ownership with frozen T-1 order state."""

    current = state.active_ships.get(ship_id)
    if not isinstance(current, Mapping):
        raise EvidenceInputUnresolved(f"ship {ship_id}: current state missing")
    current_owner = _positive_int(current.get("owner_id"))
    if current_owner is None:
        raise EvidenceInputUnresolved(
            f"ship {ship_id}: current owner unresolved"
        )

    prediction = predictions.get(ship_id)
    if not isinstance(prediction, Mapping):
        raise EvidenceInputUnresolved(
            f"ship {ship_id}: T-1 prediction missing"
        )
    tminus1_owner = _positive_int(prediction.get("owner_id"))
    raw = prediction.get("raw")
    if tminus1_owner is None or not isinstance(raw, Mapping):
        raise EvidenceInputUnresolved(
            f"ship {ship_id}: T-1 identity/orders missing"
        )

    return CurrentOwnerTMinus1OrderContext(
        ship_id=ship_id,
        current_owner_id=current_owner,
        tminus1_owner_id=tminus1_owner,
        raw=raw,
        prediction=prediction,
    )


def build_post_capture_candidate_states(
    *,
    state: SiteCombatState,
    context: Mapping[str, Any],
    prize_ship_id: int,
    through_vcr_id: int,
    requests_combat: Callable[[Mapping[str, Any], int], bool],
    relation_signature: Callable[[Mapping[Any, Any], int, int], Any],
    independent_permission: Callable[..., bool | None],
    pair_disposition: Callable[..., tuple[str, str | None]],
) -> CaptureCandidateAdapterResult:
    """Build temporary post-capture candidate states without reading N+1."""

    predictions = context.get("predictions")
    relations = context.get("relations")
    controls_raw = context.get("controls")
    start_stacks = context.get("start_stacks")
    before_turn = context.get("before_turn")
    game_id = context.get("game_id")
    battle_turn = context.get("battle_turn")
    if (
        not isinstance(predictions, Mapping)
        or not isinstance(relations, Mapping)
        or not isinstance(controls_raw, Mapping)
        or not isinstance(start_stacks, Mapping)
        or isinstance(before_turn, bool)
        or not isinstance(before_turn, int)
        or isinstance(game_id, bool)
        or not isinstance(game_id, int)
        or isinstance(battle_turn, bool)
        or not isinstance(battle_turn, int)
    ):
        raise EvidenceInputUnresolved("candidate_context_incomplete")

    controls = filter_diplomacy_controls_through_vcr(
        controls_raw,
        target_battle_turn=int(battle_turn),
        through_vcr_id=through_vcr_id,
    )

    prize = state.active_ships.get(prize_ship_id)
    if not isinstance(prize, Mapping):
        raise EvidenceInputUnresolved("captured_prize_not_physically_active")
    prize_owner = _positive_int(prize.get("owner_id"))
    prize_race = _positive_int(prize.get("race_id"))
    prize_hull = _positive_int(prize.get("hull_id"))
    if prize_owner is None or prize_race is None or prize_hull is None:
        raise EvidenceInputUnresolved("captured_prize_identity_unresolved")

    order = state.temporary_capture_order
    if order is None or order.prize_ship_id != prize_ship_id:
        raise EvidenceInputUnresolved("temporary_capture_order_missing")

    states: dict[int, CaptureCandidateState] = {}
    details: dict[str, Any] = {}

    def store(
        ship_id: int,
        disposition: str,
        reason: str | None,
        *,
        prior: int,
        current_owner: int | None = None,
        tminus1_owner: int | None = None,
    ) -> None:
        states[ship_id] = CaptureCandidateState(
            ship_id=ship_id,
            disposition=disposition,  # type: ignore[arg-type]
            reason=reason,
        )
        details[str(ship_id)] = {
            "disposition": disposition,
            "reason": reason,
            "prior_pair_occurrences": prior,
            "current_owner_id": current_owner,
            "tminus1_owner_id": tminus1_owner,
        }

    for ship_id in order.order:
        if ship_id == prize_ship_id:
            continue

        pair = _pair_key(prize_ship_id, ship_id)
        prior = int(state.standard_queue_state.pair_occurrences.get(pair, 0))

        if ship_id not in state.active_ships:
            store(ship_id, "inactive", None, prior=prior)
            continue
        if prior >= 2:
            store(ship_id, "pair_exhausted", None, prior=prior)
            continue

        current = state.active_ships[ship_id]
        current_owner = (
            _positive_int(current.get("owner_id"))
            if isinstance(current, Mapping)
            else None
        )
        if current_owner is None:
            store(
                ship_id,
                "unresolved",
                "current_owner_unresolved",
                prior=prior,
            )
            continue
        if current_owner == prize_owner:
            store(
                ship_id,
                "same_owner",
                None,
                prior=prior,
                current_owner=current_owner,
            )
            continue

        try:
            assembled = assemble_current_owner_tminus1_order_context(
                state=state,
                predictions=predictions,
                ship_id=ship_id,
            )
        except EvidenceInputUnresolved as exc:
            store(
                ship_id,
                "unresolved",
                str(exc),
                prior=prior,
                current_owner=current_owner,
            )
            continue

        if assembled.tminus1_owner_id != assembled.current_owner_id:
            store(
                ship_id,
                "unresolved",
                "candidate_owner_changed_before_capture",
                prior=prior,
                current_owner=assembled.current_owner_id,
                tminus1_owner=assembled.tminus1_owner_id,
            )
            continue

        request = requests_combat(assembled.raw, prize_owner)
        if request is False:
            store(
                ship_id,
                "no_request",
                None,
                prior=prior,
                current_owner=assembled.current_owner_id,
                tminus1_owner=assembled.tminus1_owner_id,
            )
            continue
        if request is not True:
            store(
                ship_id,
                "unresolved",
                "combat_request_unresolved",
                prior=prior,
                current_owner=assembled.current_owner_id,
                tminus1_owner=assembled.tminus1_owner_id,
            )
            continue

        signature = relation_signature(
            relations.get(int(before_turn), {}),
            assembled.current_owner_id,
            prize_owner,
        )
        permission = independent_permission(
            request=request,
            owner_id=assembled.current_owner_id,
            opponent_owner_id=prize_owner,
            signature=signature,
            controls=controls,
            excluded_rows=frozenset(),
        )
        if permission is False:
            store(
                ship_id,
                "permission_denied",
                None,
                prior=prior,
                current_owner=assembled.current_owner_id,
                tminus1_owner=assembled.tminus1_owner_id,
            )
            continue
        if permission is not True:
            store(
                ship_id,
                "unresolved",
                "strict_permission_unresolved",
                prior=prior,
                current_owner=assembled.current_owner_id,
                tminus1_owner=assembled.tminus1_owner_id,
            )
            continue

        disposition, reason = pair_disposition(
            game_id=int(game_id),
            before_turn=int(before_turn),
            prize_id=prize_ship_id,
            prize_owner=prize_owner,
            prize_race=prize_race,
            prize_hull=prize_hull,
            candidate_id=ship_id,
            candidate_row={"strict_permission": True},
            predictions=predictions,
            start_stacks=start_stacks,
        )
        store(
            ship_id,
            disposition,
            reason,
            prior=prior,
            current_owner=assembled.current_owner_id,
            tminus1_owner=assembled.tminus1_owner_id,
        )

    return CaptureCandidateAdapterResult(
        candidate_states=states,
        diagnostics={
            "candidate_states": details,
            "diplomacy_target_turn": int(battle_turn),
            "diplomacy_controls_through_vcr_id": through_vcr_id,
            "diplomacy_future_same_turn_rows_excluded": True,
        },
    )


def build_parent_standard_pair_inputs(
    *,
    state: SiteCombatState,
    context: Mapping[str, Any],
    target_battle_turn: int,
    through_vcr_id: int,
    requests_combat: Callable[[Mapping[str, Any], int], bool],
    relation_signature: Callable[[Mapping[Any, Any], int, int], Any],
    independent_permission: Callable[..., bool | None],
    interference_state: Callable[..., bool | None],
    candidate_input: Callable[..., ShipCombatSideInput],
    decide_pair: Callable[..., Any] = decide_ship_combat_pair,
) -> ParentStandardInputAdapterResult:
    """Build parent STANDARD pair inputs from carried membership and T-1 orders."""

    predictions = context.get("predictions")
    relations = context.get("relations")
    controls_raw = context.get("controls")
    start_stacks = context.get("start_stacks")
    before_turn = context.get("before_turn")
    game_id = context.get("game_id")
    if (
        not isinstance(predictions, Mapping)
        or not isinstance(relations, Mapping)
        or not isinstance(controls_raw, Mapping)
        or not isinstance(start_stacks, Mapping)
        or isinstance(before_turn, bool)
        or not isinstance(before_turn, int)
        or isinstance(game_id, bool)
        or not isinstance(game_id, int)
    ):
        raise EvidenceInputUnresolved("parent_queue_site_context_incomplete")

    controls = filter_diplomacy_controls_through_vcr(
        controls_raw,
        target_battle_turn=target_battle_turn,
        through_vcr_id=through_vcr_id,
    )

    rows: dict[int, CurrentOwnerTMinus1OrderContext] = {}
    active_parent_ids = sorted(parent_queue_active_ship_ids(state))
    for ship_id in active_parent_ids:
        assembled = assemble_current_owner_tminus1_order_context(
            state=state,
            predictions=predictions,
            ship_id=ship_id,
        )
        if assembled.current_owner_id != assembled.tminus1_owner_id:
            raise EvidenceInputUnresolved(
                f"ship {ship_id}: current owner differs from T-1 owner"
            )
        rows[ship_id] = assembled

    inputs: list[InitialStandardPairInput] = []
    diagnostics: dict[str, Any] = {
        "active_parent_ship_ids": active_parent_ids,
        "pair_rows": [],
        "diplomacy_target_turn": target_battle_turn,
        "diplomacy_controls_through_vcr_id": through_vcr_id,
        "diplomacy_future_same_turn_rows_excluded": True,
        "owner_order_context": {
            str(ship_id): {
                "current_owner_id": row.current_owner_id,
                "tminus1_owner_id": row.tminus1_owner_id,
            }
            for ship_id, row in sorted(rows.items())
        },
    }

    for a_id, b_id in combinations(sorted(rows), 2):
        a = rows[a_id]
        b = rows[b_id]
        a_owner = a.current_owner_id
        b_owner = b.current_owner_id
        if a_owner == b_owner:
            continue

        signature = relation_signature(
            relations.get(int(before_turn), {}),
            a_owner,
            b_owner,
        )
        a_request = requests_combat(a.raw, b_owner)
        b_request = requests_combat(b.raw, a_owner)

        a_permission = independent_permission(
            request=a_request,
            owner_id=a_owner,
            opponent_owner_id=b_owner,
            signature=signature,
            controls=controls,
            excluded_rows=frozenset(),
        )
        b_permission = independent_permission(
            request=b_request,
            owner_id=b_owner,
            opponent_owner_id=a_owner,
            signature=signature,
            controls=controls,
            excluded_rows=frozenset(),
        )

        a_interference = interference_state(
            game_id=int(game_id),
            before_turn=int(before_turn),
            owner_id=a_owner,
            raw=a.raw,
            start_stacks=start_stacks,
        )
        b_interference = interference_state(
            game_id=int(game_id),
            before_turn=int(before_turn),
            owner_id=b_owner,
            raw=b.raw,
            start_stacks=start_stacks,
        )

        a_side = candidate_input(
            game_id=int(game_id),
            ship_id=a_id,
            owner_id=a_owner,
            raw=a.raw,
            race_id=a.prediction.get("race_id"),
            hull_id=a.prediction.get("hull_id"),
            hull_can_cloak=a.prediction.get("hull_can_cloak"),
            diplomacy_allows_attack=a_permission,
            interference_protected=a_interference,
        )
        b_side = candidate_input(
            game_id=int(game_id),
            ship_id=b_id,
            owner_id=b_owner,
            raw=b.raw,
            race_id=b.prediction.get("race_id"),
            hull_id=b.prediction.get("hull_id"),
            hull_can_cloak=b.prediction.get("hull_can_cloak"),
            diplomacy_allows_attack=b_permission,
            interference_protected=b_interference,
        )

        decision = decide_pair(
            left=a_side,
            right=b_side,
            same_location=True,
        )
        inputs.append(
            InitialStandardPairInput(
                left=a_side,
                right=b_side,
                decision=decision,
            )
        )
        diagnostics["pair_rows"].append(
            {
                "pair": [a_id, b_id],
                "owners": [a_owner, b_owner],
                "requests": [a_request, b_request],
                "permissions": [a_permission, b_permission],
                "engagement_eligible": decision.engagement_eligible,
                "phase": decision.phase,
                "prestandard_kind": decision.prestandard_kind,
            }
        )

    return ParentStandardInputAdapterResult(
        pair_inputs=tuple(inputs),
        diagnostics=diagnostics,
    )


@dataclass(frozen=True, slots=True)
class PotentialTMinus1SiteArrival:
    """Evidence of *possible*, not proven, arrival at a known current site."""

    ship_id: int
    owner_id: int
    position_source: str
    start_at_site: bool
    waypoint_at_site: bool


def potential_tminus1_site_arrivals(
    *,
    predictions: Mapping[int, Mapping[str, Any]],
    active_ships: Mapping[int, Mapping[str, Any]],
    site: tuple[int, int],
    previously_removed_ship_ids: frozenset[int] = frozenset(),
) -> tuple[PotentialTMinus1SiteArrival, ...]:
    """Find unresolved T-1 movement that can invalidate parent NO_PAIR.

    This is a conservative *uncertainty* index, not position prediction:
    an unknown-position ship whose archived start or destination equals
    the site might compete with a carried active ship. No factual future
    VCR, combat result, or competitor identity is admitted as an input.

    Requests/diplomacy/priority are not evaluated; these records can
    prevent us from proving site exhaustion, never create a pair.
    """
    if (
        not isinstance(site, tuple)
        or len(site) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in site)
    ):
        raise EvidenceInputUnresolved("current_site_coordinates_unavailable")
    if not isinstance(predictions, Mapping) or not isinstance(active_ships, Mapping):
        raise EvidenceInputUnresolved("T-1 arrival index unavailable")
    active_owners = {
        _positive_int(ship.get("owner_id"))
        for ship in active_ships.values()
        if isinstance(ship, Mapping)
    }
    active_owners.discard(None)
    candidates: list[PotentialTMinus1SiteArrival] = []
    for ship_id, prediction in sorted(predictions.items()):
        if (
            _positive_int(ship_id) is None
            or ship_id in active_ships
            or ship_id in previously_removed_ship_ids
            or not isinstance(prediction, Mapping)
            or prediction.get("position") is not None
        ):
            continue
        raw = prediction.get("raw")
        owner_id = _positive_int(prediction.get("owner_id"))
        if (
            not isinstance(raw, Mapping)
            or owner_id is None
            or _positive_int(raw.get("id")) != ship_id
            or _positive_int(raw.get("ownerid")) != owner_id
            or _positive_int(prediction.get("hull_id")) is None
            or _positive_int(prediction.get("race_id")) in (None, 12)
        ):
            continue
        start = (raw.get("x"), raw.get("y"))
        target = (raw.get("targetx"), raw.get("targety"))
        at_start = (
            all(isinstance(v, int) and not isinstance(v, bool) for v in start)
            and start == site
        )
        at_target = (
            all(isinstance(v, int) and not isinstance(v, bool) for v in target)
            and target == site
        )
        if not at_start and not at_target:
            continue
        candidates.append(
            PotentialTMinus1SiteArrival(
                ship_id=ship_id,
                owner_id=owner_id,
                position_source=str(prediction.get("source", "unknown")),
                start_at_site=at_start,
                waypoint_at_site=at_target,
            )
        )
    owners = {row.owner_id for row in candidates}
    if active_owners:
        return tuple(row for row in candidates if any(
            row.owner_id != owner for owner in active_owners
        ))
    return tuple(candidates) if len(owners) >= 2 else ()
