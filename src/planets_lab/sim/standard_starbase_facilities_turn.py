"""Scoped starbase facilities × unmodified planetary economy composition.

Checks that a caller-asserted standard base creation or defense/fighter
purchase conserves every mineral and MegaCredit in the original planet
plus the existing economic phases. The phase may be placed before or
after the fourteen-phase economy block as an explicit MODEL HYPOTHESIS.

No ship construction, armament stockpiles, queue points, starbase tech,
special races/campaigns, actual server order receipts, Host timing or
independent NuHost parity are inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from planets_lab.core import GameState, Starbase
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_starbase_facilities_phase import (
    RESOURCE_KEYS, StandardBaseArmOrder, StandardBaseCreateOrder,
    StandardBaseFacilityOrder, StandardStarbaseFacilitiesPhase,
    STANDARD_BASE_CREATION, STANDARD_BASE_DEFENSE_COST,
    STANDARD_BASE_FIGHTER_COST, UnsupportedStandardStarbaseFacility,
)

FACILITY_PLACEMENTS = ("facilities_before_planetary", "facilities_after_planetary")
STATUS = "CONDITIONAL_STANDARD_BASE_FACILITIES_ECONOMY_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class StarbaseFacilityBalance:
    planet_id: int
    created: bool
    defense_added: int
    fighters_added: int
    spent: tuple[tuple[str, int], ...]
    exact: bool = True


@dataclass(frozen=True, slots=True)
class StandardStarbaseTurnOutcome:
    status: str
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    base_balances: tuple[StarbaseFacilityBalance, ...] = ()
    reason: str | None = None
    order_source: str = "COMPLETE_CALLER_ASSERTED_STARBASE_FACILITY_ORDERS"
    nuhost_order_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def _assert_existing_base_valid(before: GameState) -> None:
    for pid, base in before.starbases.items():
        planet = before.planets.get(pid)
        if (planet is None or planet.owner_id is None
                or planet.owner_id != base.owner_id):
            raise UnsupportedStandardStarbaseFacility("foreign or inconsistent existing starbase")
        if (type(base.defense) is not int or not 0 <= base.defense <= 200
                or type(base.fighters) is not int or not 0 <= base.fighters <= 60
                or any(type(getattr(base, name)) is not int
                       or not 1 <= getattr(base, name) <= 10
                       for name in ("tech_hull", "tech_engine", "tech_beam", "tech_torpedo"))):
            raise UnsupportedStandardStarbaseFacility("unknown existing base defense or tech")


def _audit_base_receipts(
    before: GameState,
    after: GameState,
    events: tuple[HostEvent, ...],
    orders: Mapping[int, tuple[StandardBaseFacilityOrder, ...]],
) -> tuple[GameState, tuple[StarbaseFacilityBalance, ...]]:
    intended: dict[int, StandardBaseFacilityOrder] = {}
    for owner, rows in orders.items():
        for row in rows:
            if row.planet_id in intended:
                raise UnsupportedStandardStarbaseFacility("duplicate intended base order")
            intended[row.planet_id] = row
            if before.planets[row.planet_id].owner_id != owner:
                raise UnsupportedStandardStarbaseFacility("base order owner mismatch")
    observed = [event for event in events if
                event.phase == "standard_starbase_facilities_conditional"]
    if len(observed) != len(intended):
        raise UnsupportedStandardStarbaseFacility("base receipt count disagrees with instructions")
    receipts: dict[int, HostEvent] = {}
    for event in observed:
        if (event.kind not in ("starbase_created_conditional", "starbase_armed_conditional")
                or event.entity_type != "starbase"
                or type(event.entity_id) is not int
                or event.entity_id in receipts
                or event.entity_id not in intended):
            raise UnsupportedStandardStarbaseFacility("unknown or duplicate base receipt")
        receipts[event.entity_id] = event

    projected = after.clone()
    balances: list[StarbaseFacilityBalance] = []
    if set(after.starbases) != set(before.starbases) | {
        pid for pid, order in intended.items() if type(order) is StandardBaseCreateOrder
    }:
        raise UnsupportedStandardStarbaseFacility("starbase roster changed without order")
    for pid in sorted(intended):
        order = intended[pid]
        old = before.starbases.get(pid)
        new = after.starbases.get(pid)
        if new is None:
            raise UnsupportedStandardStarbaseFacility("missing built or armed starbase")
        if type(order) is StandardBaseCreateOrder:
            if old is not None:
                raise UnsupportedStandardStarbaseFacility("duplicate creation")
            expected = Starbase(planet_id=pid, owner_id=before.planets[pid].owner_id)
            defense = fighters = 0
            costs = dict(STANDARD_BASE_CREATION)
            event_kind = "starbase_created_conditional"
        else:
            if old is None or type(order) is not StandardBaseArmOrder:
                raise UnsupportedStandardStarbaseFacility("missing expected pre-existing base")
            defense = (old.defense if order.defense_target is None
                       else order.defense_target) - old.defense
            fighters = (old.fighters if order.fighter_target is None
                        else order.fighter_target) - old.fighters
            if defense < 0 or fighters < 0 or not (defense or fighters):
                raise UnsupportedStandardStarbaseFacility("unexpected negative or empty base increase")
            costs = {
                key: dict(STANDARD_BASE_DEFENSE_COST).get(key, 0) * defense
                + dict(STANDARD_BASE_FIGHTER_COST).get(key, 0) * fighters
                for key in RESOURCE_KEYS
            }
            from dataclasses import replace
            expected = replace(
                old, defense=old.defense + defense, fighters=old.fighters + fighters,
            )
            event_kind = "starbase_armed_conditional"
        if new != expected:
            raise UnsupportedStandardStarbaseFacility("base state does not match purchased units")
        event = receipts[pid]
        fields = dict(event.details)
        required = {
            "planet_id", "defense_added", "fighters_added",
            *(("spent_" + key) for key in RESOURCE_KEYS),
        }
        if (len(event.details) != len(required)
                or set(fields) != required
                or event.kind != event_kind
                or fields["planet_id"] != str(pid)
                or fields["defense_added"] != str(defense)
                or fields["fighters_added"] != str(fighters)
                or any(fields["spent_" + key] != str(costs.get(key, 0))
                       for key in RESOURCE_KEYS)):
            raise UnsupportedStandardStarbaseFacility("base event disagrees with exact purchase")
        for key in RESOURCE_KEYS:
            value = getattr(projected.planets[pid].cargo, key)
            if type(value) is not int or value < 0:
                raise UnsupportedStandardStarbaseFacility("bad poststate base spending balance")
            setattr(projected.planets[pid].cargo, key, value + costs.get(key, 0))
        balances.append(StarbaseFacilityBalance(
            planet_id=pid, created=old is None,
            defense_added=defense, fighters_added=fighters,
            spent=tuple((key, costs.get(key, 0)) for key in RESOURCE_KEYS),
        ))
    for pid in before.starbases.keys() - intended.keys():
        if before.starbases[pid] != after.starbases[pid]:
            raise UnsupportedStandardStarbaseFacility("unrequested base mutation")
    return projected, tuple(balances)


def simulate_standard_starbase_facilities_turn(
    before: GameState,
    facilities_by_owner: Mapping[int, tuple[StandardBaseFacilityOrder, ...]],
    *,
    placement: Literal["facilities_before_planetary", "facilities_after_planetary"],
    standard_rules_asserted: bool = False,
    complete_owner_facility_scope_asserted: bool = False,
    seed: int = 0,
) -> StandardStarbaseTurnOutcome:
    """One completely stated model-only starbase/economy turn, no partials."""
    def abstain(reason: str) -> StandardStarbaseTurnOutcome:
        return StandardStarbaseTurnOutcome(
            status="ABSTAIN_STANDARD_STARBASE_FACILITIES_TURN", reason=reason,
        )

    if (type(before) is not GameState or type(seed) is not int
            or standard_rules_asserted is not True
            or complete_owner_facility_scope_asserted is not True
            or placement not in FACILITY_PLACEMENTS
            or type(facilities_by_owner) is not dict
            or set(facilities_by_owner) != set(before.players)):
        return abstain("unsupported standard context or incomplete owner scope")
    if before.ships or before.ion_storms or before.metadata:
        return abstain("unmodeled ship, storm or variant context")
    try:
        before.validate()
        _assert_existing_base_valid(before)
        facility_phase = StandardStarbaseFacilitiesPhase(facilities_by_owner)
        for owner, orders in facilities_by_owner.items():
            if type(owner) is not int or type(orders) is not tuple:
                raise UnsupportedStandardStarbaseFacility("malformed owner facility orders")
        phases = PlanetaryHostPipeline().phases
        ordered = ((facility_phase, *phases) if placement == FACILITY_PLACEMENTS[0]
                   else (*phases, facility_phase))
        noop = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner) for owner in sorted(before.players)
        })
        after, events = HostEngine(ordered).step(before, noop, seed=seed)
        projected, base_balances = _audit_base_receipts(
            before, after, events, facilities_by_owner,
        )
        planet_balances = _planet_ledgers(before, projected, events)
    except (
        ValueError, KeyError, TypeError, OverflowError, AttributeError,
        UnsupportedStandardStarbaseFacility, UnsupportedPopulationRule,
        UnsupportedEconomicLedger,
    ):
        return abstain("unsupported base purchase or unexplained local economic delta")
    return StandardStarbaseTurnOutcome(
        status=STATUS,
        state=after, events=events,
        planet_balances=planet_balances, base_balances=base_balances,
    )
