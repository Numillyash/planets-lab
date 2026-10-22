"""Conditional Classic PBP arbitration for EXACTLY ONE remaining hard slot.

The caller explicitly asserts the conventional highest-unique-PBP ranking
hypothesis and an entirely code-free, clone-free, complete owner/base
queue. Official documentation reports possible ordering changes by
player slot / priority code; THIS MODEL DOES NOT VERIFY REAL NUHOST RANKS.
Competing PBP owners with tied scores or more than one queued base per
eligible player ABSTAIN. No multi-slot competition, combat or pbN orders.

Reuse independent #257 component/new-ship audits and planetary ledgers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.classic_uncontested_priority_pbp import (
    PriorityShipOrder, documented_classic_priority_cost,
)
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, _planet_ledgers,
)
from planets_lab.sim.standard_ship_component_quote import COST_FIELDS
from planets_lab.sim.standard_ship_economy_turn import AssembledShipBalance
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, _execute_all_selected,
)

STATUS = "CONDITIONAL_CLASSIC_COMPETING_LAST_SLOT_NOT_NUHOST_VERIFIED"
POLICY = "CALLER_ASSERTED_UNIQUE_HIGHEST_PBP_NO_CODES"
PLACEMENTS = (
    "terminal_priority_before_planetary",
    "terminal_priority_after_planetary",
)


@dataclass(frozen=True, slots=True)
class ClassicContestedBase:
    planet_id: int
    queued: PriorityShipOrder | None
    pb_code: int | None = None
    cloning: bool = False


@dataclass(frozen=True, slots=True)
class ClassicTerminalContext:
    ship_limit: int
    player_pbps: tuple[tuple[int, int], ...]
    bases: tuple[ClassicContestedBase, ...]
    last_standard_build_planet_id: int
    ranking_policy: str = POLICY
    full_fleet_base_owner_pbp_scope_asserted: bool = False
    no_codes_clones_or_extra_build_windows_asserted: bool = False
    unique_highest_pbp_hypothesis_asserted: bool = False


@dataclass(frozen=True, slots=True)
class ClassicTerminalOutcome:
    status: str
    state: GameState | None = None
    winning_base_id: int | None = None
    winning_ship_id: int | None = None
    pbp_cost: int | None = None
    pbps_after: tuple[tuple[int, int], ...] = ()
    last_standard_pointer_after: int | None = None
    selected_build_balance: AssembledShipBalance | None = None
    nonwinner_warehouses: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economic_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    priority_rank_independently_verified: bool = False
    pbp_balances_independently_verified: bool = False
    ship_id_independently_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedTerminalSlot(ValueError):
    """Ambiguous or unbalanced terminal slot."""


def _winner(
    state: GameState, context: ClassicTerminalContext,
) -> tuple[int, PriorityShipOrder, dict[int, int]]:
    if (
        type(context.ship_limit) is not int
        or not 2 <= context.ship_limit <= 999
        or len(state.ships) != context.ship_limit - 1
        or type(context.last_standard_build_planet_id) is not int
        or not 0 <= context.last_standard_build_planet_id <= 500
        or context.ranking_policy != POLICY
        or context.full_fleet_base_owner_pbp_scope_asserted is not True
        or context.no_codes_clones_or_extra_build_windows_asserted is not True
        or context.unique_highest_pbp_hypothesis_asserted is not True
        or type(context.player_pbps) is not tuple
        or type(context.bases) is not tuple
        or len(context.bases) != len(state.starbases)
    ):
        raise UnsupportedTerminalSlot("known terminal hard slot and asserted ranking required")
    if state.metadata or state.ion_storms:
        raise UnsupportedTerminalSlot("special game/storm interactions")
    points: dict[int, int] = {}
    for record in context.player_pbps:
        if (
            type(record) is not tuple or len(record) != 2
            or type(record[0]) is not int or record[0] not in state.players
            or record[0] in points or type(record[1]) is not int
            or not 0 <= record[1] <= 100000
        ):
            raise UnsupportedTerminalSlot("unknown or duplicated player PBP")
        points[record[0]] = record[1]
    if set(points) != set(state.players):
        raise UnsupportedTerminalSlot("missing PBP owner scope")
    eligible = [pid for pid, n in points.items() if n >= 21]
    if len(eligible) < 2:
        raise UnsupportedTerminalSlot("no competition among eligible owners")
    top = max(points[p] for p in eligible)
    leaders = [p for p in eligible if points[p] == top]
    if len(leaders) != 1:
        raise UnsupportedTerminalSlot("highest-PBP tie, no justified ordering")
    seen: set[int] = set()
    owner_candidates = {owner: [] for owner in eligible}
    other_warehouses: dict[int, StandardComponentWarehouse] = {}
    for base_order in context.bases:
        pid = base_order.planet_id
        if (
            type(base_order) is not ClassicContestedBase
            or type(pid) is not int or pid in seen or pid not in state.starbases
            or base_order.pb_code is not None or base_order.cloning is not False
        ):
            raise UnsupportedTerminalSlot("missing/extra base, pb code, or clone")
        seen.add(pid)
        base = state.starbases[pid]
        planet = state.planets.get(pid)
        if planet is None or base.owner_id != planet.owner_id:
            raise UnsupportedTerminalSlot("base and planet owner disagree")
        if base_order.queued is not None:
            order = base_order.queued
            if (
                type(order) is not PriorityShipOrder
                or type(order.warehouse) is not StandardComponentWarehouse
                or type(order.allowed_hull_ids) is not frozenset
            ):
                raise UnsupportedTerminalSlot("incomplete component/source inventory")
            other_warehouses[pid] = order.warehouse
            if base.owner_id in owner_candidates:
                owner_candidates[base.owner_id].append((pid, order))
    if seen != set(state.starbases) or any(
        len(owner_candidates[owner]) != 1 for owner in eligible
    ):
        raise UnsupportedTerminalSlot("one unambiguous queued base per eligible player required")
    selected_pid, selected_order = owner_candidates[leaders[0]][0]
    return selected_pid, selected_order, points


def simulate_classic_terminal_priority_slot(
    before: GameState,
    specs: NuStaticSpecs,
    context: ClassicTerminalContext,
    *,
    placement: Literal[
        "terminal_priority_before_planetary",
        "terminal_priority_after_planetary",
    ],
    standard_rules_asserted: bool = False,
    complete_warehouse_and_hull_rights_asserted: bool = False,
    no_other_ship_base_or_combat_actions_asserted: bool = False,
    seed: int = 0,
) -> ClassicTerminalOutcome:
    def abstain(reason: str) -> ClassicTerminalOutcome:
        return ClassicTerminalOutcome("ABSTAIN_CLASSIC_TERMINAL_SLOT", reason=reason)
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not ClassicTerminalContext
        or placement not in PLACEMENTS or type(seed) is not int
        or standard_rules_asserted is not True
        or complete_warehouse_and_hull_rights_asserted is not True
        or no_other_ship_base_or_combat_actions_asserted is not True
    ):
        return abstain("missing strict terminal priority context")
    try:
        before.validate()
        pid, order, points = _winner(before, context)
        if any(
            ship.warp != 0 or ship.damage != 0 or ship.mission is not None
            or ship.mission1_target_id is not None
            or ship.mission2_target_id is not None
            for ship in before.ships.values()
        ):
            raise UnsupportedTerminalSlot("non-queue ship activity")
        blueprint = order.blueprint
        hull = specs.hulls.get(blueprint.hull_id)
        cost = documented_classic_priority_cost(hull.mass) if hull else None
        owner = before.starbases[pid].owner_id
        if cost is None or points[owner] < cost:
            raise UnsupportedTerminalSlot("unsupported hull mass/points expense")
        ship_id = next(
            (sid for sid in range(1, context.ship_limit + 1)
             if sid not in before.ships),
            None,
        )
        if ship_id is None:
            raise UnsupportedTerminalSlot("no legal free ship number")
        noop = TurnOrders(by_player={
            p: PlayerOrders(player_id=p) for p in sorted(before.players)
        })
        economy = HostEngine(PlanetaryHostPipeline().phases)
        def build(source: GameState) -> tuple[GameState, AssembledShipBalance]:
            selected = SelectedBuildSlot(
                starbase_planet_id=pid, proposed_ship_id=ship_id,
                global_ship_limit=context.ship_limit,
                complete_global_ship_roster_asserted=True,
                queue_selection_asserted=True,
            )
            phase, receipts = _execute_all_selected(
                source, specs, {
                    pid: CompleteBaseBuild(
                        blueprint=blueprint, warehouse=order.warehouse,
                        slot=selected, allowed_hull_ids=order.allowed_hull_ids,
                    ),
                }, context.ship_limit,
            )
            if len(receipts) != 1 or receipts[0].ship_id != ship_id:
                raise UnsupportedTerminalSlot("invalid terminal ship material receipt")
            return phase, receipts[0]
        if placement == PLACEMENTS[0]:
            built, balance = build(before)
            after, events = economy.step(built, noop, seed=seed)
        else:
            intermediate, events = economy.step(before, noop, seed=seed)
            after, balance = build(intermediate)
        expected = Ship(
            id=ship_id, owner_id=owner, hull_id=blueprint.hull_id,
            x=before.planets[pid].x, y=before.planets[pid].y,
            engine_id=blueprint.engine_id,
            beam_id=blueprint.beam_id if blueprint.beam_count else None,
            torpedo_id=(blueprint.torpedo_id
                        if blueprint.torpedo_launcher_count else None),
            beam_count=blueprint.beam_count,
            torpedo_launcher_count=blueprint.torpedo_launcher_count,
            fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
        )
        if (
            after.ships.get(ship_id) != expected
            or set(after.ships) != set(before.ships) | {ship_id}
            or any(after.ships[sid] != old for sid, old in before.ships.items())
            or after.starbases != before.starbases
        ):
            raise UnsupportedTerminalSlot("final ship/base roster changed outside selected build")
        projected = after.clone()
        projected.ships.pop(ship_id)
        for name in COST_FIELDS:
            amount = getattr(projected.planets[pid].cargo, name)
            if type(amount) is not int or amount < 0:
                raise UnsupportedTerminalSlot("invalid final resource stock")
            setattr(projected.planets[pid].cargo, name,
                    amount + getattr(balance.purchased, name))
        budgets = _planet_ledgers(before, projected, events)
        if not all(row.resource_balance_exact for row in budgets):
            raise UnsupportedTerminalSlot("unexplained planet economic balance")
        points[owner] -= cost
        return ClassicTerminalOutcome(
            STATUS, state=after, winning_base_id=pid,
            winning_ship_id=ship_id, pbp_cost=cost,
            pbps_after=tuple(sorted(points.items())),
            last_standard_pointer_after=context.last_standard_build_planet_id,
            selected_build_balance=balance,
            nonwinner_warehouses=tuple(
                sorted((r.planet_id, r.queued.warehouse)
                       for r in context.bases
                       if r.queued is not None and r.planet_id != pid)
            ),
            planet_balances=budgets, economic_events=events,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("unattributable competing terminal slot/ledger")
