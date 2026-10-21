"""Bounded model-only ONE starship assembly from typed component warehouse.

The queue selector, hull rights, proposed ship ID and entire starting
warehouse are caller assertions, NOT source-independent NuHost evidence.
Only a previously *selected* PRELIMIT standard build slot is supported.
This does not implement PBQ/PQ/PPQ/PLS arbitration, priority points,
cloning, faction variants, auto-tech, recycling or automatic ID allocation.

Returns a cloned PHASE-INTERMEDIATE state with unchanged turn number;
it is not a complete Host turn. No partial output when unsupported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs, ResourceCost
from planets_lab.sim.standard_ship_component_quote import (
    COST_FIELDS, StandardShipBlueprint, quote_standard_new_component_ship,
)

MODEL_STATUS = "CONDITIONAL_SELECTED_PRELIMIT_SHIP_ASSEMBLY_NOT_NUHOST_VERIFIED"
QUEUE_HYPOTHESIS = "CALLER_SELECTED_PRELIMIT_STANDARD_SLOT"
WAREHOUSE_FIELDS = ("hulls", "engines", "beams", "launchers")


@dataclass(frozen=True, slots=True)
class StandardComponentWarehouse:
    """Complete, explicit per-base stock. (component_id, quantity) pairs.

    Distinct from canonical Starbase, which has no warehouse storage.
    """
    hulls: tuple[tuple[int, int], ...] = ()
    engines: tuple[tuple[int, int], ...] = ()
    beams: tuple[tuple[int, int], ...] = ()
    launchers: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class SelectedBuildSlot:
    """Hypothetical queue result, never an inferred server decision."""
    starbase_planet_id: int
    proposed_ship_id: int
    global_ship_limit: int
    queue_hypothesis: str = QUEUE_HYPOTHESIS
    complete_global_ship_roster_asserted: bool = False
    queue_selection_asserted: bool = False


@dataclass(frozen=True, slots=True)
class ComponentUse:
    kind: str
    component_id: int
    drawn_from_warehouse: int
    newly_purchased: int


@dataclass(frozen=True, slots=True)
class StandardShipAssembly:
    status: str
    phase_state: GameState | None = None
    warehouse_after: StandardComponentWarehouse | None = None
    assembled_ship: Ship | None = None
    purchased_cost: ResourceCost | None = None
    component_ledger: tuple[ComponentUse, ...] = ()
    reason: str | None = None
    phase_state_turn_advanced: bool = False
    independently_authenticated_warehouse: bool = False
    independently_authenticated_queue_slot: bool = False
    independently_authenticated_ship_id: bool = False
    nuhost_ship_assembly_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == MODEL_STATUS


class UnsupportedWarehouseBuild(ValueError):
    """No partial ship, inventory or debits may be returned."""


def _decode_rows(rows: Any) -> dict[int, int]:
    if type(rows) is not tuple:
        raise UnsupportedWarehouseBuild("warehouse must be a finite tuple")
    if len(rows) > 2000:
        raise UnsupportedWarehouseBuild("warehouse entry count too large")
    result: dict[int, int] = {}
    for pair in rows:
        if (type(pair) is not tuple or len(pair) != 2
                or type(pair[0]) is not int or pair[0] <= 0
                or type(pair[1]) is not int or pair[1] < 0
                or pair[0] in result):
            raise UnsupportedWarehouseBuild("invalid/duplicate component stock")
        result[pair[0]] = pair[1]
    return result


def _add_component_cost(
    total: dict[str, int], cost: ResourceCost, count: int,
) -> None:
    if type(cost) is not ResourceCost or type(count) is not int or count < 0:
        raise UnsupportedWarehouseBuild("invalid new component price/quantity")
    for name in COST_FIELDS:
        unit = getattr(cost, name)
        if type(unit) is not int or unit < 0:
            raise UnsupportedWarehouseBuild("invalid material unit price")
        total[name] += unit * count


def assemble_selected_standard_ship(
    before: GameState,
    specs: NuStaticSpecs,
    blueprint: StandardShipBlueprint,
    warehouse: StandardComponentWarehouse,
    selection: SelectedBuildSlot,
    *,
    allowed_hull_ids: frozenset[int] | None = None,
    standard_rules_asserted: bool = False,
    complete_warehouse_asserted: bool = False,
    hull_eligibility_asserted: bool = False,
    standard_hull_crew_asserted: bool = False,
) -> StandardShipAssembly:
    """Perform exactly ONE conditional assembly and its source-stock debit.

    A selected prelimit queue position and free ship ID are **inputs**.
    Passing the assertions does not authenticate that the server selected
    that base or allocated that ID. No shipbuilding arbitration is modeled.
    """
    def abstain(reason: str) -> StandardShipAssembly:
        return StandardShipAssembly("ABSTAIN_STANDARD_SHIP_ASSEMBLY", reason=reason)

    if not (
        standard_rules_asserted is True
        and complete_warehouse_asserted is True
        and hull_eligibility_asserted is True
        and standard_hull_crew_asserted is True
        and type(before) is GameState
        and type(specs) is NuStaticSpecs
        and type(blueprint) is StandardShipBlueprint
        and type(warehouse) is StandardComponentWarehouse
        and type(selection) is SelectedBuildSlot
        and type(selection.starbase_planet_id) is int
        and type(selection.proposed_ship_id) is int
        and 1 <= selection.proposed_ship_id <= 999
        and type(selection.global_ship_limit) is int
        and 1 <= selection.global_ship_limit <= 999
        and selection.queue_hypothesis == QUEUE_HYPOTHESIS
        and selection.complete_global_ship_roster_asserted is True
        and selection.queue_selection_asserted is True
    ):
        return abstain("full standard, warehouse, queue and crew declarations required")
    if before.metadata or before.ion_storms:
        return abstain("unmodeled game variants or storm interactions")
    try:
        before.validate()
    except (ValueError, TypeError, AttributeError):
        return abstain("invalid canonical prestate")
    pid = selection.starbase_planet_id
    if (pid not in before.starbases or pid not in before.planets
            or selection.proposed_ship_id in before.ships
            or len(before.ships) >= selection.global_ship_limit):
        return abstain("no matching selected base, free ship ID or prelimit slot")
    base = before.starbases[pid]
    planet = before.planets[pid]
    quote = quote_standard_new_component_ship(
        planet, base, specs, blueprint,
        allowed_hull_ids=allowed_hull_ids,
        standard_rules_asserted=True,
        # The quote represents the all-new COMPONENT BASELINE. Actual
        # procurement below explicitly subtracts existing warehouse stock.
        no_warehouse_parts_used_asserted=True,
        hull_eligibility_asserted=True,
    )
    if not quote.supported or quote.cost is None:
        return abstain("unknown/unsupported baseline component BOM")

    hull = specs.hulls[blueprint.hull_id]
    if (type(hull.crew) is not int or hull.crew < 0
            or type(hull.fighter_bay_count) is not int
            or hull.fighter_bay_count < 0):
        return abstain("unknown standard hull crew or fighter bays")

    try:
        stock = {
            name: _decode_rows(getattr(warehouse, name))
            for name in WAREHOUSE_FIELDS
        }
        for name, library in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(component_id not in library for component_id in stock[name]):
                raise UnsupportedWarehouseBuild("warehouse contains catalog-unknown components")
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
        price: dict[str, int] = {name: 0 for name in COST_FIELDS}
        ledger: list[ComponentUse] = []
        for kind, comp_id, required, unit_cost in demand:
            available = stock[kind].get(comp_id, 0)
            drawn = min(available, required)
            buy = required - drawn
            stock[kind][comp_id] = available - drawn
            _add_component_cost(price, unit_cost, buy)
            ledger.append(ComponentUse(kind, comp_id, drawn, buy))
        for name in COST_FIELDS:
            current = getattr(planet.cargo, name)
            if type(current) is not int or current < price[name]:
                raise UnsupportedWarehouseBuild("insufficient planet resources")

        after = before.clone()
        for name in COST_FIELDS:
            setattr(after.planets[pid].cargo, name,
                    getattr(after.planets[pid].cargo, name) - price[name])
        ship = Ship(
            id=selection.proposed_ship_id,
            owner_id=base.owner_id,
            hull_id=blueprint.hull_id,
            x=planet.x, y=planet.y,
            engine_id=blueprint.engine_id,
            beam_id=blueprint.beam_id if blueprint.beam_count else None,
            torpedo_id=(blueprint.torpedo_id
                        if blueprint.torpedo_launcher_count else None),
            beam_count=blueprint.beam_count,
            torpedo_launcher_count=blueprint.torpedo_launcher_count,
            fighter_bay_count=hull.fighter_bay_count,
            crew=hull.crew,
        )
        after.ships[ship.id] = ship
        after.validate()
        remaining = StandardComponentWarehouse(**{
            name: tuple(sorted(items.items()))
            for name, items in stock.items()
        })
        actual_cost = ResourceCost(**price)
        # Independent local balance controls: no storage count below zero;
        # stock depletion+new purchasing matches each component demand;
        # all resource deltas equal the exact new-component price only.
        for item, (_, _, required, _) in zip(ledger, demand, strict=True):
            if item.drawn_from_warehouse + item.newly_purchased != required:
                raise UnsupportedWarehouseBuild("component unit balance unexplained")
        if any(
            getattr(before.planets[pid].cargo, name)
            - getattr(after.planets[pid].cargo, name) != price[name]
            for name in COST_FIELDS
        ):
            raise UnsupportedWarehouseBuild("material debit did not balance")
    except (UnsupportedWarehouseBuild, ValueError, TypeError,
            AttributeError, KeyError, OverflowError):
        return abstain("unmodeled or unbalanced component inventory/price")
    return StandardShipAssembly(
        status=MODEL_STATUS,
        phase_state=after,
        warehouse_after=remaining,
        assembled_ship=ship,
        purchased_cost=actual_cost,
        component_ledger=tuple(ledger),
    )
