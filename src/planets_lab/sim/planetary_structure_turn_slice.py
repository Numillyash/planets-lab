"""Research-only explicit planetary construction with conditional phase placement.

This module composes the documented standard-target priority builder with
the EXISTING unchanged fourteen-phase PlanetaryHostPipeline, using two
clearly hypothetical placements relative to the entire economy block.

Construction targets are separate from PlayerOrders and owner-signed V1/V2
records. Treating them as authenticated or Host-accepted orders would be
incorrect. Complete explicit per-player scope must be asserted; a missing
owner is never silently converted into "no orders".

No move/combat/ship/starbase/campaign paths. No Host phase position or
NuHost execution can become independently verified from a local replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Mapping, Literal

from planets_lab.core import GameState
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_structure_build import (
    StructureBuildTargets,
    forecast_priority_structure_build,
)

STRUCTURE_PLACEMENTS = ("structures_before_planetary", "structures_after_planetary")
TURN_STATUS = "CONDITIONAL_STRUCTURE_AND_ECONOMY_TURN_NOT_NUHOST_VERIFIED"


class UnsupportedStructureTurn(RuntimeError):
    """Fail closed without returning partially simulated state."""


@dataclass(slots=True)
class _ExplicitStructurePhase:
    targets_by_player: Mapping[int, tuple[StructureBuildTargets, ...]]
    automatic_supply_sale_enabled: bool
    name: str = field(init=False, default="standard_structure_build_conditional")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        result: list[HostEvent] = []
        for owner_id in sorted(self.targets_by_player):
            for target in sorted(
                self.targets_by_player[owner_id], key=lambda row: row.planet_id
            ):
                planet = state.planets[target.planet_id]
                forecast = forecast_priority_structure_build(
                    planet, target, standard_rules_asserted=True,
                    automatic_supply_sale_enabled=self.automatic_supply_sale_enabled,
                )
                if not forecast.supported or forecast.resulting_planet is None:
                    raise UnsupportedStructureTurn("invalid or unsupported structure phase")
                state.planets[planet.id] = forecast.resulting_planet
                result.append(HostEvent(
                    phase=self.name,
                    kind="conditional_structure_target_partially_executed"
                         if forecast.unbuilt and any(v for _, v in forecast.unbuilt)
                         or forecast.capped_by_population
                         else "conditional_structure_target_satisfied",
                    entity_type="planet", entity_id=target.planet_id,
                    details=(
                        ("built", str(sum(n for _, n in forecast.built))),
                        ("unbuilt", str(sum(n for _, n in forecast.unbuilt))),
                        ("supplies_for_building", str(forecast.supplies_used_for_building)),
                        ("supplies_sold", str(forecast.supplies_sold_for_mc)),
                        ("mc_spent", str(forecast.megacredits_spent_on_building)),
                        # Per-family figures enable an independent multi-turn
                        # structure ledger (including population-driven decay).
                        ("built_defense_posts", str(dict(forecast.built).get("defense_posts", 0))),
                        ("built_factories", str(dict(forecast.built).get("factories", 0))),
                        ("built_mines", str(dict(forecast.built).get("mines", 0))),
                        ("capped_types", str(len(forecast.capped_by_population))),
                    ),
                    message="locally asserted standard structure targets, not authenticated Host orders",
                ))
        return result


@dataclass(frozen=True, slots=True)
class ConditionalStructureTurn:
    status: str
    placement: str | None = None
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    order_source: str = "CALLER_ASSERTED_STRUCTURE_TARGETS_NOT_SERVER_VERIFIED"
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == TURN_STATUS


def simulate_explicit_structure_turn(
    before: GameState,
    targets_by_player: Mapping[int, tuple[StructureBuildTargets, ...]],
    *,
    placement: Literal["structures_before_planetary", "structures_after_planetary"],
    standard_rules_asserted: bool = False,
    complete_structure_target_scope_asserted: bool = False,
    automatic_supply_sale_enabled: bool = False,
    seed: int = 0,
) -> ConditionalStructureTurn:
    def abstain(reason: str) -> ConditionalStructureTurn:
        return ConditionalStructureTurn("ABSTAIN_STRUCTURE_TURN", reason=reason)

    if standard_rules_asserted is not True or complete_structure_target_scope_asserted is not True:
        return abstain("standard rules and complete target scope must both be asserted")
    if placement not in STRUCTURE_PLACEMENTS:
        return abstain("explicit supported structure phase placement required")
    if type(automatic_supply_sale_enabled) is not bool or type(seed) is not int:
        return abstain("unsupported option value")
    if type(before) is not GameState:
        return abstain("complete GameState required")
    try:
        before.validate()
    except (ValueError, TypeError, AttributeError):
        return abstain("invalid input state")
    if (before.ships or before.starbases or before.ion_storms
            or before.metadata.get("no_supplies") is True):
        return abstain("ship/base/storm or special-game interactions not modeled")
    if (type(targets_by_player) is not dict
            or set(targets_by_player) != set(before.players)):
        return abstain("explicit targets required for every declared player")
    any_target = False
    seen_planets: set[int] = set()
    for owner_id, targets in targets_by_player.items():
        if type(owner_id) is not int or type(targets) is not tuple:
            return abstain("invalid target/owner record")
        for target in targets:
            if type(target) is not StructureBuildTargets:
                return abstain("unexpected construction target type")
            if (type(target.planet_id) is not int or
                    target.planet_id in seen_planets):
                return abstain("duplicate or invalid target planet identity")
            seen_planets.add(target.planet_id)
            planet = before.planets.get(target.planet_id)
            if planet is None or planet.owner_id != owner_id:
                return abstain("target missing or owned by another player")
            any_target = True
    if not any_target:
        return abstain("no explicit building targets")

    # Empty ordinary TurnOrders: construction is deliberately NOT smuggled
    # through legacy owner-signed cargo/technology observation schemas.
    placeholder = TurnOrders(by_player={
        pid: PlayerOrders(player_id=pid) for pid in sorted(before.players)
    })
    structure = _ExplicitStructurePhase(
        targets_by_player=targets_by_player,
        automatic_supply_sale_enabled=automatic_supply_sale_enabled,
    )
    planet_phases = PlanetaryHostPipeline().phases
    phases = (
        (structure, *planet_phases)
        if placement == STRUCTURE_PLACEMENTS[0]
        else (*planet_phases, structure)
    )
    try:
        after, events = HostEngine(phases).step(before, placeholder, seed=seed)
    except (UnsupportedStructureTurn, UnsupportedPopulationRule,
            ValueError, TypeError, OverflowError, AttributeError, KeyError):
        return abstain("unsupported synthetic economy or target execution")
    return ConditionalStructureTurn(
        TURN_STATUS, placement=placement, state=after, events=events,
    )


@dataclass(frozen=True, slots=True)
class StructurePlacementComparison:
    status: str
    before: ConditionalStructureTurn
    after: ConditionalStructureTurn
    observationally_distinct_final_states: bool = False
    nuhost_phase_placement_verified: bool = False


def compare_structure_phase_placements(
    before: GameState,
    targets_by_player: Mapping[int, tuple[StructureBuildTargets, ...]],
    *,
    standard_rules_asserted: bool = False,
    complete_structure_target_scope_asserted: bool = False,
    automatic_supply_sale_enabled: bool = False,
    seed: int = 0,
) -> StructurePlacementComparison:
    opts = dict(
        standard_rules_asserted=standard_rules_asserted,
        complete_structure_target_scope_asserted=complete_structure_target_scope_asserted,
        automatic_supply_sale_enabled=automatic_supply_sale_enabled,
        seed=seed,
    )
    first = simulate_explicit_structure_turn(
        before, targets_by_player, placement=STRUCTURE_PLACEMENTS[0], **opts,
    )
    second = simulate_explicit_structure_turn(
        before, targets_by_player, placement=STRUCTURE_PLACEMENTS[1], **opts,
    )
    if not (first.supported and second.supported):
        return StructurePlacementComparison(
            "ABSTAIN_INCOMPLETE_CONDITIONAL_PLACEMENTS", first, second,
        )
    different = first.state != second.state
    return StructurePlacementComparison(
        "CONDITIONAL_PLACEMENTS_DISTINCT_NOT_HOST_VERIFIED"
        if different else "CONDITIONAL_PLACEMENTS_INDISTINGUISHABLE_NOT_HOST_VERIFIED",
        first, second, observationally_distinct_final_states=different,
    )
