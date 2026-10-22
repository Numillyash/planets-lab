"""Late PPQ integer Stage-1 regular ships, exact BOM and 14-phase economy.

Only the selection SET is uniquely modeled by the #269 quote. The
base-to-ID permutation and placement relative to the planetary economy
are explicit caller hypotheses, never inferred NuHost facts.

The ordinary prelimit assembler is invoked with the PROGRAMMATIC 999
Ship-ID ceiling, not the soft PPQ limit. PPQ regular Stage 1 expressly
may produce 10 ships and exceed its configured soft limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.late_ppq_integer_stage1_allocation import (
    PPQStage1Context, PPQStage1Quote, quote_integral_ppq_regular_stage1,
)
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import PlanetEconomicBalance, _planet_ledgers
from planets_lab.sim.standard_ship_component_quote import (
    COST_FIELDS, StandardShipBlueprint,
)
from planets_lab.sim.standard_ship_economy_turn import AssembledShipBalance
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse, _decode_rows,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, _execute_all_selected,
)

STATUS = "CONDITIONAL_LATE_PPQ_STAGE1_SHIPS_AND_ECONOMY_NOT_NUHOST_VERIFIED"
PLACEMENTS = (
    "late_regular_builds_before_economy",
    "late_regular_builds_after_economy",
)


@dataclass(frozen=True, slots=True)
class PPQWarehouseBase:
    planet_id: int
    warehouse: StandardComponentWarehouse
    blueprint: StandardShipBlueprint | None = None
    allowed_hull_ids: frozenset[int] | None = None
    asserted_ship_id: int | None = None


@dataclass(frozen=True, slots=True)
class PPQIntegralEconomicContext:
    stage1: PPQStage1Context
    all_base_warehouses: tuple[PPQWarehouseBase, ...]
    player_pp: tuple[tuple[int, int], ...]
    complete_warehouse_hull_rights_and_ship_id_assignment_asserted: bool = False
    default_zero_pp_regular_build_and_no_pp_income_asserted: bool = False
    no_external_ship_planet_base_or_combat_effects_asserted: bool = False


@dataclass(frozen=True, slots=True)
class PPQIntegralEconomicOutcome:
    status: str
    state: GameState | None = None
    selected_bases_by_owner: tuple[tuple[int, tuple[int, ...]], ...] = ()
    ship_receipts: tuple[AssembledShipBalance, ...] = ()
    player_pp_after: tuple[tuple[int, int], ...] = ()
    base_warehouses_after: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    selected_set_independently_verified: bool = False
    base_to_ship_id_assignment_verified: bool = False
    accepted_order_independently_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedPPQEconomy(ValueError):
    """All-or-nothing conditional late PPQ economy rejection."""


def _admit(
    before: GameState, specs: NuStaticSpecs, context: PPQIntegralEconomicContext,
    selection: PPQStage1Quote,
) -> tuple[dict[int, CompleteBaseBuild],
           dict[int, StandardComponentWarehouse], tuple[tuple[int, int], ...]]:
    base_rows = context.all_base_warehouses
    if (
        type(base_rows) is not tuple
        or len(base_rows) != len(before.starbases)
        or type(context.player_pp) is not tuple
        or not selection.supported
    ):
        raise UnsupportedPPQEconomy("incomplete warehouses, owner PP or selection")
    pp: dict[int, int] = {}
    for row in context.player_pp:
        if (
            type(row) is not tuple or len(row) != 2
            or type(row[0]) is not int or row[0] not in before.players
            or row[0] in pp or type(row[1]) is not int
            or not 0 <= row[1] <= 1000000
        ):
            raise UnsupportedPPQEconomy("incomplete or invalid PP ownership ledger")
        pp[row[0]] = row[1]
    if set(pp) != set(before.players):
        raise UnsupportedPPQEconomy("missing owner PP")

    source_roster = {row.planet_id: row for row in context.stage1.all_bases}
    selected = {
        pid for _, bases in selection.selected_base_ids_by_owner for pid in bases
    }
    pool = set(selection.lowest_available_ship_id_pool)
    if (
        len(pool) != selection.allocated_regular_slots
        or len(selected) != len(pool)
        or len(pool) == 0
    ):
        raise UnsupportedPPQEconomy("unreconciled Stage-1 selected slot set")
    queues: dict[int, CompleteBaseBuild] = {}
    warehouses: dict[int, StandardComponentWarehouse] = {}
    ids: set[int] = set()
    for row in base_rows:
        if (
            type(row) is not PPQWarehouseBase
            or type(row.planet_id) is not int
            or row.planet_id not in before.starbases
            or row.planet_id in warehouses
            or type(row.warehouse) is not StandardComponentWarehouse
        ):
            raise UnsupportedPPQEconomy("duplicate/missing base or warehouse")
        pid = row.planet_id
        warehouses[pid] = row.warehouse
        for name, catalog in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(ident not in catalog for ident in _decode_rows(
                getattr(row.warehouse, name)
            )):
                raise UnsupportedPPQEconomy("unrecognized component stock at a base")

        src = source_roster[pid]
        if src.queued:
            if (
                type(row.blueprint) is not StandardShipBlueprint
                or type(row.allowed_hull_ids) is not frozenset
                or any(type(i) is not int for i in row.allowed_hull_ids)
                or row.blueprint.hull_id not in row.allowed_hull_ids
                or row.blueprint.hull_id not in specs.hulls
                or type(specs.hulls[row.blueprint.hull_id].mass) is not int
                or specs.hulls[row.blueprint.hull_id].mass != src.hull_mass_kt
            ):
                raise UnsupportedPPQEconomy("queued base not matched to its hull mass or rights")
        elif row.blueprint is not None or row.allowed_hull_ids is not None:
            raise UnsupportedPPQEconomy("idle base has unexplained blueprint or hull rights")

        if pid in selected:
            sid = row.asserted_ship_id
            if (
                type(sid) is not int or sid not in pool
                or sid in ids or not src.queued
            ):
                raise UnsupportedPPQEconomy("missing/duplicate/unassigned selected ship ID")
            ids.add(sid)
            queues[pid] = CompleteBaseBuild(
                blueprint=row.blueprint, warehouse=row.warehouse,
                allowed_hull_ids=row.allowed_hull_ids,
                slot=SelectedBuildSlot(
                    starbase_planet_id=pid, proposed_ship_id=sid,
                    # The assembler prelimit check is bound to the absolute
                    # PROGRAMMATIC ceiling, never the PPQ soft cap.
                    global_ship_limit=999,
                    complete_global_ship_roster_asserted=True,
                    queue_selection_asserted=True,
                ),
            )
        elif row.asserted_ship_id is not None:
            raise UnsupportedPPQEconomy("an unselected base was given a ship ID")
    if (
        set(warehouses) != set(before.starbases)
        or ids != pool or set(queues) != selected
    ):
        raise UnsupportedPPQEconomy("incomplete full-roster or ID bijection")
    return queues, warehouses, tuple(sorted(pp.items()))


def simulate_integral_ppq_stage1_economic_turn(
    before: GameState, specs: NuStaticSpecs, context: PPQIntegralEconomicContext,
    *, placement: Literal[
        "late_regular_builds_before_economy",
        "late_regular_builds_after_economy",
    ],
    standard_rules_asserted: bool = False,
    complete_independent_planetary_inventory_asserted: bool = False,
    seed: int = 0,
) -> PPQIntegralEconomicOutcome:
    def abstain(reason: str) -> PPQIntegralEconomicOutcome:
        return PPQIntegralEconomicOutcome(
            "ABSTAIN_LATE_PPQ_STAGE1_ECONOMIC_TURN", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not PPQIntegralEconomicContext
        or type(seed) is not int or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_independent_planetary_inventory_asserted is not True
        or context.complete_warehouse_hull_rights_and_ship_id_assignment_asserted is not True
        or context.default_zero_pp_regular_build_and_no_pp_income_asserted is not True
        or context.no_external_ship_planet_base_or_combat_effects_asserted is not True
    ):
        return abstain("incomplete asserted late PPQ or economic scope")
    try:
        selection = quote_integral_ppq_regular_stage1(before, context.stage1)
        if not selection.supported:
            raise UnsupportedPPQEconomy("ambiguous PPQ regular Stage-1 quota")
        queue, warehouses, pp = _admit(before, specs, context, selection)
        if len(before.ships) + len(queue) > 999:
            raise UnsupportedPPQEconomy("programmatic ship ID ceiling")
        engine = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            oid: PlayerOrders(player_id=oid) for oid in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            built, receipts = _execute_all_selected(before, specs, queue, 999)
            modeled, events = engine.step(built, noop, seed=seed)
        else:
            intermediate, events = engine.step(before, noop, seed=seed)
            modeled, receipts = _execute_all_selected(
                intermediate, specs, queue, 999,
            )
        # Undo ONLY exact component purchases from a detached projection;
        # then independently reconcile every planet's 14-phase ledger.
        projected = modeled.clone()
        for receipt in receipts:
            pid, sid = receipt.starbase_planet_id, receipt.ship_id
            if sid not in projected.ships:
                raise UnsupportedPPQEconomy("missing built ship")
            projected.ships.pop(sid)
            for field in COST_FIELDS:
                value = getattr(projected.planets[pid].cargo, field)
                if type(value) is not int or value < 0:
                    raise UnsupportedPPQEconomy("invalid final source stock")
                setattr(
                    projected.planets[pid].cargo, field,
                    value + getattr(receipt.purchased, field),
                )
            warehouses[pid] = receipt.warehouse_after
        if (
            len(receipts) != selection.allocated_regular_slots
            or set(modeled.ships) != (
                set(before.ships) | set(selection.lowest_available_ship_id_pool)
            )
            or any(modeled.ships[sid] != old for sid, old in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedPPQEconomy("unexpected ship or starbase changes")
        for receipt in receipts:
            pid = receipt.starbase_planet_id
            design = queue[pid].blueprint
            hull = specs.hulls[design.hull_id]
            planet = before.planets[pid]
            expected = Ship(
                id=receipt.ship_id,
                owner_id=before.starbases[pid].owner_id,
                hull_id=design.hull_id, x=planet.x, y=planet.y,
                engine_id=design.engine_id,
                beam_id=design.beam_id if design.beam_count else None,
                torpedo_id=(design.torpedo_id
                            if design.torpedo_launcher_count else None),
                beam_count=design.beam_count,
                torpedo_launcher_count=design.torpedo_launcher_count,
                fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
            )
            if modeled.ships[receipt.ship_id] != expected:
                raise UnsupportedPPQEconomy("new ship changed unexpectedly")
        balances = _planet_ledgers(before, projected, events)
        if not all(item.resource_balance_exact for item in balances):
            raise UnsupportedPPQEconomy("unbalanced planetary event or resources")
        if pp != tuple(sorted(context.player_pp)):
            raise UnsupportedPPQEconomy("regular shipbuilding unexpectedly changed PP")
        return PPQIntegralEconomicOutcome(
            STATUS, state=modeled,
            selected_bases_by_owner=selection.selected_base_ids_by_owner,
            ship_receipts=receipts,
            player_pp_after=pp,
            base_warehouses_after=tuple(sorted(warehouses.items())),
            planet_balances=balances, economic_events=events,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("incomplete or inconsistent PPQ, BOM, fleet, PP or economy")
