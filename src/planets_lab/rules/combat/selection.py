"""Fail-closed ship-vs-ship Host pair decision composition.

This module sits above the narrow order/eligibility primitives and below a
future stack-level Host queue. It decides only what can be established for one
already-identified pair: whether the pair may engage, whether a documented
pre-standard phase applies, and any attributable left/right assignment.

Dynamic Host facts which are not yet reconstructed globally (directed
Diplomacy/Safe Passage, Intercept Interference protection, active cloak state at
the Intercept step, ordinary-STANDARD directional targetability, effective
advantage enablement and era-dependent C&I hull eligibility) are explicit
inputs. ``None`` is preserved rather than silently replaced by a default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .eligibility import (
    harmonic_weapon_modulation_applies,
    matching_ship_friendly_code_blocks_combat,
)
from .order import (
    CLOAK_INTERCEPT_MISSION_ID,
    INTERCEPT_MISSION_ID,
    cloak_intercept_order_signature,
    galactic_power_forces_left,
    orders_request_ship_combat,
    priority_intercept_order_signature,
    priority_intercept_reciprocal_target_signature,
    standard_battle_priority_key,
)


class ShipCombatPairPhase(str, Enum):
    PRIORITY_INTERCEPT = "priority_intercept"
    CLOAK_INTERCEPT = "cloak_intercept"
    STANDARD = "standard"


class ShipCombatPrestandardKind(str, Enum):
    NORMAL_PRIORITY_INTERCEPT = "normal_priority_intercept"
    RECIPROCAL_PRIORITY_INTERCEPT = "reciprocal_priority_intercept"
    CLOAK_AND_INTERCEPT = "cloak_and_intercept"


@dataclass(frozen=True, slots=True)
class ShipCombatSideInput:
    """Mechanical and resolved dynamic inputs for one ship in a pair."""

    ship_id: int
    owner_id: int
    race_id: int | None = None
    hull_id: int | None = None
    mission: int | None = None
    mission_target_id: int | None = None
    primary_enemy: int | None = None
    friendly_code: Any = None
    hull_can_cloak: bool | None = None

    # Dynamic pair/turn facts. These are intentionally tri-state.
    has_fuel: bool | None = None
    diplomacy_allows_attack: bool | None = None
    harmonic_weapon_modulation_enabled: bool | None = None
    cloak_and_intercept_enabled: bool | None = None
    cloak_and_intercept_hull_eligible: bool | None = None
    active_cloak_at_intercept: bool | None = None
    intercept_interference_protected: bool | None = None
    galactic_power_enabled: bool | None = None

    # Pair-specific fact for ordinary STANDARD combat only: whether this ship
    # can be selected as the target of the opponent's directed attack request.
    # It is deliberately not consulted by PIA/C&I. Ordinary callers default to
    # targetable; upstream potentially-cloaked branches must explicitly supply
    # False or None after reconstructing their dynamic precombat state.
    standard_targetable_by_opponent: bool | None = True

    def __post_init__(self) -> None:
        if (
            isinstance(self.ship_id, bool)
            or not isinstance(self.ship_id, int)
            or self.ship_id <= 0
        ):
            raise ValueError("ship_id must be a positive integer")
        if (
            isinstance(self.owner_id, bool)
            or not isinstance(self.owner_id, int)
            or self.owner_id <= 0
        ):
            raise ValueError("owner_id must be a positive integer")


@dataclass(frozen=True, slots=True)
class ShipCombatPairDecision:
    """Bounded result for one candidate ship-vs-ship pair."""

    engagement_eligible: bool | None
    matching_fc_blocks: bool | None
    left_hwm_applies: bool | None
    right_hwm_applies: bool | None
    phase: ShipCombatPairPhase | None
    prestandard_kind: ShipCombatPrestandardKind | None
    phase_attacker_ship_id: int | None
    left_ship_id: int | None
    right_ship_id: int | None
    unresolved_reasons: tuple[str, ...] = ()


def _effective_attack_request(
    side: ShipCombatSideInput,
    *,
    opponent_owner_id: int,
) -> bool | None:
    requested = orders_request_ship_combat(
        mission=side.mission,
        primary_enemy=side.primary_enemy,
        opponent_owner_id=opponent_owner_id,
    )
    if not requested:
        return False
    if side.diplomacy_allows_attack is None:
        return None
    return bool(side.diplomacy_allows_attack)


def _base_engagement(
    *,
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
    same_location: bool | None,
    matching_fc_blocks: bool | None,
) -> tuple[bool | None, tuple[str, ...], bool | None, bool | None]:
    if left.owner_id == right.owner_id:
        return False, ("same_owner",), False, False

    left_request = _effective_attack_request(left, opponent_owner_id=right.owner_id)
    right_request = _effective_attack_request(right, opponent_owner_id=left.owner_id)

    blockers: list[str] = []
    unknown: list[str] = []

    if same_location is False:
        blockers.append("different_location")
    elif same_location is None:
        unknown.append("same_location_unknown")

    for label, value in (("left_fuel", left.has_fuel), ("right_fuel", right.has_fuel)):
        if value is False:
            blockers.append(f"{label}_absent")
        elif value is None:
            unknown.append(f"{label}_unknown")

    if matching_fc_blocks is True:
        blockers.append("matching_friendly_code")
    elif matching_fc_blocks is None:
        unknown.append("matching_friendly_code_state_unknown")

    if left_request is not True and right_request is not True:
        if left_request is False and right_request is False:
            blockers.append("no_combat_request")
        else:
            unknown.append("directed_combat_request_unknown")

    if blockers:
        return False, tuple(blockers), left_request, right_request
    if unknown:
        return None, tuple(unknown), left_request, right_request
    return True, (), left_request, right_request


def _standard_request_after_targetability(
    *,
    request: bool | None,
    targetable: bool | None,
) -> bool | None:
    """Filter one directed ordinary-STANDARD request by its target state.

    A known non-targetable target wins even when the directed request itself is
    unresolved. Conversely, a known absent request never depends on targetability.
    This helper is intentionally unused by pre-standard PIA/C&I classification.
    """

    if targetable is False:
        return False
    if request is False:
        return False
    if request is None:
        return None
    if targetable is None:
        return None
    return True


def _standard_targetability_reasons(
    *,
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
    left_request: bool | None,
    right_request: bool | None,
    left_standard_request: bool | None,
    right_standard_request: bool | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if left_standard_request is None:
        if left_request is None:
            reasons.append("left_standard_attack_request_unknown")
        elif right.standard_targetable_by_opponent is None:
            reasons.append("right_standard_targetability_unknown")
    if right_standard_request is None:
        if right_request is None:
            reasons.append("right_standard_attack_request_unknown")
        elif left.standard_targetable_by_opponent is None:
            reasons.append("left_standard_targetability_unknown")
    return tuple(reasons)


def _normal_pia_candidate(
    *,
    interceptor: ShipCombatSideInput,
    target: ShipCombatSideInput,
    interceptor_attack_request: bool | None,
) -> tuple[bool | None, str | None]:
    signature = priority_intercept_order_signature(
        mission=interceptor.mission,
        mission_target_id=interceptor.mission_target_id,
        primary_enemy=interceptor.primary_enemy,
        target_owner_id=target.owner_id,
        hull_can_cloak=interceptor.hull_can_cloak,
    )
    if signature is False:
        return False, None
    if signature is None:
        return None, "normal_pia_signature_unknown"

    # PIA priority is attached to the actual intercepted target, not merely any
    # ship owned by the target faction. A mission-7 ship may later fight another
    # hostile ship at the same location in ordinary combat, but that pair is not
    # the documented Priority Intercept pair.
    if interceptor.mission_target_id != target.ship_id:
        return False, None

    # Normal PIA is the interceptor-initiated branch. If directed diplomacy
    # blocks that attack, the target may still create the reciprocal branch.
    if interceptor_attack_request is False:
        return False, None
    if interceptor_attack_request is None:
        return None, "normal_pia_directed_attack_unknown"

    # Intercept Interference keeps normal Intercept movement but removes PIA
    # combat priority.
    if target.intercept_interference_protected is True:
        return False, None
    if target.intercept_interference_protected is None:
        return None, "normal_pia_interference_unknown"
    return True, None


def _reciprocal_pia_candidate(
    *,
    interceptor: ShipCombatSideInput,
    target: ShipCombatSideInput,
    target_attack_request: bool | None,
) -> tuple[bool | None, str | None]:
    signature = priority_intercept_reciprocal_target_signature(
        interceptor_mission=interceptor.mission,
        interceptor_target_id=interceptor.mission_target_id,
        interceptor_hull_can_cloak=interceptor.hull_can_cloak,
        target_ship_id=target.ship_id,
        target_would_combat_interceptor=target_attack_request,
    )
    if signature is False:
        return False, None
    if signature is None:
        return None, "reciprocal_pia_signature_unknown"

    if target.intercept_interference_protected is True:
        return False, None
    if target.intercept_interference_protected is None:
        return None, "reciprocal_pia_interference_unknown"
    return True, None


def _c_and_i_candidate(
    *,
    interceptor: ShipCombatSideInput,
    target: ShipCombatSideInput,
    interceptor_attack_request: bool | None,
) -> tuple[bool | None, str | None]:
    signature = cloak_intercept_order_signature(
        mission=interceptor.mission,
        owner_race_id=interceptor.race_id,
        mission_target_id=interceptor.mission_target_id,
        primary_enemy=interceptor.primary_enemy,
        target_owner_id=target.owner_id,
        hull_can_cloak=interceptor.hull_can_cloak,
    )
    if signature is False:
        return False, None
    if signature is None:
        return None, "cloak_intercept_signature_unknown"

    if interceptor.cloak_and_intercept_enabled is False:
        return False, None
    if interceptor.cloak_and_intercept_enabled is None:
        return None, "cloak_intercept_advantage_unknown"

    # In games after 2021 C&I only affects hulls buildable by the Birds. Keep
    # this era/static-catalog fact external rather than assuming every captured
    # cloak-capable hull is eligible.
    if interceptor.cloak_and_intercept_hull_eligible is False:
        return False, None
    if interceptor.cloak_and_intercept_hull_eligible is None:
        return None, "cloak_intercept_hull_eligibility_unknown"

    # The mission page requires the ship to retain its active cloak until the
    # Intercept step; hull capability alone is insufficient.
    if interceptor.active_cloak_at_intercept is False:
        return False, None
    if interceptor.active_cloak_at_intercept is None:
        return None, "cloak_intercept_active_cloak_unknown"

    if interceptor_attack_request is False:
        return False, None
    if interceptor_attack_request is None:
        return None, "cloak_intercept_directed_attack_unknown"

    # Intercept Interference breaks the C&I intercept lock entirely.
    if target.intercept_interference_protected is True:
        return False, None
    if target.intercept_interference_protected is None:
        return None, "cloak_intercept_interference_unknown"
    return True, None


def _side_prestandard_kind(
    *,
    side: ShipCombatSideInput,
    target: ShipCombatSideInput,
    side_attack_request: bool | None,
    target_attack_request: bool | None,
) -> tuple[ShipCombatPrestandardKind | None, str | None]:
    if side.mission == CLOAK_INTERCEPT_MISSION_ID:
        c_and_i, reason = _c_and_i_candidate(
            interceptor=side,
            target=target,
            interceptor_attack_request=side_attack_request,
        )
        if c_and_i is True:
            return ShipCombatPrestandardKind.CLOAK_AND_INTERCEPT, None
        if c_and_i is None:
            return None, reason
        return None, None

    if side.mission != INTERCEPT_MISSION_ID:
        return None, None

    normal, normal_reason = _normal_pia_candidate(
        interceptor=side,
        target=target,
        interceptor_attack_request=side_attack_request,
    )
    if normal is True:
        # A normal PE-matching PIA subsumes the reciprocal condition if the
        # target also happens to attack the interceptor.
        return ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT, None

    reciprocal, reciprocal_reason = _reciprocal_pia_candidate(
        interceptor=side,
        target=target,
        target_attack_request=target_attack_request,
    )
    if reciprocal is True:
        return ShipCombatPrestandardKind.RECIPROCAL_PRIORITY_INTERCEPT, None

    reasons = [value for value in (normal_reason, reciprocal_reason) if value]
    if reasons:
        return None, ";".join(reasons)
    return None, None


def _standard_side_assignment(
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
) -> tuple[int | None, int | None, str | None]:
    left_key = standard_battle_priority_key(
        ship_id=left.ship_id,
        mission=left.mission,
        primary_enemy=left.primary_enemy,
        friendly_code=left.friendly_code,
    )
    right_key = standard_battle_priority_key(
        ship_id=right.ship_id,
        mission=right.mission,
        primary_enemy=right.primary_enemy,
        friendly_code=right.friendly_code,
    )
    if left_key is None or right_key is None:
        return None, None, "standard_priority_unsupported_friendly_code"
    if left_key < right_key:
        return right.ship_id, left.ship_id, None
    if right_key < left_key:
        return left.ship_id, right.ship_id, None
    return None, None, "standard_priority_tie"


def _apply_galactic_power_side_override(
    *,
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
    base_left_ship_id: int | None,
    base_right_ship_id: int | None,
) -> tuple[int | None, int | None, str | None]:
    left_forced = galactic_power_forces_left(
        owner_race_id=left.race_id,
        hull_id=left.hull_id,
        galactic_power_enabled=left.galactic_power_enabled,
    )
    right_forced = galactic_power_forces_left(
        owner_race_id=right.race_id,
        hull_id=right.hull_id,
        galactic_power_enabled=right.galactic_power_enabled,
    )

    if left_forced is True and right_forced is True:
        return None, None, "dual_galactic_power_forced_left_unresolved"
    if left_forced is True:
        if right_forced is None:
            return None, None, "opponent_galactic_power_state_unknown"
        return left.ship_id, right.ship_id, None
    if right_forced is True:
        if left_forced is None:
            return None, None, "opponent_galactic_power_state_unknown"
        return right.ship_id, left.ship_id, None
    if left_forced is None or right_forced is None:
        return None, None, "galactic_power_state_unknown"
    return base_left_ship_id, base_right_ship_id, None


def decide_ship_combat_pair(
    *,
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
    same_location: bool | None,
) -> ShipCombatPairDecision:
    """Compose known C5 mechanics for one candidate ship-vs-ship pair.

    The function does not build a target list, mutate ships, or resolve combat.
    It is the pure pair-level predicate for a future stack queue. A known blocker
    wins immediately; otherwise unknown dynamic facts remain explicit.
    """

    matching_fc_blocks = matching_ship_friendly_code_blocks_combat(
        left_friendly_code=left.friendly_code,
        right_friendly_code=right.friendly_code,
        left_race_id=left.race_id,
        right_race_id=right.race_id,
        left_harmonic_weapon_modulation_enabled=left.harmonic_weapon_modulation_enabled,
        right_harmonic_weapon_modulation_enabled=right.harmonic_weapon_modulation_enabled,
    )
    left_hwm = harmonic_weapon_modulation_applies(
        bird_race_id=left.race_id,
        harmonic_weapon_modulation_enabled=left.harmonic_weapon_modulation_enabled,
        bird_friendly_code=left.friendly_code,
        opponent_friendly_code=right.friendly_code,
    )
    right_hwm = harmonic_weapon_modulation_applies(
        bird_race_id=right.race_id,
        harmonic_weapon_modulation_enabled=right.harmonic_weapon_modulation_enabled,
        bird_friendly_code=right.friendly_code,
        opponent_friendly_code=left.friendly_code,
    )

    engagement, base_reasons, left_request, right_request = _base_engagement(
        left=left,
        right=right,
        same_location=same_location,
        matching_fc_blocks=matching_fc_blocks,
    )
    if engagement is not True:
        return ShipCombatPairDecision(
            engagement_eligible=engagement,
            matching_fc_blocks=matching_fc_blocks,
            left_hwm_applies=left_hwm,
            right_hwm_applies=right_hwm,
            phase=None,
            prestandard_kind=None,
            phase_attacker_ship_id=None,
            left_ship_id=None,
            right_ship_id=None,
            unresolved_reasons=base_reasons,
        )

    # At least one directed request is known True here. The opposite direction
    # may still be unknown; preserve that tri-state value because it only blocks
    # phase classification when the special branch actually depends on it.
    left_kind, left_reason = _side_prestandard_kind(
        side=left,
        target=right,
        side_attack_request=left_request,
        target_attack_request=right_request,
    )
    right_kind, right_reason = _side_prestandard_kind(
        side=right,
        target=left,
        side_attack_request=right_request,
        target_attack_request=left_request,
    )

    unresolved = tuple(reason for reason in (left_reason, right_reason) if reason)
    if unresolved:
        return ShipCombatPairDecision(
            engagement_eligible=True,
            matching_fc_blocks=matching_fc_blocks,
            left_hwm_applies=left_hwm,
            right_hwm_applies=right_hwm,
            phase=None,
            prestandard_kind=None,
            phase_attacker_ship_id=None,
            left_ship_id=None,
            right_ship_id=None,
            unresolved_reasons=unresolved,
        )

    candidates = [
        (left.ship_id, left_kind),
        (right.ship_id, right_kind),
    ]
    candidates = [(ship_id, kind) for ship_id, kind in candidates if kind is not None]

    phase: ShipCombatPairPhase
    prestandard_kind: ShipCombatPrestandardKind | None = None
    attacker_ship_id: int | None = None
    base_left: int | None
    base_right: int | None
    side_reason: str | None = None

    if not candidates:
        left_standard_request = _standard_request_after_targetability(
            request=left_request,
            targetable=right.standard_targetable_by_opponent,
        )
        right_standard_request = _standard_request_after_targetability(
            request=right_request,
            targetable=left.standard_targetable_by_opponent,
        )
        if left_standard_request is not True and right_standard_request is not True:
            if left_standard_request is False and right_standard_request is False:
                standard_reasons = ("no_standard_combat_request_after_targetability",)
                standard_eligible: bool | None = False
            else:
                standard_reasons = _standard_targetability_reasons(
                    left=left,
                    right=right,
                    left_request=left_request,
                    right_request=right_request,
                    left_standard_request=left_standard_request,
                    right_standard_request=right_standard_request,
                )
                if not standard_reasons:
                    standard_reasons = ("standard_targetability_or_request_unknown",)
                standard_eligible = None
            return ShipCombatPairDecision(
                engagement_eligible=standard_eligible,
                matching_fc_blocks=matching_fc_blocks,
                left_hwm_applies=left_hwm,
                right_hwm_applies=right_hwm,
                phase=None,
                prestandard_kind=None,
                phase_attacker_ship_id=None,
                left_ship_id=None,
                right_ship_id=None,
                unresolved_reasons=standard_reasons,
            )

        phase = ShipCombatPairPhase.STANDARD
        base_left, base_right, side_reason = _standard_side_assignment(left, right)
    elif len(candidates) == 1:
        attacker_ship_id, prestandard_kind = candidates[0]
        opponent_ship_id = right.ship_id if attacker_ship_id == left.ship_id else left.ship_id
        if prestandard_kind is ShipCombatPrestandardKind.CLOAK_AND_INTERCEPT:
            phase = ShipCombatPairPhase.CLOAK_INTERCEPT
            # Ordinary factual C5 corpus: 7/7 isolated C&I attackers are right.
            base_left, base_right = opponent_ship_id, attacker_ship_id
        elif prestandard_kind is ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT:
            phase = ShipCombatPairPhase.PRIORITY_INTERCEPT
            # Ordinary linked normal-PIA corpus: 37/37 attackers are right.
            base_left, base_right = opponent_ship_id, attacker_ship_id
        else:
            phase = ShipCombatPairPhase.PRIORITY_INTERCEPT
            # Reciprocal-only population currently contains one historical row;
            # do not promote a universal reciprocal-specific side rule.
            base_left = None
            base_right = None
            side_reason = "reciprocal_priority_intercept_side_unverified"
    else:
        kinds = {kind for _ship_id, kind in candidates}
        if kinds == {ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT}:
            # PIA documentation specifies reverse Ship ID order when multiple
            # cloakable vessels perform Priority Intercept Attacks.
            attacker_ship_id = max(ship_id for ship_id, _kind in candidates)
            prestandard_kind = ShipCombatPrestandardKind.NORMAL_PRIORITY_INTERCEPT
            phase = ShipCombatPairPhase.PRIORITY_INTERCEPT
            opponent_ship_id = right.ship_id if attacker_ship_id == left.ship_id else left.ship_id
            base_left, base_right = opponent_ship_id, attacker_ship_id
        else:
            return ShipCombatPairDecision(
                engagement_eligible=True,
                matching_fc_blocks=matching_fc_blocks,
                left_hwm_applies=left_hwm,
                right_hwm_applies=right_hwm,
                phase=None,
                prestandard_kind=None,
                phase_attacker_ship_id=None,
                left_ship_id=None,
                right_ship_id=None,
                unresolved_reasons=("mixed_prestandard_candidates_unresolved",),
            )

    final_left, final_right, galactic_reason = _apply_galactic_power_side_override(
        left=left,
        right=right,
        base_left_ship_id=base_left,
        base_right_ship_id=base_right,
    )
    reasons = tuple(reason for reason in (side_reason, galactic_reason) if reason)

    return ShipCombatPairDecision(
        engagement_eligible=True,
        matching_fc_blocks=matching_fc_blocks,
        left_hwm_applies=left_hwm,
        right_hwm_applies=right_hwm,
        phase=phase,
        prestandard_kind=prestandard_kind,
        phase_attacker_ship_id=attacker_ship_id,
        left_ship_id=final_left,
        right_ship_id=final_right,
        unresolved_reasons=reasons,
    )