"""Conditional late PQ soft-capped ordinary queue: no builds, full economy.

Contrasts the explicit external-loss #272 case: here NO vessel is lost
between consecutive turns. With a complete fleet AT the soft limit,
ordinary PQ requests cannot consume a regular vacancy. Priority-coded
builds, cloning, Mining Stations, additional Host actions and nondefault
PP earnings are excluded by explicit complete-scope assertions.

All queued designs and idle bases stay in a fully enumerated input roster;
no queue item is consumed. Complete owner PP and every component
warehouse carry unchanged. Each turn executes only the same supported
14-phase planetary economy, with independently reconciled event ledger.
"""
from __future__ import annotations

from dataclasses import dataclass

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_ship_component_quote import StandardShipBlueprint
from planets_lab.sim.standard_ship_warehouse_assembly import (
    StandardComponentWarehouse, _decode_rows,
)

STATUS = "CONDITIONAL_SOFT_CAPPED_PQ_NO_REGULAR_BUILD_CARRY_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class CappedPQCarry:
    soft_ship_limit: int
    owner_pp: tuple[tuple[int, int], ...]
    all_base_warehouses: tuple[tuple[int, StandardComponentWarehouse], ...]


@dataclass(frozen=True, slots=True)
class CappedPQBaseIntent:
    planet_id: int
    blueprint: StandardShipBlueprint | None
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class CappedPQNoBuildTurn:
    all_bases: tuple[CappedPQBaseIntent, ...]
    no_priority_or_special_orders_on_this_turn_asserted: bool = False


@dataclass(frozen=True, slots=True)
class CappedPQNoBuildReceipt:
    turn_after: int
    queued_base_ids: tuple[int, ...]
    planet_balances: tuple[PlanetEconomicBalance, ...]
    economic_events: tuple[HostEvent, ...]
    all_planet_ledgers_exact: bool = True
    built_ship_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CappedPQNoBuildOutcome:
    status: str
    state: GameState | None = None
    carry_after: CappedPQCarry | None = None
    turns: tuple[CappedPQNoBuildReceipt, ...] = ()
    reason: str | None = None
    nuhost_regular_queue_selection_verified: bool = False
    independently_verified_no_priority_orders: bool = False
    independent_host_economy_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_order_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedCappedPQ(ValueError):
    """No partial output from unknown capped PQ queue or event effects."""


def _admit(
    state: GameState, specs: NuStaticSpecs, carry: CappedPQCarry,
    plans: tuple[CappedPQNoBuildTurn, ...],
) -> None:
    if (
        type(carry) is not CappedPQCarry
        or type(carry.soft_ship_limit) is not int
        or not 10 <= carry.soft_ship_limit <= 999
        or type(carry.owner_pp) is not tuple
        or type(carry.all_base_warehouses) is not tuple
        or len(carry.all_base_warehouses) != len(state.starbases)
        or not 2 <= len(state.starbases) <= 64
        or type(plans) is not tuple
        or not 2 <= len(plans) <= 8
        or len(state.ships) != carry.soft_ship_limit
        or state.metadata or state.ion_storms
    ):
        raise UnsupportedCappedPQ("not a complete, full soft-cap late PQ economy")
    state.validate()
    if any(
        type(sid) is not int or not 1 <= sid <= 999
        or type(ship.id) is not int or ship.id != sid
        or ship.warp != 0 or ship.damage != 0
        or ship.mission is not None
        or ship.mission1_target_id is not None
        or ship.mission2_target_id is not None
        for sid, ship in state.ships.items()
    ):
        raise UnsupportedCappedPQ("other fleet activity or untyped ship")
    owners: dict[int, int] = {}
    for entry in carry.owner_pp:
        if (
            type(entry) is not tuple or len(entry) != 2
            or type(entry[0]) is not int or entry[0] not in state.players
            or entry[0] in owners or type(entry[1]) is not int
            or not 0 <= entry[1] <= 1000000
        ):
            raise UnsupportedCappedPQ("owner PP missing, duplicate or untyped")
        owners[entry[0]] = entry[1]
    if set(owners) != set(state.players):
        raise UnsupportedCappedPQ("not all PP owners represented")
    warehouses: dict[int, StandardComponentWarehouse] = {}
    for row in carry.all_base_warehouses:
        if (
            type(row) is not tuple or len(row) != 2
            or type(row[0]) is not int or row[0] not in state.starbases
            or row[0] in warehouses
            or type(row[1]) is not StandardComponentWarehouse
        ):
            raise UnsupportedCappedPQ("duplicate/missing starbase warehouse")
        for field, catalog in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(identifier not in catalog
                   for identifier in _decode_rows(getattr(row[1], field))):
                raise UnsupportedCappedPQ("invalid stock even on idle/queued base")
        warehouses[row[0]] = row[1]
    if set(warehouses) != set(state.starbases):
        raise UnsupportedCappedPQ("not all base stocks present")
    for pid, base in state.starbases.items():
        if (
            pid not in state.planets
            or base.owner_id != state.planets[pid].owner_id
            or base.owner_id not in owners
        ):
            raise UnsupportedCappedPQ("base and planet owner disagree")
    for plan in plans:
        if (
            type(plan) is not CappedPQNoBuildTurn
            or type(plan.all_bases) is not tuple
            or len(plan.all_bases) != len(state.starbases)
            or plan.no_priority_or_special_orders_on_this_turn_asserted is not True
        ):
            raise UnsupportedCappedPQ("missing full no-priority turn declaration")
        ids: set[int] = set()
        queued_count = 0
        for row in plan.all_bases:
            if (
                type(row) is not CappedPQBaseIntent
                or type(row.planet_id) is not int
                or row.planet_id not in state.starbases
                or row.planet_id in ids
                or type(row.allowed_hull_ids) is not frozenset
                or any(type(h) is not int or h not in specs.hulls
                       for h in row.allowed_hull_ids)
            ):
                raise UnsupportedCappedPQ("unknown base/rights in turn roster")
            ids.add(row.planet_id)
            if row.blueprint is None:
                if row.allowed_hull_ids:
                    raise UnsupportedCappedPQ("idle base with unexplained hull rights")
            else:
                queued_count += 1
                bp = row.blueprint
                if (
                    type(bp) is not StandardShipBlueprint
                    or bp.hull_id not in row.allowed_hull_ids
                    or bp.engine_id not in specs.engines
                    or (bp.beam_count and bp.beam_id not in specs.beams)
                    or (bp.torpedo_launcher_count
                        and bp.torpedo_id not in specs.torpedoes)
                ):
                    raise UnsupportedCappedPQ("unknown queued normal blueprint")
        if ids != set(state.starbases) or queued_count < 2:
            raise UnsupportedCappedPQ("missing bases or PQ competition declaration")


def simulate_soft_capped_pq_no_build_carry(
    before: GameState,
    specs: NuStaticSpecs,
    carry: CappedPQCarry,
    plans: tuple[CappedPQNoBuildTurn, ...],
    *,
    standard_rules_asserted: bool = False,
    complete_owner_planet_base_fleet_and_queue_roster_asserted: bool = False,
    no_priority_clone_mining_stations_or_external_actions_asserted: bool = False,
    default_no_pp_income_or_regular_pp_spend_asserted: bool = False,
    seed: int = 0,
) -> CappedPQNoBuildOutcome:
    def abstain(reason: str) -> CappedPQNoBuildOutcome:
        return CappedPQNoBuildOutcome(
            "ABSTAIN_CAPPED_PQ_NO_REGULAR_BUILD_CARRY", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(seed) is not int
        or standard_rules_asserted is not True
        or complete_owner_planet_base_fleet_and_queue_roster_asserted is not True
        or no_priority_clone_mining_stations_or_external_actions_asserted is not True
        or default_no_pp_income_or_regular_pp_spend_asserted is not True
    ):
        return abstain("incomplete capped PQ ordinary queue contract")
    try:
        _admit(before, specs, carry, plans)
        game = before
        engine = HostEngine(PlanetaryHostPipeline().phases)
        noop = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner)
            for owner in sorted(before.players)
        })
        output: list[CappedPQNoBuildReceipt] = []
        for index, plan in enumerate(plans):
            if (
                game.starbases != before.starbases
                or game.players != before.players
                or game.ships != before.ships
                or len(game.ships) != carry.soft_ship_limit
            ):
                raise UnsupportedCappedPQ("fleet or owner roster changed at full cap")
            modeled, events = engine.step(game, noop, seed=seed + index)
            if (
                modeled.turn != game.turn + 1
                or modeled.ships != game.ships
                or modeled.starbases != game.starbases
                or modeled.players != game.players
                or modeled.metadata != game.metadata
                or modeled.ion_storms != game.ion_storms
            ):
                raise UnsupportedCappedPQ("ship/base/owner effect during no-build phase")
            balances = _planet_ledgers(game, modeled, events)
            if not all(b.resource_balance_exact for b in balances):
                raise UnsupportedCappedPQ("unaccounted economy stock or event receipt")
            output.append(CappedPQNoBuildReceipt(
                turn_after=modeled.turn,
                queued_base_ids=tuple(sorted(
                    row.planet_id for row in plan.all_bases
                    if row.blueprint is not None
                )),
                planet_balances=balances,
                economic_events=events,
            ))
            game = modeled
        return CappedPQNoBuildOutcome(
            STATUS, state=game, carry_after=carry, turns=tuple(output),
        )
    except (
        ValueError, TypeError, KeyError, AttributeError, OverflowError,
        UnsupportedPopulationRule, UnsupportedEconomicLedger,
    ):
        return abstain("unsupported at-cap PQ queue, 14-phase economy or inventory")
