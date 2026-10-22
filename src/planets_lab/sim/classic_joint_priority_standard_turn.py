"""Two distinct, conditional Classic PBP shipbuilding subphases in ONE turn.

A *single* unambiguous priority build is followed by standard pointer
selection.  It is NOT a reconstruction of real NuHost ordering. The
caller supplies the entire fleet/owner/base/PBP/warehouse snapshot,
uncontested priority candidate and a known standard queue pointer.
Priority PBP is spent once; only STANDARD builds advance the pointer.
All selected builds draw the same finite hard-cap ship-ID pool.

The component/ship auditor is reused for each build. The untouched
canonical 14-phase planetary economy runs strictly before OR after both
build subphases as a caller-supplied hypothesis. Reject unsupported
priority remainder (>=21), competing queues, pbN, clones, missing scope
or any unexpected material/state delta with a WHOLE-TURN ABSTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Literal

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.classic_uncontested_priority_pbp import (
    ClassicPriorityContext, PriorityShipOrder,
    simulate_uncontested_classic_pbp_priority,
)
from planets_lab.sim.classic_standard_queue_pointer import (
    ClassicBaseQueueEntry, ClassicStandardSubphase,
    select_classic_standard_subphase,
)
from planets_lab.sim.classic_standard_pointer_economy_turn import (
    ClassicOrdinaryBuild, _build_in_selected_order, UnsupportedClassicStandardTurn,
)
from planets_lab.sim.standard_ship_economy_turn import (
    AssembledShipBalance, UnsupportedShipEconomicTurn,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, UnsupportedMultiBaseQueue, _execute_all_selected,
)
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_ship_component_quote import COST_FIELDS

PLACEMENTS = (
    "classic_joint_builds_before_planetary",
    "classic_joint_builds_after_planetary",
)
STATUS = "CONDITIONAL_CLASSIC_PRIORITY_THEN_STANDARD_NOT_NUHOST_VERIFIED"


class UnsupportedJointClassicTurn(ValueError):
    """An explicit assumption or audited state transition failed."""


@dataclass(frozen=True, slots=True)
class ClassicJointContext:
    """Same complete snapshot used by BOTH queue subphases."""
    priority: ClassicPriorityContext
    standard: ClassicStandardSubphase
    ordinary_queued: Mapping[int, ClassicOrdinaryBuild]


@dataclass(frozen=True, slots=True)
class ClassicJointOutcome:
    status: str
    state: GameState | None = None
    priority_base_id: int | None = None
    priority_ship_id: int | None = None
    priority_pbp_cost: int | None = None
    selected_standard_bases: tuple[int, ...] = ()
    selected_standard_ship_ids: tuple[int, ...] = ()
    pbps_after: tuple[tuple[int, int], ...] = ()
    last_standard_pointer_after: int | None = None
    warehouse_after: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    build_balances: tuple[AssembledShipBalance, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    queue_and_pbp_independently_witnessed: bool = False
    ship_ids_independently_witnessed: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def _check_shared_scope(
    before: GameState, ctx: ClassicJointContext,
) -> None:
    priority = ctx.priority
    standard = ctx.standard
    if (type(ctx) is not ClassicJointContext
            or type(priority) is not ClassicPriorityContext
            or type(standard) is not ClassicStandardSubphase
            or type(ctx.ordinary_queued) is not dict
            or type(priority.queued_base_orders) is not dict
            or type(standard.bases) is not tuple):
        raise UnsupportedJointClassicTurn("complete typed shared queue scope required")
    if (standard.ship_limit != priority.ship_limit
            or standard.current_ship_count != len(before.ships)
            or priority.player_pbps != standard.player_pbps
            or set(priority.queued_base_orders) != set(before.starbases)
            or {r.planet_id for r in standard.bases} != set(before.starbases)
            or set(before.players) != {x[0] for x in priority.player_pbps}
            or len(priority.player_pbps) != len(before.players)):
        raise UnsupportedJointClassicTurn("priority and standard phase source snapshots disagree")
    if not (
        priority.exact_single_precombat_priority_subphase_asserted is True
        and priority.full_fleet_and_base_roster_asserted is True
        and priority.complete_player_pbp_balances_asserted is True
        and priority.no_pb_codes_clones_or_other_priority_orders_asserted is True
        and standard.complete_starbase_roster_asserted is True
        and standard.complete_player_pbp_balances_asserted is True
        and standard.no_cloning_or_other_build_effects_asserted is True
    ):
        raise UnsupportedJointClassicTurn("unasserted queue scope")
    queued = {r.planet_id for r in standard.bases if r.ordinary_ship_queued}
    if set(ctx.ordinary_queued) != queued:
        raise UnsupportedJointClassicTurn("missing or extra ordinary queued designs")
    for row in standard.bases:
        planet = before.planets.get(row.planet_id)
        base = before.starbases.get(row.planet_id)
        if (
            type(row) is not ClassicBaseQueueEntry
            or row.priority_build_code is not None
            or row.clone_ordered is not False
            or type(row.ordinary_ship_queued) is not bool
            or planet is None or base is None
            or base.owner_id != row.owner_id
            or planet.owner_id != row.owner_id
        ):
            raise UnsupportedJointClassicTurn("unmodeled code, clone or ownership")
        priority_order = priority.queued_base_orders[row.planet_id]
        standard_order = ctx.ordinary_queued.get(row.planet_id)
        if (priority_order is None) != (standard_order is None):
            raise UnsupportedJointClassicTurn("subphases disagree about queued starships")
        if priority_order is not None:
            if (
                type(priority_order) is not PriorityShipOrder
                or type(standard_order) is not ClassicOrdinaryBuild
                or priority_order.blueprint != standard_order.blueprint
                or priority_order.warehouse != standard_order.warehouse
                or priority_order.allowed_hull_ids != standard_order.allowed_hull_ids
            ):
                raise UnsupportedJointClassicTurn("priority vs standard instructions disagree")
    if before.metadata or before.ion_storms:
        raise UnsupportedJointClassicTurn("special/ion interactions unsupported")


def _build_shared_phase(
    before: GameState,
    specs: NuStaticSpecs,
    ctx: ClassicJointContext,
) -> tuple[
    GameState, int, int, int, tuple[tuple[int, int], ...],
    tuple[int, ...], int, tuple[AssembledShipBalance, ...],
]:
    # Priority is guaranteed a single eligible owner and a single base;
    # it produces the exact intermediate state and charged PBP ledger.
    priority = simulate_uncontested_classic_pbp_priority(
        before, specs, ctx.priority,
        standard_rules_asserted=True,
        complete_warehouse_and_hull_rights_asserted=True,
    )
    if (
        not priority.supported or priority.phase_state is None
        or priority.selected_base_planet_id is None
        or priority.built_ship_id is None
        or priority.pbp_cost is None
        or priority.warehouse_after is None
    ):
        raise UnsupportedJointClassicTurn("unattributable PBP priority build")
    priority_base = priority.selected_base_planet_id
    priority_ship = priority.built_ship_id
    # Independent replay from the unmodified BEFORE: typed/quoted
    # resources and exactly one new ship must match the priority result.
    chosen_order = ctx.priority.queued_base_orders[priority_base]
    assert chosen_order is not None
    standalone_slot = SelectedBuildSlot(
        starbase_planet_id=priority_base,
        proposed_ship_id=priority_ship,
        global_ship_limit=ctx.priority.ship_limit,
        complete_global_ship_roster_asserted=True,
        queue_selection_asserted=True,
    )
    verified_state, priority_receipts = _execute_all_selected(
        before, specs,
        {priority_base: CompleteBaseBuild(
            blueprint=chosen_order.blueprint,
            warehouse=chosen_order.warehouse,
            slot=standalone_slot,
            allowed_hull_ids=chosen_order.allowed_hull_ids,
        )},
        ctx.priority.ship_limit,
    )
    if (
        verified_state != priority.phase_state
        or len(priority_receipts) != 1
        or priority_receipts[0].warehouse_after != priority.warehouse_after
        or priority_receipts[0].purchased != priority.purchased_materials
    ):
        raise UnsupportedJointClassicTurn("priority phase receipt and state disagree")

    # IMPORTANT: a base built in priority is no longer eligible to build
    # again in the same bounded phase. Priority must NOT move the saved
    # standard pointer, and its PBP expense must not be charged twice.
    if any(points >= 21 for _, points in priority.player_pbps_after):
        raise UnsupportedJointClassicTurn(
            "priority-eligible owner remains; another priority subphase may be required"
        )
    next_bases = tuple(
        replace(row, ordinary_ship_queued=False)
        if row.planet_id == priority_base else row
        for row in ctx.standard.bases
    )
    remaining_context = replace(
        ctx.standard,
        current_ship_count=len(priority.phase_state.ships),
        player_pbps=priority.player_pbps_after,
        bases=next_bases,
        standard_phase_after_priorities_asserted=True,
    )
    standard_selection = select_classic_standard_subphase(remaining_context)
    if not standard_selection.supported:
        raise UnsupportedJointClassicTurn("unattributable postpriority standard pointer")
    remaining_orders = {
        pid: build for pid, build in ctx.ordinary_queued.items()
        if pid != priority_base
    }
    result_state, standard_receipts = _build_in_selected_order(
        priority.phase_state, specs, remaining_orders,
        standard_selection.selected_planet_ids, ctx.standard.ship_limit,
    )
    if (
        len(result_state.ships) != len(before.ships) + 1 + len(standard_receipts)
        or priority_ship not in result_state.ships
    ):
        raise UnsupportedJointClassicTurn("unexpected priority/standard ship count")
    return (
        result_state, priority_base, priority_ship, priority.pbp_cost,
        priority.player_pbps_after,
        standard_selection.selected_planet_ids,
        standard_selection.last_standard_build_planet_id_after,
        priority_receipts + standard_receipts,
    )


def simulate_classic_joint_priority_standard_turn(
    before: GameState,
    specs: NuStaticSpecs,
    context: ClassicJointContext,
    *,
    placement: Literal[
        "classic_joint_builds_before_planetary",
        "classic_joint_builds_after_planetary",
    ],
    standard_rules_asserted: bool = False,
    complete_queue_and_component_scope_asserted: bool = False,
    no_other_ship_or_base_actions_asserted: bool = False,
    seed: int = 0,
) -> ClassicJointOutcome:
    def abstain(reason: str) -> ClassicJointOutcome:
        return ClassicJointOutcome("ABSTAIN_CLASSIC_JOINT_TURN", reason=reason)

    if (
        type(before) is not GameState
        or type(specs) is not NuStaticSpecs
        or type(context) is not ClassicJointContext
        or type(seed) is not int
        or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_queue_and_component_scope_asserted is not True
        or no_other_ship_or_base_actions_asserted is not True
    ):
        return abstain("incomplete standard queue/economy assumption")
    try:
        before.validate()
        _check_shared_scope(before, context)
        economic = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            p: PlayerOrders(player_id=p) for p in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            (built, priority_base, priority_ship, pbp_cost,
             pbps, standard_ids, next_pointer, receipts) = _build_shared_phase(
                before, specs, context,
            )
            modeled, events = economic.step(built, noop, seed=seed)
        else:
            economy, events = economic.step(before, noop, seed=seed)
            (modeled, priority_base, priority_ship, pbp_cost,
             pbps, standard_ids, next_pointer, receipts) = _build_shared_phase(
                economy, specs, context,
            )
        projection = modeled.clone()
        for receipt in receipts:
            pid = receipt.starbase_planet_id
            sid = receipt.ship_id
            if sid not in projection.ships or pid not in projection.planets:
                raise UnsupportedJointClassicTurn("lost assembled ship/base")
            projection.ships.pop(sid)
            for name in COST_FIELDS:
                value = getattr(projection.planets[pid].cargo, name)
                if type(value) is not int or value < 0:
                    raise UnsupportedJointClassicTurn("invalid surface resource")
                setattr(
                    projection.planets[pid].cargo, name,
                    value + getattr(receipt.purchased, name),
                )
        new_ids = {r.ship_id for r in receipts}
        if (
            set(modeled.ships) != set(before.ships) | new_ids
            or len(new_ids) != len(receipts)
            or any(modeled.ships[sid] != ship for sid, ship in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedJointClassicTurn("unexpected final fleet or base state")
        # Reverify the actual final ship blueprints after BOTH assembly
        # and economy, not just the intermediate material receipts.
        for receipt in receipts:
            pid = receipt.starbase_planet_id
            if pid == priority_base:
                design = context.priority.queued_base_orders[pid].blueprint
            else:
                design = context.ordinary_queued[pid].blueprint
            hull = specs.hulls[design.hull_id]
            home = before.planets[pid]
            expected = Ship(
                id=receipt.ship_id, owner_id=before.starbases[pid].owner_id,
                hull_id=design.hull_id, x=home.x, y=home.y,
                engine_id=design.engine_id,
                beam_id=design.beam_id if design.beam_count else None,
                torpedo_id=design.torpedo_id if design.torpedo_launcher_count else None,
                beam_count=design.beam_count,
                torpedo_launcher_count=design.torpedo_launcher_count,
                fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
            )
            if modeled.ships[receipt.ship_id] != expected:
                raise UnsupportedJointClassicTurn("final assembled ship changed silently")
        planet_balances = _planet_ledgers(before, projection, events)
        if not all(x.resource_balance_exact for x in planet_balances):
            raise UnsupportedJointClassicTurn("unreconciled planetary economy")
        warehouses = {
            pid: order.warehouse for pid, order in context.ordinary_queued.items()
        }
        for receipt in receipts:
            warehouses[receipt.starbase_planet_id] = receipt.warehouse_after
        return ClassicJointOutcome(
            STATUS, state=modeled, priority_base_id=priority_base,
            priority_ship_id=priority_ship, priority_pbp_cost=pbp_cost,
            selected_standard_bases=standard_ids,
            selected_standard_ship_ids=tuple(x.ship_id for x in receipts[1:]),
            pbps_after=pbps,
            last_standard_pointer_after=next_pointer,
            warehouse_after=tuple(sorted(warehouses.items())),
            build_balances=receipts,
            planet_balances=planet_balances,
            economic_events=events,
        )
    except (
        UnsupportedJointClassicTurn, UnsupportedClassicStandardTurn,
        UnsupportedMultiBaseQueue, UnsupportedShipEconomicTurn,
        UnsupportedEconomicLedger, UnsupportedPopulationRule,
        ValueError, TypeError, AttributeError, KeyError, OverflowError,
    ):
        return abstain("unsupported or unreconciled priority/standard/economic state")
