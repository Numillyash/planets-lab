"""Evidence-scoped precombat effective-state helpers.

This module contains only narrow state reconstructions that have passed a
historical differential.  It deliberately does not wire those states into the
canonical pair selector; queue/selection composition remains a separate gate.

Unknown or out-of-scope inputs fail closed to ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass


PRIVATEER_RACE_ID = 5
ROB_SHIP_MISSION_ID = 9


@dataclass(frozen=True, slots=True)
class EffectiveCloakState:
    """Tri-state effective-cloak reconstruction with an attribution label."""

    effective_cloak: bool | None
    reason: str


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
    (Rob Ship), cloak-capable *ordinary-cloak* hulls.  Archived prior
    ``iscloaked=true`` is combat-effective only with fuel strictly greater than
    the ordinary cloak reference cost.  Equality and below are not effective.

    This is intentionally not a universal cloak mechanic.  Advanced Cloak,
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
