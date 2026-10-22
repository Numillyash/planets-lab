"""Early unthrottled PQ/PPQ: ordinary ships AND selected idle-base PP.

Different from late priority construction (#266/267), this model ONLY
admits a complete ordinary-starbase roster safely below 90% of the
caller-asserted soft cap. Every ordinary base is selected in the
unthrottled stage; a queued base builds an ordinary ship at ZERO PP
cost and an idle, build-capable base earns the default 2 PP.

The source-independent rule for which starbase gets each lowest free
ship ID is NOT inferred: the caller explicitly supplies per-base IDs
whose SET must equal the lowest N free IDs. Sorted local execution
must never be confused with NuHost random PQ/PPQ scheduling.
The entire assembly and 14-phase economic turn ABSTAIN atomically
for unknown PP earning, caps, stocks, receipt or special interactions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, _planet_ledgers,
)
from planets_lab.sim.standard_ship_component_quote import COST_FIELDS
from planets_lab.sim.standard_ship_economy_turn import AssembledShipBalance
from planets_lab.sim.standard_ship_warehouse_assembly import (
    StandardComponentWarehouse, _decode_rows, QUEUE_HYPOTHESIS,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, _execute_all_selected,
)
from planets_lab.sim.late_pq_ppq_priority_admission import MODES

STATUS = "CONDITIONAL_EARLY_PQ_PPQ_BUILD_AND_IDLE_PP_NOT_NUHOST_VERIFIED"
PLACEMENTS = ("early_builds_before_economy", "early_builds_after_economy")


@dataclass(frozen=True, slots=True)
class EarlyOrdinaryBase:
    planet_id: int
    queued: CompleteBaseBuild | None
    # Even an idle base must have a complete and checked inventory.
    idle_warehouse: StandardComponentWarehouse | None = None


@dataclass(frozen=True, slots=True)
class EarlyPPContext:
    queue_mode: str
    soft_ship_limit: int
    player_pp: tuple[tuple[int, int], ...]
    all_bases: tuple[EarlyOrdinaryBase, ...]
    complete_fleet_owner_base_and_inventory_asserted: bool = False
    all_ordinary_starbases_selected_asserted: bool = False
    default_two_pp_per_idle_selected_base_asserted: bool = False
    no_priority_clone_regular_contention_or_other_actions_asserted: bool = False


@dataclass(frozen=True, slots=True)
class EarlyPPOutcome:
    status: str
    state: GameState | None = None
    ship_receipts: tuple[AssembledShipBalance, ...] = ()
    player_pp_after: tuple[tuple[int, int], ...] = ()
    base_warehouses_after: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    idle_pp_credits: tuple[tuple[int, int, int], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    real_starbase_selection_verified: bool = False
    real_ship_id_assignment_verified: bool = False
    independently_accepted_pp_earnings_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedEarlyPP(ValueError):
    """Invalid per-base selection or inventory; whole-turn abstention."""


def _admit(
    before: GameState, specs: NuStaticSpecs, ctx: EarlyPPContext,
) -> tuple[dict[int, CompleteBaseBuild], dict[int, StandardComponentWarehouse],
           dict[int, int], tuple[tuple[int, int, int], ...]]:
    if (
        ctx.queue_mode not in MODES
        or type(ctx.soft_ship_limit) is not int
        or not 10 <= ctx.soft_ship_limit <= 999
        or type(ctx.player_pp) is not tuple or type(ctx.all_bases) is not tuple
        or not 2 <= len(ctx.all_bases) <= 64
        or len(ctx.all_bases) != len(before.starbases)
        or ctx.complete_fleet_owner_base_and_inventory_asserted is not True
        or ctx.all_ordinary_starbases_selected_asserted is not True
        or ctx.default_two_pp_per_idle_selected_base_asserted is not True
        or ctx.no_priority_clone_regular_contention_or_other_actions_asserted is not True
        or before.metadata or before.ion_storms
    ):
        raise UnsupportedEarlyPP("unknown early queue mode, base count, custom rules or assumptions")
    pp: dict[int, int] = {}
    for row in ctx.player_pp:
        if (
            type(row) is not tuple or len(row) != 2
            or type(row[0]) is not int or row[0] not in before.players
            or row[0] in pp or type(row[1]) is not int
            or not 0 <= row[1] <= 1000000
        ):
            raise UnsupportedEarlyPP("invalid or incomplete player PP balances")
        pp[row[0]] = row[1]
    if set(pp) != set(before.players):
        raise UnsupportedEarlyPP("missing PP owner balance")
    queued: dict[int, CompleteBaseBuild] = {}
    warehouses: dict[int, StandardComponentWarehouse] = {}
    credits: list[tuple[int, int, int]] = []
    seen: set[int] = set()
    for row in ctx.all_bases:
        if (
            type(row) is not EarlyOrdinaryBase
            or type(row.planet_id) is not int
            or row.planet_id not in before.starbases
            or row.planet_id in seen
        ):
            raise UnsupportedEarlyPP("unknown or duplicate ordinary base")
        seen.add(row.planet_id)
        base = before.starbases[row.planet_id]
        planet = before.planets.get(row.planet_id)
        if (
            planet is None or base.owner_id != planet.owner_id
            or base.owner_id not in pp
        ):
            raise UnsupportedEarlyPP("base and planet ownership disagreement")
        if row.queued is not None:
            build = row.queued
            if (
                type(build) is not CompleteBaseBuild
                or build.slot.starbase_planet_id != row.planet_id
                or build.slot.global_ship_limit != ctx.soft_ship_limit
                or build.slot.queue_hypothesis != QUEUE_HYPOTHESIS
                or build.slot.complete_global_ship_roster_asserted is not True
                or build.slot.queue_selection_asserted is not True
                or type(build.warehouse) is not StandardComponentWarehouse
                or type(build.allowed_hull_ids) is not frozenset
                or row.idle_warehouse is not None
            ):
                raise UnsupportedEarlyPP("inconsistent selected ordinary build slot")
            queued[row.planet_id] = build
            warehouses[row.planet_id] = build.warehouse
        else:
            if type(row.idle_warehouse) is not StandardComponentWarehouse:
                raise UnsupportedEarlyPP("missing idle selected-base warehouse")
            warehouses[row.planet_id] = row.idle_warehouse
            pp[base.owner_id] += 2
            if pp[base.owner_id] > 1000000:
                raise UnsupportedEarlyPP("PP exceeds bounded state")
            credits.append((row.planet_id, base.owner_id, 2))
    if (
        seen != set(before.starbases) or not queued or not credits
        or len(before.ships) + len(queued) > 999
        or 10 * (len(before.ships) + len(queued))
           >= 9 * ctx.soft_ship_limit
    ):
        raise UnsupportedEarlyPP("not the common unthrottled early build interval")
    for stock in warehouses.values():
        for kind, catalog in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(component_id not in catalog
                   for component_id in _decode_rows(getattr(stock, kind))):
                raise UnsupportedEarlyPP("unknown warehouse component, even at idle base")
    expected_ids = [
        sid for sid in range(1, 1000) if sid not in before.ships
    ][:len(queued)]
    provided = [build.slot.proposed_ship_id for build in queued.values()]
    if (
        any(type(sid) is not int for sid in provided)
        or len(set(provided)) != len(provided)
        or set(provided) != set(expected_ids)
    ):
        raise UnsupportedEarlyPP("assigned IDs do not equal N lowest free ship numbers")
    if any(
        ship.warp != 0 or ship.damage != 0 or ship.mission is not None
        or ship.mission1_target_id is not None
        or ship.mission2_target_id is not None
        for ship in before.ships.values()
    ):
        raise UnsupportedEarlyPP("ship missions and combat are out of scope")
    return queued, warehouses, pp, tuple(sorted(credits))


def simulate_unthrottled_pq_ppq_idle_pp_turn(
    before: GameState,
    specs: NuStaticSpecs,
    context: EarlyPPContext,
    *,
    placement: Literal[
        "early_builds_before_economy",
        "early_builds_after_economy",
    ],
    standard_rules_asserted: bool = False,
    complete_component_rights_and_inventory_asserted: bool = False,
    no_external_pp_income_or_other_host_actions_asserted: bool = False,
    seed: int = 0,
) -> EarlyPPOutcome:
    def abstain(reason: str) -> EarlyPPOutcome:
        return EarlyPPOutcome("ABSTAIN_EARLY_PQ_PPQ_IDLE_PP", reason=reason)

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not EarlyPPContext
        or type(seed) is not int or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_component_rights_and_inventory_asserted is not True
        or no_external_pp_income_or_other_host_actions_asserted is not True
    ):
        return abstain("missing explicit default early PQ/PPQ scope")
    try:
        before.validate()
        selected, warehouses, after_pp, credits = _admit(before, specs, context)
        economics = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner) for owner in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            built, receipts = _execute_all_selected(
                before, specs, selected, context.soft_ship_limit,
            )
            modeled, events = economics.step(built, noop, seed=seed)
        else:
            economy, events = economics.step(before, noop, seed=seed)
            modeled, receipts = _execute_all_selected(
                economy, specs, selected, context.soft_ship_limit,
            )
        projection = modeled.clone()
        for receipt in receipts:
            if receipt.ship_id not in projection.ships:
                raise UnsupportedEarlyPP("missing built ship")
            pid = receipt.starbase_planet_id
            projection.ships.pop(receipt.ship_id)
            for name in COST_FIELDS:
                value = getattr(projection.planets[pid].cargo, name)
                if type(value) is not int or value < 0:
                    raise UnsupportedEarlyPP("invalid surface stock")
                setattr(projection.planets[pid].cargo, name,
                        value + getattr(receipt.purchased, name))
            warehouses[pid] = receipt.warehouse_after
        if (
            set(modeled.ships) != set(before.ships) | {r.ship_id for r in receipts}
            or any(modeled.ships[sid] != old for sid, old in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedEarlyPP("unexplained ship/base identity mutation")
        # Reconstruct final new ships independently of the source receipt.
        for receipt in receipts:
            pid = receipt.starbase_planet_id
            design = selected[pid].blueprint
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
                raise UnsupportedEarlyPP("new ship changed after warehouse purchase")
        balances = _planet_ledgers(before, projection, events)
        if not all(row.resource_balance_exact for row in balances):
            raise UnsupportedEarlyPP("planet economy event/stock mismatch")
        # PP earnings are tied to the complete *idle* base roster only;
        # constructed ships do not earn or spend PP in this early mode.
        initial_pp = dict(context.player_pp)
        credits_by_owner: dict[int, int] = {
            owner: sum(value for _, oid, value in credits if oid == owner)
            for owner in initial_pp
        }
        if any(
            after_pp[owner] != initial_pp[owner] + credits_by_owner[owner]
            for owner in initial_pp
        ):
            raise UnsupportedEarlyPP("PP credit ledger did not balance")
        return EarlyPPOutcome(
            STATUS, state=modeled, ship_receipts=receipts,
            player_pp_after=tuple(sorted(after_pp.items())),
            base_warehouses_after=tuple(sorted(warehouses.items())),
            idle_pp_credits=credits,
            planet_balances=balances, economic_events=events,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("unsupported early PQ/PPQ idle-point or ship/economy inventory")
