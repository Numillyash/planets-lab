"""Bounded common EARLY/unthrottled all-bases shipbuilding research turn.

This models the intersection of Classic PBP, PQ and PPQ *early* modes:
ALL existing ordinary bases have one queued ship, ALL can build well below
the hard/soft global ship-limit boundary, and no priority/cloning/empty
base/advanced/campaign action competes. Build order is NOT inferred;
bases are processed by ID only for reproducibility of disjoint purchases.

At/near the cap, in late mode, and with contested slots, ABSTAIN rather
than claim a Classic pointer, randomized PQ decision or PPQ point allocation.
Complete warehouses, hull rights, free IDs and absence of priority orders
are caller assertions, NOT independently authenticated Host evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs, ResourceCost
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_ship_component_quote import (
    COST_FIELDS, StandardShipBlueprint,
)
from planets_lab.sim.standard_ship_economy_turn import (
    _audit_selected_assembly, AssembledShipBalance,
    UnsupportedShipEconomicTurn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
    QUEUE_HYPOTHESIS, assemble_selected_standard_ship,
)

QUEUE_MODES = ("CLASSIC_PBP", "PRODUCTION_PQ", "PLANETARY_PPQ")
PLACEMENTS = ("unthrottled_builds_before_planetary", "unthrottled_builds_after_planetary")
STATUS = "CONDITIONAL_UNTHROTTLED_ALL_BASES_BUILD_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class CompleteBaseBuild:
    """Exactly one queue entry for one real base; nothing is inferred."""
    blueprint: StandardShipBlueprint
    warehouse: StandardComponentWarehouse
    slot: SelectedBuildSlot
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class MultiBaseBuildOutcome:
    status: str
    state: GameState | None = None
    receipts: tuple[AssembledShipBalance, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economy_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    queue_mode: str | None = None
    order_source: str = "COMPLETE_CALLER_ASSERTED_UNTHROTTLED_BASE_QUEUE_AND_IDS"
    independently_verified_queue_order: bool = False
    independently_verified_priority_points: bool = False
    independently_verified_ship_id_allocation: bool = False
    independently_verified_component_warehouses: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedMultiBaseQueue(ValueError):
    """Strict bounded model admission failure."""


def _validate_unthrottled_roster(
    before: GameState,
    queue: Mapping[int, CompleteBaseBuild],
    queue_mode: str,
    ship_limit: int,
) -> None:
    if (
        queue_mode not in QUEUE_MODES
        or type(ship_limit) is not int
        or not 10 <= ship_limit <= 999
        or type(queue) is not dict
        or len(queue) < 2
        or set(queue) != set(before.starbases)
        or len(queue) > 64
    ):
        raise UnsupportedMultiBaseQueue("unknown queue or missing/oversized base roster")
    if before.metadata or before.ion_storms:
        raise UnsupportedMultiBaseQueue("game modifiers or storms not modeled")
    if len(before.ships) + len(queue) > 999:
        raise UnsupportedMultiBaseQueue("no programmatic ship numbers")
    # Conservative *common* fully unthrottled window. Classic switches to
    # PBP-sensitive middle mode at 90% of the configured ship limit. PQ/PPQ
    # can use different selection and PP/points when fewer slots exist.
    if 10 * (len(before.ships) + len(queue)) >= 9 * ship_limit:
        raise UnsupportedMultiBaseQueue("approaching contested/priority queue window")
    proposed: set[int] = set()
    for pid in sorted(queue):
        request = queue[pid]
        base = before.starbases[pid]
        planet = before.planets.get(pid)
        if (
            type(pid) is not int or type(request) is not CompleteBaseBuild
            or planet is None or planet.owner_id is None
            or planet.owner_id not in before.players
            or planet.owner_id != base.owner_id
            or type(request.blueprint) is not StandardShipBlueprint
            or type(request.warehouse) is not StandardComponentWarehouse
            or type(request.slot) is not SelectedBuildSlot
            or request.slot.starbase_planet_id != pid
            or request.slot.queue_hypothesis != QUEUE_HYPOTHESIS
            or request.slot.queue_selection_asserted is not True
            or request.slot.complete_global_ship_roster_asserted is not True
            or request.slot.global_ship_limit != ship_limit
            or type(request.allowed_hull_ids) is not frozenset
        ):
            raise UnsupportedMultiBaseQueue("untrusted per-base queue/owner/warehouse")
        sid = request.slot.proposed_ship_id
        if (
            type(sid) is not int or not 1 <= sid <= 999
            or (queue_mode == "CLASSIC_PBP" and sid > ship_limit)
            or sid in before.ships or sid in proposed
        ):
            raise UnsupportedMultiBaseQueue("reused or out-of-range asserted ship ID")
        proposed.add(sid)
    if any(
        (ship.mission is not None or ship.mission1_target_id is not None
         or ship.mission2_target_id is not None or ship.warp != 0
         or ship.damage != 0)
        for ship in before.ships.values()
    ):
        raise UnsupportedMultiBaseQueue("unmodeled existing fleet activity")


def _execute_all_selected(
    before: GameState,
    specs: NuStaticSpecs,
    queue: Mapping[int, CompleteBaseBuild],
    ship_limit: int,
) -> tuple[GameState, tuple[AssembledShipBalance, ...]]:
    working = before
    output: list[AssembledShipBalance] = []
    # Sorting is a LOCAL deterministic implementation choice ONLY:
    # disjoint planets/stocks and universally admitted slots mean it cannot
    # establish real queue priority or serialized Host order.
    for pid in sorted(queue):
        intent = queue[pid]
        result = assemble_selected_standard_ship(
            working, specs, intent.blueprint, intent.warehouse, intent.slot,
            allowed_hull_ids=intent.allowed_hull_ids,
            standard_rules_asserted=True,
            complete_warehouse_asserted=True,
            hull_eligibility_asserted=True,
            standard_hull_crew_asserted=True,
        )
        if not result.supported or result.phase_state is None:
            raise UnsupportedMultiBaseQueue("one queued base cannot purchase its ship")
        # Reuse the independent PR #257 unit/price/new-ship auditor for EACH
        # base. Its contract expects one adjacent turn, so use a *detached*
        # synthetic +1 turn audit copy without altering the real phase turn.
        next_for_audit = result.phase_state.clone()
        next_for_audit.turn += 1
        projected, receipt = _audit_selected_assembly(
            working, next_for_audit, result, intent.warehouse, specs,
            intent.blueprint, intent.slot,
        )
        expected = working.clone()
        expected.turn += 1
        if projected != expected:
            raise UnsupportedMultiBaseQueue("unexplained per-base side effect")
        if result.phase_state.turn != working.turn:
            raise UnsupportedMultiBaseQueue("assembly advanced the turn unexpectedly")
        working = result.phase_state
        output.append(receipt)
    if len(working.ships) != len(before.ships) + len(queue):
        raise UnsupportedMultiBaseQueue("ship roster delta unexplained")
    return working, tuple(output)


def simulate_unthrottled_multibase_build_turn(
    before: GameState,
    specs: NuStaticSpecs,
    queue: Mapping[int, CompleteBaseBuild],
    *,
    queue_mode: Literal["CLASSIC_PBP", "PRODUCTION_PQ", "PLANETARY_PPQ"],
    global_ship_limit: int,
    placement: Literal[
        "unthrottled_builds_before_planetary",
        "unthrottled_builds_after_planetary",
    ],
    standard_rules_asserted: bool = False,
    complete_base_roster_and_warehouses_asserted: bool = False,
    all_bases_have_ordinary_builds_asserted: bool = False,
    no_priority_cloning_or_other_base_actions_asserted: bool = False,
    no_ship_actions_or_combat_asserted: bool = False,
    seed: int = 0,
) -> MultiBaseBuildOutcome:
    def abstain(reason: str) -> MultiBaseBuildOutcome:
        return MultiBaseBuildOutcome("ABSTAIN_UNTHROTTLED_MULTI_BASE_BUILD", reason=reason)

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(seed) is not int or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_base_roster_and_warehouses_asserted is not True
        or all_bases_have_ordinary_builds_asserted is not True
        or no_priority_cloning_or_other_base_actions_asserted is not True
        or no_ship_actions_or_combat_asserted is not True
    ):
        return abstain("explicit full standard unthrottled scope required")
    try:
        before.validate()
        _validate_unthrottled_roster(before, queue, queue_mode, global_ship_limit)
        econ = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            p: PlayerOrders(player_id=p) for p in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            assembled, receipts = _execute_all_selected(
                before, specs, queue, global_ship_limit,
            )
            modeled, events = econ.step(assembled, noop, seed=seed)
        else:
            economy, events = econ.step(before, noop, seed=seed)
            modeled, receipts = _execute_all_selected(
                economy, specs, queue, global_ship_limit,
            )
        # Whole-turn independent resource controls. Undo *only* the
        # purchased material cost for each base, remove only new ships,
        # then reconcile all 14-phase economy effects against pre-turn.
        projection = modeled.clone()
        for item in receipts:
            if item.ship_id not in projection.ships:
                raise UnsupportedMultiBaseQueue("assembled ship disappeared")
            projection.ships.pop(item.ship_id)
            for material in COST_FIELDS:
                value = getattr(projection.planets[item.starbase_planet_id].cargo, material)
                if type(value) is not int or value < 0:
                    raise UnsupportedMultiBaseQueue("invalid final planet material")
                setattr(
                    projection.planets[item.starbase_planet_id].cargo, material,
                    value + getattr(item.purchased, material),
                )
        if (
            set(modeled.ships) != set(before.ships) | {r.ship_id for r in receipts}
            or any(modeled.ships[sid] != old for sid, old in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedMultiBaseQueue("other ships/starbases were modified")
        balances = _planet_ledgers(before, projection, events)
        if not all(x.resource_balance_exact for x in balances):
            raise UnsupportedMultiBaseQueue("planet economy budget unexplained")
    except (
        UnsupportedMultiBaseQueue, UnsupportedShipEconomicTurn,
        UnsupportedEconomicLedger, UnsupportedPopulationRule,
        ValueError, TypeError, AttributeError, KeyError, OverflowError,
    ):
        return abstain("unsupported build queue, receipt or resource accounting")
    return MultiBaseBuildOutcome(
        status=STATUS, state=modeled, receipts=receipts,
        planet_balances=balances, economy_events=events,
        queue_mode=queue_mode,
    )
