"""Evidence-scoped precombat effective-state helpers.

This module contains only narrow state reconstructions that have passed a
historical differential. It deliberately does not inspect post-Host state,
VCR outcomes or Host messages and does not build combat queues.

Unknown or out-of-scope inputs fail closed to ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass


PRIVATEER_RACE_ID = 5
BIRD_RACE_ID = 3
ROB_SHIP_MISSION_ID = 9
BIRD_SUPER_SPY_MISSION_ID = 9


@dataclass(frozen=True, slots=True)
class EffectiveCloakState:
    """Tri-state effective-cloak reconstruction with an attribution label."""

    effective_cloak: bool | None
    reason: str


@dataclass(frozen=True, slots=True)
class StandardTargetabilityState:
    """Tri-state ordinary-STANDARD targetability derived from effective cloak."""

    targetable_by_opponent: bool | None
    reason: str


def standard_targetability_from_effective_cloak(
    state: EffectiveCloakState,
) -> StandardTargetabilityState:
    """Map scoped effective cloak to incoming ordinary-STANDARD targetability.

    This is a directional combat-input projection, not a universal cloak rule.
    Callers must first identify an evidence-supported potentially-cloaked branch
    and reconstruct that branch's effective state. ``None`` remains unresolved.
    """

    if state.effective_cloak is True:
        return StandardTargetabilityState(False, f"effective_cloak:{state.reason}")
    if state.effective_cloak is False:
        return StandardTargetabilityState(True, f"not_effectively_cloaked:{state.reason}")
    return StandardTargetabilityState(None, f"effective_cloak_unresolved:{state.reason}")


def privateer_rob_ordinary_cloak_state(
    *,
    race_id: int | None,
    mission: int | None,
    hull_can_cloak: bool | None,
    prior_iscloaked: bool | None,
    fuel: int | None,
    ordinary_cloak_reference_cost: int | None,
    advanced_cloak: bool | None,
) -> EffectiveCloakState:
    """Reconstruct the tested ordinary-cloak Privateer Rob state.

    Evidence scope (historical NuHost corpus, C5): Privateer race 5, mission 9
    (Rob Ship), cloak-capable *ordinary-cloak* hulls. Archived prior
    ``iscloaked=true`` is combat-effective only with fuel strictly greater than
    the ordinary cloak reference cost. Equality and below are not effective.

    This is intentionally not a universal cloak mechanic. Advanced Cloak,
    other races/missions and unresolved inputs return ``None`` rather than an
    invented default.
    """

    if race_id != PRIVATEER_RACE_ID:
        return EffectiveCloakState(None, "outside_privateer_scope")
    if mission != ROB_SHIP_MISSION_ID:
        return EffectiveCloakState(None, "outside_rob_mission_scope")
    if hull_can_cloak is not True:
        return EffectiveCloakState(None, "cloak_capability_unresolved_or_false")

    if prior_iscloaked is False:
        return EffectiveCloakState(False, "prior_false")
    if prior_iscloaked is not True:
        return EffectiveCloakState(None, "prior_cloak_unresolved")

    if advanced_cloak is True:
        return EffectiveCloakState(None, "advanced_cloak_unresolved")
    if advanced_cloak is None:
        return EffectiveCloakState(None, "cloak_type_unresolved")

    if fuel is None or ordinary_cloak_reference_cost is None:
        return EffectiveCloakState(None, "fuel_or_reference_cost_unresolved")
    if fuel < 0 or ordinary_cloak_reference_cost < 0:
        return EffectiveCloakState(None, "invalid_fuel_or_reference_cost")

    if fuel <= ordinary_cloak_reference_cost:
        return EffectiveCloakState(
            False,
            "ordinary_prior_true_at_or_below_reference_cost",
        )
    return EffectiveCloakState(
        True,
        "ordinary_prior_true_above_reference_cost",
    )


def bird_super_spy_ordinary_cloak_state(
    *,
    race_id: int | None,
    mission: int | None,
    hull_can_cloak: bool | None,
    advanced_cloak: bool | None,
    damage: int | None,
    fuel_before: int | None,
    ordinary_cloak_reference_cost: int | None,
    reference_move_resolved: bool,
    reference_remaining_fuel: int | None,
    prior_iscloaked: bool | None,
    ion_start_inside: bool | None,
    planet_ion_pulse_possible: bool | None,
    loki_start_exposed: bool | None,
    active_glory_colocated: bool,
) -> EffectiveCloakState:
    """Reconstruct the supported ordinary-cloak Bird Super Spy state.

    This is the production form of the documented/corpus-tested C5 candidate
    previously used by the Bird population diagnostic. The helper intentionally
    requires conservative positive evidence before returning effective cloak:

    - Bird race and Super Spy mission;
    - cloak-capable, non-Advanced-Cloak hull;
    - no existing damage;
    - positive prior cloak observation;
    - fuel safely above the ordinary reference cost before movement;
    - independently resolved reference movement with fuel still safely above the
      reference cost;
    - no visible ion-storm, possible Super-Spy ion-pulse, Loki or active Glory
      decloak context.

    The helper does not consume post-Host ``T`` state, VCR results or Host
    messages. Advanced Cloak remains unresolved until its dynamic precombat
    state is independently reconstructible.
    """

    if race_id != BIRD_RACE_ID:
        return EffectiveCloakState(None, "outside_bird_scope")
    if mission != BIRD_SUPER_SPY_MISSION_ID:
        return EffectiveCloakState(None, "outside_super_spy_scope")
    if hull_can_cloak is not True:
        return EffectiveCloakState(None, "cloak_capability_unresolved_or_false")

    if advanced_cloak is True:
        return EffectiveCloakState(None, "advanced_cloak_unresolved")
    if advanced_cloak is not False:
        return EffectiveCloakState(None, "cloak_type_unresolved")

    if damage is None:
        return EffectiveCloakState(None, "damage_unresolved")
    if damage < 0:
        return EffectiveCloakState(None, "invalid_damage")
    if damage > 0:
        return EffectiveCloakState(False, "damage_blocks_cloak")

    # The population gate intentionally required a positive archived prior-cloak
    # observation rather than assuming Super Spy alone proves this turn's active
    # cloak state.
    if prior_iscloaked is not True:
        return EffectiveCloakState(None, "prior_cloak_not_positive")

    if fuel_before is None or ordinary_cloak_reference_cost is None:
        return EffectiveCloakState(None, "fuel_or_reference_unresolved")
    if fuel_before < 0 or ordinary_cloak_reference_cost < 0:
        return EffectiveCloakState(None, "invalid_fuel_or_reference_cost")
    if fuel_before <= ordinary_cloak_reference_cost:
        return EffectiveCloakState(False, "fuel_not_safely_above_reference_cost")

    if reference_move_resolved is not True or reference_remaining_fuel is None:
        return EffectiveCloakState(None, "reference_move_fuel_unresolved")
    if reference_remaining_fuel < 0:
        return EffectiveCloakState(None, "invalid_reference_remaining_fuel")
    if reference_remaining_fuel <= ordinary_cloak_reference_cost:
        return EffectiveCloakState(None, "post_move_fuel_margin_not_positive")

    if ion_start_inside is None:
        return EffectiveCloakState(None, "ion_storm_context_unresolved")
    if ion_start_inside:
        return EffectiveCloakState(None, "ion_storm_context_present")

    if planet_ion_pulse_possible is None:
        return EffectiveCloakState(None, "planet_ion_pulse_context_unresolved")
    if planet_ion_pulse_possible:
        return EffectiveCloakState(None, "planet_ion_pulse_possible")

    if loki_start_exposed is None:
        return EffectiveCloakState(None, "loki_context_unresolved")
    if loki_start_exposed:
        return EffectiveCloakState(None, "loki_context_present")

    if active_glory_colocated:
        return EffectiveCloakState(None, "active_glory_context_present")

    return EffectiveCloakState(
        True,
        "documented_super_spy_ordinary_cloak_supported",
    )
