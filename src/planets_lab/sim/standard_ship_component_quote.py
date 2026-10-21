"""Exact standard NEW-COMPONENT ship material quote (no build execution).

This computes a hypothetical freshly purchased hull + ALL required
engines + specified beam/launcher equipment for one complete design.
No ship is created, no resources spent, no warehouse inventory, queue,
ship limit, priority point, race-specific hull license or Host sequence
is inferred. Race hull eligibility must be explicitly caller asserted.

Actual starbase shipbuilding requires an independent order/warehouse/
queue/slot/ship-ID contract. This unit remains DOCUMENTED arithmetic and
TESTED local calculation, NOT a NuHost order-acceptance receipt.
"""
from __future__ import annotations

from dataclasses import dataclass

from planets_lab.core import Planet, Starbase
from planets_lab.data.nu_specs import NuStaticSpecs, ResourceCost

COST_FIELDS = ("megacredits", "duranium", "tritanium", "molybdenum")
QUOTE_STATUS = "CONDITIONAL_NEW_COMPONENT_STARSHIP_BOM_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class StandardShipBlueprint:
    hull_id: int
    engine_id: int
    beam_id: int | None = None
    beam_count: int = 0
    torpedo_id: int | None = None
    torpedo_launcher_count: int = 0


@dataclass(frozen=True, slots=True)
class StandardShipQuote:
    status: str
    cost: ResourceCost | None = None
    shortfalls: tuple[tuple[str, int], ...] = ()
    hull_count: int = 0
    engine_count: int = 0
    beam_count: int = 0
    torpedo_launcher_count: int = 0
    affordable_from_surface: bool = False
    reason: str | None = None
    warehouse_inventory_verified: bool = False
    race_build_rights_independently_verified: bool = False
    actual_ship_build_queue_verified: bool = False
    ship_limit_and_priority_verified: bool = False
    ship_id_allocated: bool = False
    nuhost_order_execution_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == QUOTE_STATUS


def quote_standard_new_component_ship(
    planet: Planet,
    base: Starbase,
    specs: NuStaticSpecs,
    blueprint: StandardShipBlueprint,
    *,
    allowed_hull_ids: frozenset[int] | None = None,
    standard_rules_asserted: bool = False,
    no_warehouse_parts_used_asserted: bool = False,
    hull_eligibility_asserted: bool = False,
) -> StandardShipQuote:
    def abstain(reason: str) -> StandardShipQuote:
        return StandardShipQuote("ABSTAIN_STANDARD_SHIP_COMPONENT_QUOTE", reason=reason)

    if (standard_rules_asserted is not True
            or no_warehouse_parts_used_asserted is not True
            or hull_eligibility_asserted is not True):
        return abstain("explicit standard, no-storage and hull-eligibility declarations required")
    if (type(planet) is not Planet or type(base) is not Starbase
            or type(specs) is not NuStaticSpecs
            or type(blueprint) is not StandardShipBlueprint
            or type(allowed_hull_ids) is not frozenset
            or not allowed_hull_ids
            or any(type(x) is not int or x <= 0 for x in allowed_hull_ids)):
        return abstain("complete exact typed design and allowed hull set required")
    if (type(planet.id) is not int or planet.owner_id is None
            or type(planet.owner_id) is not int
            or base.planet_id != planet.id or base.owner_id != planet.owner_id):
        return abstain("matched same-owner planet and starbase required")
    if (any(type(getattr(base, field)) is not int
            or not 1 <= getattr(base, field) <= 10 for field in (
                "tech_hull", "tech_engine", "tech_beam", "tech_torpedo",
            ))
            or any(type(getattr(planet.cargo, field)) is not int
                   or getattr(planet.cargo, field) < 0 for field in COST_FIELDS)):
        return abstain("complete standard base technology and planet surface stock required")
    if (type(blueprint.hull_id) is not int
            or type(blueprint.engine_id) is not int
            or blueprint.hull_id not in allowed_hull_ids
            or type(blueprint.beam_count) is not int or blueprint.beam_count < 0
            or type(blueprint.torpedo_launcher_count) is not int
            or blueprint.torpedo_launcher_count < 0):
        return abstain("unlicensed hull or invalid component counts")
    hull = specs.hulls.get(blueprint.hull_id)
    engine = specs.engines.get(blueprint.engine_id)
    if (hull is None or engine is None or hull.special
            or hull.id != blueprint.hull_id or engine.id != blueprint.engine_id
            or type(hull.engine_count) is not int or hull.engine_count < 1
            or type(hull.beam_count) is not int or hull.beam_count < 0
            or type(hull.torpedo_launcher_count) is not int
            or hull.torpedo_launcher_count < 0
            or hull.tech_level > base.tech_hull or engine.tech_level > base.tech_engine
            or hull.tech_level < 1 or engine.tech_level < 1):
        return abstain("unknown or unsupported hull/engine or insufficient base tech")
    if (blueprint.beam_count > hull.beam_count
            or blueprint.torpedo_launcher_count > hull.torpedo_launcher_count):
        return abstain("more installed weapons than hull slots")
    # Every hull's fixed engine-count is purchased, never allow partial engines.
    parts = [(hull.cost, 1), (engine.cost, hull.engine_count)]
    for count, ident, library, maximum in (
        (blueprint.beam_count, blueprint.beam_id, specs.beams, base.tech_beam),
        (blueprint.torpedo_launcher_count, blueprint.torpedo_id,
         specs.torpedoes, base.tech_torpedo),
    ):
        if count == 0:
            if ident is not None:
                return abstain("component identifier with zero slots")
            continue
        if type(ident) is not int or ident <= 0:
            return abstain("missing weapon identifier with populated slots")
        component = library.get(ident)
        if (component is None or component.id != ident
                or type(component.tech_level) is not int
                or not 1 <= component.tech_level <= maximum):
            return abstain("unknown or tech-locked weapon component")
        parts.append((component.cost, count))
    total: dict[str, int] = {field: 0 for field in COST_FIELDS}
    for cost, count in parts:
        if type(cost) is not ResourceCost:
            return abstain("unknown material price")
        for name in COST_FIELDS:
            unit = getattr(cost, name)
            if type(unit) is not int or unit < 0:
                return abstain("invalid or missing standard component price")
            total[name] += unit * count
    required = ResourceCost(**total)
    deficits = tuple(
        (name, max(0, total[name] - getattr(planet.cargo, name)))
        for name in COST_FIELDS
    )
    return StandardShipQuote(
        status=QUOTE_STATUS,
        cost=required,
        shortfalls=deficits,
        hull_count=1,
        engine_count=hull.engine_count,
        beam_count=blueprint.beam_count,
        torpedo_launcher_count=blueprint.torpedo_launcher_count,
        affordable_from_surface=all(value == 0 for _, value in deficits),
    )
