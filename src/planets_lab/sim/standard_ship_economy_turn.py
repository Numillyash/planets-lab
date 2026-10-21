"""One selected prelimit ship assembly + existing 14-phase planetary economy.

This is an opt-in SINGLE-BASE, SINGLE-SELECTED-SLOT standard research turn.
Explicitly compare assembly-before vs assembly-after the intact economy.
Warehouse, queue selection, hull rights, crew, free ID and complete fleet
remain caller assertions. A source-independent NuHost execution claim is
never possible from model-internal state/receipts alone.

Crucially, independently reconcile (a) old ship/base identity and new
ship spec, (b) warehouse component draws and *only* newly bought prices,
(c) planet stock spent by assembly, (d) existing planetary economy event
ledger after algebraically removing assembly expense from the poststate.
Failure at any point returns ABSTAIN with no partial snapshots/receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
from planets_lab.sim.standard_ship_warehouse_assembly import (
    ComponentUse, SelectedBuildSlot, StandardComponentWarehouse,
    StandardShipAssembly, _decode_rows, assemble_selected_standard_ship,
)

PLACEMENTS = ("selected_assembly_before_planetary", "selected_assembly_after_planetary")
STATUS = "CONDITIONAL_SELECTED_SHIP_ASSEMBLY_WITH_ECONOMY_NOT_NUHOST_VERIFIED"


class UnsupportedShipEconomicTurn(ValueError):
    """Unexplained or unsupported integrated inventory."""


@dataclass(frozen=True, slots=True)
class AssembledShipBalance:
    ship_id: int
    starbase_planet_id: int
    purchased: ResourceCost
    component_ledger: tuple[ComponentUse, ...]
    warehouse_after: StandardComponentWarehouse
    material_debit_exact: bool = True
    warehouse_debit_exact: bool = True
    assembled_ship_exact: bool = True


@dataclass(frozen=True, slots=True)
class SelectedShipEconomicTurn:
    status: str
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    ship_balance: AssembledShipBalance | None = None
    reason: str | None = None
    order_source: str = "CALLER_ASSERTED_UNCONTESTED_SELECTED_PRELIMIT_SLOT_AND_WAREHOUSE"
    independently_verified_queue_order: bool = False
    independently_verified_ship_id: bool = False
    independently_verified_warehouse: bool = False
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False
    nuhost_phase_placement_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def _audit_selected_assembly(
    before: GameState,
    after: GameState,
    assembly: StandardShipAssembly,
    inventory: StandardComponentWarehouse,
    specs: NuStaticSpecs,
    blueprint: StandardShipBlueprint,
    selection: SelectedBuildSlot,
) -> tuple[GameState, AssembledShipBalance]:
    """Verify a component/ship/planet conservation ledger from typed inputs.

    This does not trust an assembly's reported ComponentUse counts, its
    warehouse_after or the new ship as an independent reference.
    """
    if (
        type(assembly) is not StandardShipAssembly
        or not assembly.supported
        or type(assembly.assembled_ship) is not Ship
        or type(assembly.purchased_cost) is not ResourceCost
        or type(assembly.warehouse_after) is not StandardComponentWarehouse
        or type(assembly.component_ledger) is not tuple
        or any((
            assembly.phase_state_turn_advanced,
            assembly.independently_authenticated_warehouse,
            assembly.independently_authenticated_queue_slot,
            assembly.independently_authenticated_ship_id,
            assembly.nuhost_ship_assembly_verified,
            assembly.independent_host_parity_verified,
        ))
    ):
        raise UnsupportedShipEconomicTurn("invalid provenance or missing assembly receipt")
    pid = selection.starbase_planet_id
    ship_id = selection.proposed_ship_id
    if (
        set(after.ships) != set(before.ships) | {ship_id}
        or after.turn != before.turn + 1
        or after.starbases != before.starbases
        or any(after.ships[sid] != old for sid, old in before.ships.items())
    ):
        raise UnsupportedShipEconomicTurn("unexpected ship/base inventory mutation")
    hull = specs.hulls[blueprint.hull_id]
    base = before.starbases[pid]
    planet = before.planets[pid]
    expected_ship = Ship(
        id=ship_id, owner_id=base.owner_id, hull_id=blueprint.hull_id,
        x=planet.x, y=planet.y, engine_id=blueprint.engine_id,
        beam_id=blueprint.beam_id if blueprint.beam_count else None,
        torpedo_id=blueprint.torpedo_id if blueprint.torpedo_launcher_count else None,
        beam_count=blueprint.beam_count,
        torpedo_launcher_count=blueprint.torpedo_launcher_count,
        fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
    )
    if after.ships[ship_id] != expected_ship or assembly.assembled_ship != expected_ship:
        raise UnsupportedShipEconomicTurn("new ship differs from selected exact blueprint")

    demand = (
        ("hulls", blueprint.hull_id, 1, hull.cost),
        ("engines", blueprint.engine_id, hull.engine_count,
         specs.engines[blueprint.engine_id].cost),
    ) + (
        (("beams", blueprint.beam_id, blueprint.beam_count,
          specs.beams[blueprint.beam_id].cost),)
        if blueprint.beam_count else ()
    ) + (
        (("launchers", blueprint.torpedo_id, blueprint.torpedo_launcher_count,
          specs.torpedoes[blueprint.torpedo_id].cost),)
        if blueprint.torpedo_launcher_count else ()
    )
    stock_before = {
        key: _decode_rows(getattr(inventory, key))
        for key in ("hulls", "engines", "beams", "launchers")
    }
    stock_after = {
        key: _decode_rows(getattr(assembly.warehouse_after, key))
        for key in stock_before
    }
    if any(set(stock_before[k]) != set(stock_after[k]) for k in stock_before):
        raise UnsupportedShipEconomicTurn("unexplained warehouse component identities")
    if len(assembly.component_ledger) != len(demand):
        raise UnsupportedShipEconomicTurn("missing or extra component purchase receipts")
    priced = {key: 0 for key in COST_FIELDS}
    for component, (kind, ident, units, unit_cost) in zip(
        assembly.component_ledger, demand, strict=True
    ):
        if type(component) is not ComponentUse:
            raise UnsupportedShipEconomicTurn("untyped component receipt")
        available = stock_before[kind].get(ident, 0)
        drawn = min(available, units)
        purchased = units - drawn
        if (
            (component.kind, component.component_id,
             component.drawn_from_warehouse, component.newly_purchased)
            != (kind, ident, drawn, purchased)
            or stock_after[kind].get(ident, 0) != available - drawn
        ):
            raise UnsupportedShipEconomicTurn("component receipt does not conserve warehouse stock")
        for key in COST_FIELDS:
            price = getattr(unit_cost, key)
            if type(price) is not int or price < 0:
                raise UnsupportedShipEconomicTurn("untrusted component unit price")
            priced[key] += purchased * price
    # No other warehouse component may move or be injected.
    for kind in stock_before:
        used = {ident for item_kind, ident, _, _ in demand if item_kind == kind}
        if any(stock_before[kind][ident] != stock_after[kind][ident]
               for ident in stock_before[kind] if ident not in used):
            raise UnsupportedShipEconomicTurn("unrequested warehouse inventory mutation")
    expected_cost = ResourceCost(**priced)
    if assembly.purchased_cost != expected_cost:
        raise UnsupportedShipEconomicTurn("purchased materials mismatch exact BOM")
    if pid not in after.planets:
        raise UnsupportedShipEconomicTurn("assembly source planet missing")

    # Restore assembly material spending ONLY in a detached projection.
    projected = after.clone()
    for field in COST_FIELDS:
        available = getattr(projected.planets[pid].cargo, field)
        if type(available) is not int or available < 0:
            raise UnsupportedShipEconomicTurn("invalid post-turn material stock")
        setattr(projected.planets[pid].cargo, field, available + priced[field])
    projected.ships.pop(ship_id)
    projected.validate()
    return projected, AssembledShipBalance(
        ship_id=ship_id, starbase_planet_id=pid,
        purchased=expected_cost,
        component_ledger=assembly.component_ledger,
        warehouse_after=assembly.warehouse_after,
    )


def simulate_selected_ship_economy_turn(
    before: GameState,
    specs: NuStaticSpecs,
    blueprint: StandardShipBlueprint,
    warehouse: StandardComponentWarehouse,
    selection: SelectedBuildSlot,
    *,
    placement: Literal[
        "selected_assembly_before_planetary",
        "selected_assembly_after_planetary",
    ],
    allowed_hull_ids: frozenset[int] | None = None,
    standard_rules_asserted: bool = False,
    complete_warehouse_asserted: bool = False,
    hull_eligibility_asserted: bool = False,
    standard_hull_crew_asserted: bool = False,
    no_other_ship_or_base_actions_asserted: bool = False,
    uncontested_single_prelimit_build_asserted: bool = False,
    seed: int = 0,
) -> SelectedShipEconomicTurn:
    def abstain(reason: str) -> SelectedShipEconomicTurn:
        return SelectedShipEconomicTurn("ABSTAIN_SELECTED_SHIP_ECONOMIC_TURN", reason=reason)

    if (
        placement not in PLACEMENTS or type(seed) is not int
        or type(before) is not GameState
        or type(selection) is not SelectedBuildSlot
        or standard_rules_asserted is not True
        or complete_warehouse_asserted is not True
        or hull_eligibility_asserted is not True
        or standard_hull_crew_asserted is not True
        or no_other_ship_or_base_actions_asserted is not True
        or uncontested_single_prelimit_build_asserted is not True
    ):
        return abstain("missing exact standard assumption, slot, or phase placement")
    if before.metadata or before.ion_storms or set(before.starbases) != {selection.starbase_planet_id}:
        return abstain("only a single ordinary starbase with no special interactions is admitted")
    if any(
        s.mission is not None or s.mission1_target_id is not None
        or s.mission2_target_id is not None or s.warp != 0
        or s.damage != 0
        for s in before.ships.values()
    ):
        return abstain("other ship missions or movement are unsupported")
    try:
        before.validate()
        engine = HostEngine(PlanetaryHostPipeline().phases)
        no_ship_actions = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner) for owner in sorted(before.players)
        })
        assembly_options = dict(
            allowed_hull_ids=allowed_hull_ids, standard_rules_asserted=True,
            complete_warehouse_asserted=True,
            hull_eligibility_asserted=True,
            standard_hull_crew_asserted=True,
        )
        if placement == PLACEMENTS[0]:
            built = assemble_selected_standard_ship(
                before, specs, blueprint, warehouse, selection,
                **assembly_options,
            )
            if not built.supported or built.phase_state is None:
                return abstain("unsupported assembly prior to planet economy")
            modeled, events = engine.step(built.phase_state, no_ship_actions, seed=seed)
        else:
            economy, events = engine.step(before, no_ship_actions, seed=seed)
            built = assemble_selected_standard_ship(
                economy, specs, blueprint, warehouse, selection,
                **assembly_options,
            )
            if not built.supported or built.phase_state is None:
                return abstain("unsupported assembly following planet economy")
            modeled = built.phase_state
        projected, assembled = _audit_selected_assembly(
            before, modeled, built, warehouse, specs, blueprint, selection,
        )
        balances = _planet_ledgers(before, projected, events)
    except (
        ValueError, KeyError, TypeError, OverflowError, AttributeError,
        UnsupportedShipEconomicTurn, UnsupportedEconomicLedger,
        UnsupportedPopulationRule,
    ):
        return abstain("unexplained assembly, warehouse or planetary economic inventory")
    return SelectedShipEconomicTurn(
        status=STATUS, state=modeled, events=events,
        planet_balances=balances, ship_balance=assembled,
    )
