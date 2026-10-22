"""Narrow late PQ/PPQ priority-point selection and quote; no ship built.

Unlike Classic PBP, PQ/PPQ charge 1 + ceil(min(hull_mass,1000)/50)
PP for an ordinary priority ship, by default. Actual priority
arbitration and the random/proportional regular queues are not modeled.
Require exactly ONE explicitly pb1-coded priority request across the
COMPLETE base roster and enough recorded PP to make its selection
uncontested. This is a model-stage admission, NOT server acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.classic_uncontested_priority_pbp import PriorityShipOrder

STATUS = "CONDITIONAL_LATE_PQ_PPQ_SINGLE_PRIORITY_QUOTE_NOT_NUHOST_VERIFIED"
MODES = ("PRODUCTION_PQ", "PLANETARY_PPQ")


@dataclass(frozen=True, slots=True)
class LatePriorityBase:
    planet_id: int
    priority_code: str | None
    order: PriorityShipOrder | None
    cloning: bool = False


@dataclass(frozen=True, slots=True)
class LatePriorityContext:
    mode: str
    soft_ship_limit: int
    player_pp: tuple[tuple[int, int], ...]
    all_bases: tuple[LatePriorityBase, ...]
    complete_fleet_base_and_player_roster_asserted: bool = False
    complete_priority_point_balances_asserted: bool = False
    no_other_priority_or_regular_builds_in_phase_asserted: bool = False
    default_priority_cost_rule_asserted: bool = False


@dataclass(frozen=True, slots=True)
class LatePriorityQuote:
    status: str
    base_planet_id: int | None = None
    proposed_ship_id: int | None = None
    owner_id: int | None = None
    hull_mass: int | None = None
    priority_point_cost: int | None = None
    pp_after: tuple[tuple[int, int], ...] = ()
    reason: str | None = None
    server_selected_priority_slot_verified: bool = False
    server_accepted_order_verified: bool = False
    ship_id_independently_verified: bool = False
    host_phase_order_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def default_pq_ppq_priority_cost(hull_mass: int) -> int | None:
    """Default 1 PP base + 50-KT increments, charged only through 1000 KT."""
    if type(hull_mass) is not int or hull_mass < 1:
        return None
    return 1 + (min(hull_mass, 1000) + 49) // 50


def quote_single_late_priority(
    before: GameState,
    specs: NuStaticSpecs,
    context: LatePriorityContext,
) -> LatePriorityQuote:
    def abstain(reason: str) -> LatePriorityQuote:
        return LatePriorityQuote("ABSTAIN_LATE_PQ_PPQ_PRIORITY_QUOTE", reason=reason)

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not LatePriorityContext
        or context.mode not in MODES
        or type(context.soft_ship_limit) is not int
        or not 1 <= context.soft_ship_limit < 999
        or type(context.player_pp) is not tuple
        or type(context.all_bases) is not tuple
        or context.complete_fleet_base_and_player_roster_asserted is not True
        or context.complete_priority_point_balances_asserted is not True
        or context.no_other_priority_or_regular_builds_in_phase_asserted is not True
        or context.default_priority_cost_rule_asserted is not True
    ):
        return abstain("complete default PQ/PPQ late priority contract missing")
    try:
        before.validate()
        if (
            before.metadata or before.ion_storms
            or len(before.ships) < context.soft_ship_limit
            or len(before.ships) >= 999
            or len(before.starbases) < 2
            or len(context.all_bases) != len(before.starbases)
        ):
            return abstain("not late, globally full, or unusual game context")
        points: dict[int, int] = {}
        for row in context.player_pp:
            if (
                type(row) is not tuple or len(row) != 2
                or type(row[0]) is not int or row[0] not in before.players
                or row[0] in points or type(row[1]) is not int
                or not 0 <= row[1] <= 1000000
            ):
                return abstain("incomplete or invalid PP owner rows")
            points[row[0]] = row[1]
        if set(points) != set(before.players):
            return abstain("not all player PP balances supplied")
        seen: set[int] = set()
        priorities: list[tuple[int, PriorityShipOrder]] = []
        for row in context.all_bases:
            if (
                type(row) is not LatePriorityBase or type(row.planet_id) is not int
                or row.planet_id not in before.starbases or row.planet_id in seen
                or row.cloning is not False
                or row.priority_code not in (None, "pb1")
            ):
                return abstain("duplicate/missing base, unknown pbN or cloning")
            seen.add(row.planet_id)
            base = before.starbases[row.planet_id]
            planet = before.planets.get(row.planet_id)
            if (
                planet is None or base.owner_id != planet.owner_id
                or base.owner_id not in before.players
            ):
                return abstain("starbase/planet owner mismatch")
            if row.priority_code is not None:
                if (
                    type(row.order) is not PriorityShipOrder
                    or type(row.order.allowed_hull_ids) is not frozenset
                ):
                    return abstain("incomplete explicitly prioritized order")
                priorities.append((row.planet_id, row.order))
            elif row.order is not None:
                # This stage cannot decide if ordinary builds are allowed
                # in any pre/post-combat window.
                return abstain("ordinary competing build outside priority-only phase")
        if seen != set(before.starbases) or len(priorities) != 1:
            return abstain("priority arbitration not uniquely established")
        pid, intent = priorities[0]
        hull = specs.hulls.get(intent.blueprint.hull_id)
        price = default_pq_ppq_priority_cost(hull.mass) if hull is not None else None
        if price is None:
            return abstain("missing/unsupported hull for priority quote")
        owner = before.starbases[pid].owner_id
        if points[owner] < price:
            return abstain("not enough PP for an admitted priority build")
        ship_id = next((i for i in range(1, 1000) if i not in before.ships), None)
        if ship_id is None:
            return abstain("no programmatic ship ID available")
        points[owner] -= price
        return LatePriorityQuote(
            STATUS, base_planet_id=pid, proposed_ship_id=ship_id,
            owner_id=owner, hull_mass=hull.mass,
            priority_point_cost=price, pp_after=tuple(sorted(points.items())),
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("unsupported static spec or malformed priority state")
