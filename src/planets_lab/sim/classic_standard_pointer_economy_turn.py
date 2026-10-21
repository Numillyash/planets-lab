"""Exact-scope Classic STANDARD pointer -> selected ship assembly + economy.

This is a conditional *standard subphase*, not full Classic PBP Host logic.
An externally asserted saved pointer, full player PBP (<21) and all-base
roster feed the independently tested circular standard selector.
Selected base builds use caller-asserted immutable component stocks and
rights, but ship IDs are allocated here as lowest free IDs in *pointer
selection order*, subject to the hard Classic cap.

No priority builds, pbN, middle PBP consumption, cloning, PvP, movement
or pre/post-combat causal inference. Failed later builds ABSTAIN the
entire synthetic turn without emitting intermediate ships or resources.
"""
from __future__ import annotations

from dataclasses import dataclass
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
from planets_lab.sim.standard_ship_component_quote import COST_FIELDS, StandardShipBlueprint
from planets_lab.sim.standard_ship_economy_turn import AssembledShipBalance, UnsupportedShipEconomicTurn
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, UnsupportedMultiBaseQueue, _execute_all_selected,
)
from planets_lab.sim.classic_standard_queue_pointer import (
    ClassicStandardSubphase, select_classic_standard_subphase,
)

PLACEMENTS = ("classic_standard_before_planetary", "classic_standard_after_planetary")
STATUS = "CONDITIONAL_CLASSIC_POINTER_ASSEMBLY_ECONOMY_NOT_NUHOST_VERIFIED"


class UnsupportedClassicStandardTurn(ValueError):
    """Any unsupported input or unexpected resource/queue mutation."""


@dataclass(frozen=True, slots=True)
class ClassicOrdinaryBuild:
    blueprint: StandardShipBlueprint
    warehouse: StandardComponentWarehouse
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class ClassicPointerEconomicOutcome:
    status: str
    state: GameState | None = None
    selected_planet_ids: tuple[int, ...] = ()
    selected_ship_ids: tuple[int, ...] = ()
    last_standard_build_planet_id_after: int | None = None
    build_receipts: tuple[AssembledShipBalance, ...] = ()
    warehouse_states_after: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    source: str = "CALLER_ASSERTED_CLASSIC_STANDARD_POINTER_NO_PBP_PRIORITY"
    pointer_independently_witnessed: bool = False
    queue_selection_independently_witnessed: bool = False
    player_pbp_balances_independently_witnessed: bool = False
    ship_id_allocation_independently_witnessed: bool = False
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False
    nuhost_phase_placement_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def _strict_scope(
    before: GameState,
    context: ClassicStandardSubphase,
    ordinary_orders: Mapping[int, ClassicOrdinaryBuild],
) -> None:
    if (type(context) is not ClassicStandardSubphase
            or type(ordinary_orders) is not dict
            or len(before.starbases) < 2
            or before.metadata or before.ion_storms):
        raise UnsupportedClassicStandardTurn("explicit ordinary multi-base Classic scope required")
    if (
        context.current_ship_count != len(before.ships)
        or set(row.planet_id for row in context.bases) != set(before.starbases)
        or set(pid for pid, _ in context.player_pbps) != set(before.players)
    ):
        raise UnsupportedClassicStandardTurn("asserted complete fleet, player and base scope disagree")
    queued = {row.planet_id for row in context.bases if row.ordinary_ship_queued is True}
    if set(ordinary_orders) != queued or not queued:
        raise UnsupportedClassicStandardTurn("all and only ordinary queued base designs required")
    for row in context.bases:
        planet = before.planets.get(row.planet_id)
        base = before.starbases.get(row.planet_id)
        if (planet is None or base is None
                or planet.owner_id != row.owner_id
                or base.owner_id != row.owner_id):
            raise UnsupportedClassicStandardTurn("starbase/owner mismatch")
    for pid, build in ordinary_orders.items():
        if (type(pid) is not int
                or type(build) is not ClassicOrdinaryBuild
                or type(build.blueprint) is not StandardShipBlueprint
                or type(build.warehouse) is not StandardComponentWarehouse
                or type(build.allowed_hull_ids) is not frozenset):
            raise UnsupportedClassicStandardTurn("incomplete component warehouse, design or race rights")
    for ship in before.ships.values():
        if (ship.mission is not None or ship.mission1_target_id is not None
                or ship.mission2_target_id is not None
                or ship.warp != 0 or ship.damage != 0):
            raise UnsupportedClassicStandardTurn("moving/combat/mission ships outside bounded scope")


def _build_in_selected_order(
    state: GameState,
    specs: NuStaticSpecs,
    ordinary_orders: Mapping[int, ClassicOrdinaryBuild],
    selection: tuple[int, ...],
    ship_limit: int,
) -> tuple[GameState, tuple[AssembledShipBalance, ...]]:
    working = state
    receipts: list[AssembledShipBalance] = []
    for base_id in selection:
        if base_id not in ordinary_orders:
            raise UnsupportedClassicStandardTurn("selected base lacks a typed ordinary build")
        # Classic hard-limited ships use the lowest available number.
        allocated = next(
            (candidate for candidate in range(1, ship_limit + 1)
             if candidate not in working.ships),
            None,
        )
        if allocated is None:
            raise UnsupportedClassicStandardTurn("no legal Classic ship number")
        requested = ordinary_orders[base_id]
        chosen = SelectedBuildSlot(
            starbase_planet_id=base_id,
            proposed_ship_id=allocated,
            global_ship_limit=ship_limit,
            complete_global_ship_roster_asserted=True,
            queue_selection_asserted=True,
        )
        # The existing per-base component and ship/state auditor is reused
        # without modifying its original independently tested behavior.
        completed, rows = _execute_all_selected(
            working, specs,
            {base_id: CompleteBaseBuild(
                blueprint=requested.blueprint,
                warehouse=requested.warehouse,
                slot=chosen,
                allowed_hull_ids=requested.allowed_hull_ids,
            )},
            ship_limit,
        )
        if len(rows) != 1 or rows[0].ship_id != allocated:
            raise UnsupportedClassicStandardTurn("bad selected ship receipt")
        working = completed
        receipts.append(rows[0])
    return working, tuple(receipts)


def simulate_classic_standard_pointer_economy_turn(
    before: GameState,
    specs: NuStaticSpecs,
    context: ClassicStandardSubphase,
    ordinary_orders: Mapping[int, ClassicOrdinaryBuild],
    *,
    placement: Literal["classic_standard_before_planetary", "classic_standard_after_planetary"],
    standard_rules_asserted: bool = False,
    complete_warehouses_and_hull_rights_asserted: bool = False,
    no_other_ship_base_or_combat_actions_asserted: bool = False,
    seed: int = 0,
) -> ClassicPointerEconomicOutcome:
    def abstain(reason: str) -> ClassicPointerEconomicOutcome:
        return ClassicPointerEconomicOutcome(
            status="ABSTAIN_CLASSIC_POINTER_ECONOMIC_TURN", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(seed) is not int or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_warehouses_and_hull_rights_asserted is not True
        or no_other_ship_base_or_combat_actions_asserted is not True
    ):
        return abstain("missing explicit supported Classic conditions")
    try:
        before.validate()
        _strict_scope(before, context, ordinary_orders)
        eligible = select_classic_standard_subphase(context)
        if not eligible.supported:
            return abstain("missing valid saved-pointer/low-PBP standard-only selection")
        econ = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner) for owner in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            built, receipts = _build_in_selected_order(
                before, specs, ordinary_orders,
                eligible.selected_planet_ids, context.ship_limit,
            )
            modeled, events = econ.step(built, noop, seed=seed)
        else:
            intermediate, events = econ.step(before, noop, seed=seed)
            modeled, receipts = _build_in_selected_order(
                intermediate, specs, ordinary_orders,
                eligible.selected_planet_ids, context.ship_limit,
            )
        # Reconstruct the expected assembled ships from the *original*
        # typed blueprint and static catalog, rather than trusting a phase
        # executor's already-audited but later mutable ship object.
        for receipt in receipts:
            intended = ordinary_orders[receipt.starbase_planet_id].blueprint
            hull = specs.hulls[intended.hull_id]
            origin = before.planets[receipt.starbase_planet_id]
            expected_ship = Ship(
                id=receipt.ship_id,
                owner_id=before.starbases[receipt.starbase_planet_id].owner_id,
                hull_id=intended.hull_id,
                x=origin.x, y=origin.y, engine_id=intended.engine_id,
                beam_id=intended.beam_id if intended.beam_count else None,
                torpedo_id=(intended.torpedo_id
                            if intended.torpedo_launcher_count else None),
                beam_count=intended.beam_count,
                torpedo_launcher_count=intended.torpedo_launcher_count,
                fighter_bay_count=hull.fighter_bay_count,
                crew=hull.crew,
            )
            if modeled.ships.get(receipt.ship_id) != expected_ship:
                raise UnsupportedClassicStandardTurn("assembled ship mutated after its material receipt")
        # Undo only exact new-component expenses and precisely the ships
        # authorized by the standard pointer. Audit the separate
        # 14-phase planet economy on this cloned projection.
        projection = modeled.clone()
        selected_ship_ids: list[int] = []
        for receipt in receipts:
            sid = receipt.ship_id
            pid = receipt.starbase_planet_id
            if sid not in projection.ships or pid not in projection.planets:
                raise UnsupportedClassicStandardTurn("missing selected ship or debit planet")
            selected_ship_ids.append(sid)
            projection.ships.pop(sid)
            for material in COST_FIELDS:
                current = getattr(projection.planets[pid].cargo, material)
                if type(current) is not int or current < 0:
                    raise UnsupportedClassicStandardTurn("invalid final planet stock")
                setattr(
                    projection.planets[pid].cargo, material,
                    current + getattr(receipt.purchased, material),
                )
        if (len(receipts) != len(eligible.selected_planet_ids)
                or {receipt.starbase_planet_id for receipt in receipts}
                   != set(eligible.selected_planet_ids)
                or set(modeled.ships) != set(before.ships) | set(selected_ship_ids)
                or any(modeled.ships[sid] != ship for sid, ship in before.ships.items())
                or modeled.starbases != before.starbases):
            raise UnsupportedClassicStandardTurn("unexpected ship/base mutation or queue result")
        budgets = _planet_ledgers(before, projection, events)
        after_stock = {
            pid: ordinary_orders[pid].warehouse for pid in ordinary_orders
        }
        for receipt in receipts:
            after_stock[receipt.starbase_planet_id] = receipt.warehouse_after
        # Pointer is updated only by regular selected builds, never by
        # any local sort order, priority hypothesis or Host inference.
        return ClassicPointerEconomicOutcome(
            status=STATUS,
            state=modeled,
            selected_planet_ids=eligible.selected_planet_ids,
            selected_ship_ids=tuple(selected_ship_ids),
            last_standard_build_planet_id_after=eligible.last_standard_build_planet_id_after,
            build_receipts=receipts,
            warehouse_states_after=tuple(sorted(after_stock.items())),
            planet_balances=budgets,
            economic_events=events,
        )
    except (
        UnsupportedClassicStandardTurn, UnsupportedMultiBaseQueue,
        UnsupportedShipEconomicTurn, UnsupportedEconomicLedger,
        UnsupportedPopulationRule, ValueError, TypeError,
        KeyError, AttributeError, OverflowError,
    ):
        return abstain("invalid queue scope or unexplained ship, storage or planet inventory")
