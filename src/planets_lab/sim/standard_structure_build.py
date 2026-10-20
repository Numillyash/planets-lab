"""Conditional fully-funded standard planetary structure construction.

Documented Planets.nu baseline: 1 supply per structure, plus 4 MC
per mine / 3 MC per factory / 10 MC per defense post. Colonist-clan
caps use truncating integer square roots above the published thresholds.
Targets are construction ceilings, not statements of Host orders.

Deliberately UNSUPPORTED in v1: part-funded build queues, auto-selling
supplies to MC, unknown planet owner, campaign modifiers, and actual
NuHost phase ordering. This is a pure research calculation; no mutation
of the supplied Planet or any HostEngine pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from math import isqrt

from planets_lab.core import Planet

STANDARD_STRUCTURE_MC_COST = {
    "defense_posts": 10,
    "factories": 3,
    "mines": 4,
}
BUILD_PRIORITY = ("defense_posts", "factories", "mines")
RESEARCH_STATUS = "CONDITIONAL_FULLY_FUNDED_STANDARD_STRUCTURE_BUILD_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class StructureBuildTargets:
    planet_id: int
    defense_posts: int | None = None
    factories: int | None = None
    mines: int | None = None


@dataclass(frozen=True, slots=True)
class StructureBuildForecast:
    status: str
    resulting_planet: Planet | None = None
    supplied_structures: tuple[tuple[str, int], ...] = ()
    spent_supplies: int = 0
    spent_megacredits: int = 0
    reason: str | None = None
    nuhost_execution_verified: bool = False
    host_phase_position_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == RESEARCH_STATUS


def max_standard_structures(clans: int) -> dict[str, int]:
    if type(clans) is not int or clans < 0:
        raise ValueError("known nonnegative colonist clans required")
    return {
        "mines": clans if clans <= 200 else 200 + isqrt(clans - 200),
        "factories": clans if clans <= 100 else 100 + isqrt(clans - 100),
        "defense_posts": clans if clans <= 50 else 50 + isqrt(clans - 50),
    }


def forecast_standard_structure_build(
    planet: Planet,
    targets: StructureBuildTargets,
    *,
    standard_rules_asserted: bool = False,
) -> StructureBuildForecast:
    """Model ONLY entirely affordable non-converting standard build batches.

    If any requested increase is over cap, insufficiently funded or would
    require supply sale, return ABSTAIN (not a misleading partial forecast).
    Costs are for positive deltas only; existing structures are not charged.
    """
    def abstain(reason: str) -> StructureBuildForecast:
        return StructureBuildForecast("ABSTAIN_UNSUPPORTED_STRUCTURE_BUILD", reason=reason)

    if not standard_rules_asserted:
        return abstain("standard-rules eligibility has not been asserted")
    if type(planet) is not Planet or type(targets) is not StructureBuildTargets:
        return abstain("exact planet and target records required")
    if (type(planet.id) is not int or type(targets.planet_id) is not int
            or planet.id != targets.planet_id or planet.owner_id is None
            or type(planet.owner_id) is not int):
        return abstain("planet identity and known owner required")
    if (type(planet.cargo.supplies) is not int or planet.cargo.supplies < 0
            or type(planet.cargo.megacredits) is not int
            or planet.cargo.megacredits < 0):
        return abstain("complete nonnegative available resources required")
    try:
        caps = max_standard_structures(planet.cargo.clans)
    except ValueError:
        return abstain("valid known colonist population required")

    requested: dict[str, int] = {}
    explicit = False
    for name in BUILD_PRIORITY:
        old = getattr(planet, name)
        want = getattr(targets, name)
        if type(old) is not int or old < 0 or old > caps[name]:
            return abstain("existing structures outside verified standard caps")
        if want is None:
            continue
        explicit = True
        if type(want) is not int or not old <= want <= caps[name]:
            return abstain("unsupported target, downgrade, or population cap")
        requested[name] = want - old
    if not explicit:
        return abstain("no explicit structure target supplied")

    units = sum(requested.values())
    mc = sum(amount * STANDARD_STRUCTURE_MC_COST[name]
             for name, amount in requested.items())
    if units > planet.cargo.supplies or mc > planet.cargo.megacredits:
        return abstain("part-funding or automatic supply sale is outside this subset")

    out = deepcopy(planet)
    for name, amount in requested.items():
        setattr(out, name, getattr(out, name) + amount)
    out.cargo.supplies -= units
    out.cargo.megacredits -= mc
    return StructureBuildForecast(
        RESEARCH_STATUS,
        resulting_planet=out,
        supplied_structures=tuple((name, requested[name]) for name in BUILD_PRIORITY
                                  if name in requested),
        spent_supplies=units,
        spent_megacredits=mc,
    )
