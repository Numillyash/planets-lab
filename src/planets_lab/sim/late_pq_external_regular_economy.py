"""Late PQ ordinary build with *external caller-selected* random slot.

A single open soft-cap ship slot, at least two competing queued ordinary
bases, all existing ordinary build-capable starbases and warehouses known.
PQ's random host selection is NEVER generated or asserted causal.
A caller-supplied winning base is a conditional scenario hypothesis.

No priority, clones, mining stations, other ship actions or PP earnings
are modeled. Reuse exact component BOM, ship audit and 14 economic phases.
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
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
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

STATUS = "CONDITIONAL_LATE_PQ_EXTERNAL_SELECTED_SHIP_ECONOMY_NOT_NUHOST_VERIFIED"
PLACEMENTS = (
    "late_pq_build_before_economy",
    "late_pq_build_after_economy",
)


@dataclass(frozen=True, slots=True)
class LatePQBase:
    planet_id: int
    warehouse: StandardComponentWarehouse
    blueprint: StandardShipBlueprint | None = None
    allowed_hull_ids: frozenset[int] | None = None


@dataclass(frozen=True, slots=True)
class LatePQContext:
    soft_ship_limit: int
    selected_planet_id: int
    selected_ship_id: int
    all_bases: tuple[LatePQBase, ...]
    player_pp: tuple[tuple[int, int], ...]
    complete_fleet_planets_all_buildable_bases_and_warehouses_asserted: bool = False
    caller_explicit_random_selected_base_asserted: bool = False
    no_priority_cloning_mining_stations_or_other_actions_asserted: bool = False
    default_regular_zero_pp_no_idle_pp_income_asserted: bool = False


@dataclass(frozen=True, slots=True)
class LatePQOutcome:
    status: str
    state: GameState | None = None
    selected_base_id: int | None = None
    ship_receipt: AssembledShipBalance | None = None
    player_pp_after: tuple[tuple[int, int], ...] = ()
    warehouses_after: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    independently_verified_random_base_choice: bool = False
    independently_verified_ship_id: bool = False
    independently_verified_orders: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedLatePQ(ValueError):
    """Fail closed with no partial ship, PP, warehouses or planet state."""


def _admit(before: GameState, specs: NuStaticSpecs, ctx: LatePQContext) -> tuple[
    CompleteBaseBuild, dict[int, StandardComponentWarehouse], tuple[tuple[int, int], ...]
]:
    before.validate()
    if (
        type(ctx.soft_ship_limit) is not int
        or not 10 <= ctx.soft_ship_limit <= 999
        or type(ctx.selected_planet_id) is not int
        or type(ctx.selected_ship_id) is not int
        or type(ctx.all_bases) is not tuple
        or type(ctx.player_pp) is not tuple
        or not 2 <= len(ctx.all_bases) <= 64
        or len(ctx.all_bases) != len(before.starbases)
        or ctx.complete_fleet_planets_all_buildable_bases_and_warehouses_asserted is not True
        or ctx.caller_explicit_random_selected_base_asserted is not True
        or ctx.no_priority_cloning_mining_stations_or_other_actions_asserted is not True
        or ctx.default_regular_zero_pp_no_idle_pp_income_asserted is not True
        or before.metadata or before.ion_storms
        or len(before.ships) != ctx.soft_ship_limit - 1
        or len(before.ships) >= 999
    ):
        raise UnsupportedLatePQ("not a complete, contested, one-slot late PQ turn")
    lowest = next(
        (sid for sid in range(1, 1000) if sid not in before.ships), None
    )
    if ctx.selected_ship_id != lowest:
        raise UnsupportedLatePQ("selected ship ID differs from lowest free")
    if any(
        type(sid) is not int or type(ship.id) is not int or ship.id != sid
        or ship.warp != 0 or ship.damage != 0
        or ship.mission is not None
        or ship.mission1_target_id is not None
        or ship.mission2_target_id is not None
        for sid, ship in before.ships.items()
    ):
        raise UnsupportedLatePQ("untyped ship or other fleet action")
    pp: dict[int, int] = {}
    for row in ctx.player_pp:
        if (
            type(row) is not tuple or len(row) != 2
            or type(row[0]) is not int or row[0] not in before.players
            or row[0] in pp or type(row[1]) is not int
            or not 0 <= row[1] <= 1000000
        ):
            raise UnsupportedLatePQ("invalid player PP roster")
        pp[row[0]] = row[1]
    if set(pp) != set(before.players):
        raise UnsupportedLatePQ("incomplete owner PP roster")
    stocks: dict[int, StandardComponentWarehouse] = {}
    selected = None
    queued = 0
    for row in ctx.all_bases:
        if (
            type(row) is not LatePQBase or type(row.planet_id) is not int
            or row.planet_id not in before.starbases
            or row.planet_id in stocks
            or type(row.warehouse) is not StandardComponentWarehouse
        ):
            raise UnsupportedLatePQ("duplicate/missing base or stock")
        pid = row.planet_id
        stocks[pid] = row.warehouse
        base = before.starbases[pid]
        planet = before.planets[pid]
        if (
            base.owner_id not in pp or planet.owner_id != base.owner_id
        ):
            raise UnsupportedLatePQ("base and planet owner disagree")
        for kind, catalog in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(i not in catalog for i in _decode_rows(getattr(row.warehouse, kind))):
                raise UnsupportedLatePQ("unknown component at queued or idle base")
        if row.blueprint is None:
            if row.allowed_hull_ids is not None:
                raise UnsupportedLatePQ("idle base has unexplained hull rights")
        else:
            queued += 1
            if (
                type(row.blueprint) is not StandardShipBlueprint
                or type(row.allowed_hull_ids) is not frozenset
                or any(type(i) is not int for i in row.allowed_hull_ids)
                or row.blueprint.hull_id not in row.allowed_hull_ids
                or row.blueprint.hull_id not in specs.hulls
            ):
                raise UnsupportedLatePQ("untrusted queued hull/rights")
        if pid == ctx.selected_planet_id:
            if row.blueprint is None:
                raise UnsupportedLatePQ("externally selected base has no ship queued")
            selected = CompleteBaseBuild(
                blueprint=row.blueprint, warehouse=row.warehouse,
                allowed_hull_ids=row.allowed_hull_ids,
                slot=SelectedBuildSlot(
                    starbase_planet_id=pid,
                    proposed_ship_id=ctx.selected_ship_id,
                    global_ship_limit=ctx.soft_ship_limit,
                    complete_global_ship_roster_asserted=True,
                    queue_selection_asserted=True,
                ),
            )
    if set(stocks) != set(before.starbases) or queued < 2 or selected is None:
        raise UnsupportedLatePQ("not a full multi-candidate PQ random queue")
    return selected, stocks, tuple(sorted(pp.items()))


def simulate_late_pq_external_selected_economic_turn(
    before: GameState, specs: NuStaticSpecs, ctx: LatePQContext,
    *, placement: Literal[
        "late_pq_build_before_economy", "late_pq_build_after_economy",
    ],
    standard_rules_asserted: bool = False,
    full_independent_economic_inventory_asserted: bool = False,
    seed: int = 0,
) -> LatePQOutcome:
    def abstain(reason: str) -> LatePQOutcome:
        return LatePQOutcome("ABSTAIN_LATE_PQ_EXTERNAL_REGULAR_TURN", reason=reason)

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(ctx) is not LatePQContext or type(seed) is not int
        or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or full_independent_economic_inventory_asserted is not True
    ):
        return abstain("missing required late PQ scope")
    try:
        selected, warehouses, pp = _admit(before, specs, ctx)
        queue = {ctx.selected_planet_id: selected}
        engine = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner)
            for owner in sorted(before.players)
        })
        if placement == PLACEMENTS[0]:
            built, receipts = _execute_all_selected(
                before, specs, queue, ctx.soft_ship_limit,
            )
            modeled, events = engine.step(built, noop, seed=seed)
        else:
            intermediate, events = engine.step(before, noop, seed=seed)
            modeled, receipts = _execute_all_selected(
                intermediate, specs, queue, ctx.soft_ship_limit,
            )
        if len(receipts) != 1:
            raise UnsupportedLatePQ("not exactly one ordinary ship")
        receipt = receipts[0]
        pid, sid = receipt.starbase_planet_id, receipt.ship_id
        if (
            pid != ctx.selected_planet_id or sid != ctx.selected_ship_id
            or set(modeled.ships) != set(before.ships) | {sid}
            or any(modeled.ships[i] != old for i, old in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedLatePQ("unexplained ship/base mutations")
        design = selected.blueprint
        hull = specs.hulls[design.hull_id]
        planet = before.planets[pid]
        expected = Ship(
            id=sid, owner_id=before.starbases[pid].owner_id,
            hull_id=design.hull_id, x=planet.x, y=planet.y,
            engine_id=design.engine_id,
            beam_id=design.beam_id if design.beam_count else None,
            torpedo_id=design.torpedo_id if design.torpedo_launcher_count else None,
            beam_count=design.beam_count,
            torpedo_launcher_count=design.torpedo_launcher_count,
            fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
        )
        if modeled.ships[sid] != expected:
            raise UnsupportedLatePQ("wrong final ship identity")
        projection = modeled.clone()
        projection.ships.pop(sid)
        for field in COST_FIELDS:
            amount = getattr(projection.planets[pid].cargo, field)
            if type(amount) is not int or amount < 0:
                raise UnsupportedLatePQ("invalid post-build source stock")
            setattr(
                projection.planets[pid].cargo, field,
                amount + getattr(receipt.purchased, field),
            )
        balances = _planet_ledgers(before, projection, events)
        if not all(x.resource_balance_exact for x in balances):
            raise UnsupportedLatePQ("unbalanced planet economic ledger")
        warehouses[pid] = receipt.warehouse_after
        if tuple(sorted(ctx.player_pp)) != pp:
            raise UnsupportedLatePQ("owner PP unexpectedly changed")
        return LatePQOutcome(
            STATUS, state=modeled,
            selected_base_id=pid, ship_receipt=receipt,
            player_pp_after=pp,
            warehouses_after=tuple(sorted(warehouses.items())),
            planet_balances=balances, economic_events=events,
        )
    except (
        ValueError, TypeError, KeyError, AttributeError, OverflowError,
        UnsupportedPopulationRule, UnsupportedEconomicLedger,
    ):
        return abstain("unverified PQ selection, ship, PP or economic inventory")
