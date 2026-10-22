"""One conditional late PQ/PPQ pb1 priority ship with a full economic turn.

PQ/PPQ priority may pass their SOFT ship limit, but cannot use ship
numbers above 999. Only one unambiguous pp-funded request (PR #266)
is admitted. The existing component assembler requires an asserted
prelimit global slot: we pass the distinct PROGRAMMATIC 999 ceiling,
never misrepresent the 500/custom soft cap as a hard building cap.
This adapter does not infer actual NuHost selection, timing, PP earned
by idle starbases, ordinary PQ random slots or PPQ planet-share RB#.
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
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, _execute_all_selected,
)
from planets_lab.sim.late_pq_ppq_priority_admission import (
    LatePriorityContext, quote_single_late_priority,
)

STATUS = "CONDITIONAL_LATE_PQ_PPQ_PRIORITY_SHIP_ECONOMY_NOT_NUHOST_VERIFIED"
PLACEMENTS = (
    "priority_ship_before_planet_economy",
    "priority_ship_after_planet_economy",
)


@dataclass(frozen=True, slots=True)
class LatePriorityShipEconomicTurn:
    status: str
    state: GameState | None = None
    priority_mode: str | None = None
    winning_base_id: int | None = None
    new_ship_id: int | None = None
    pp_cost: int | None = None
    player_pp_after: tuple[tuple[int, int], ...] = ()
    component_receipt: AssembledShipBalance | None = None
    unused_base_warehouses: tuple[tuple[int, StandardComponentWarehouse], ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    economy_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    priority_order_independently_verified: bool = False
    server_accepted_order_verified: bool = False
    programmatic_ship_id_independently_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedLatePriorityShip(ValueError):
    """No partial ship, PP or stock sidecar is emitted."""


def simulate_late_pq_ppq_priority_economic_turn(
    before: GameState,
    specs: NuStaticSpecs,
    context: LatePriorityContext,
    *,
    placement: Literal[
        "priority_ship_before_planet_economy",
        "priority_ship_after_planet_economy",
    ],
    standard_rules_asserted: bool = False,
    complete_component_warehouse_and_hull_rights_asserted: bool = False,
    no_other_ship_base_pp_or_combat_effects_asserted: bool = False,
    seed: int = 0,
) -> LatePriorityShipEconomicTurn:
    def abstain(reason: str) -> LatePriorityShipEconomicTurn:
        return LatePriorityShipEconomicTurn(
            "ABSTAIN_LATE_PQ_PPQ_PRIORITY_ECONOMIC_TURN", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not LatePriorityContext
        or type(seed) is not int or placement not in PLACEMENTS
        or standard_rules_asserted is not True
        or complete_component_warehouse_and_hull_rights_asserted is not True
        or no_other_ship_base_pp_or_combat_effects_asserted is not True
    ):
        return abstain("missing exact late priority/warehouse/economic scope")
    try:
        if any(
            ship.warp != 0 or ship.damage != 0 or ship.mission is not None
            or ship.mission1_target_id is not None
            or ship.mission2_target_id is not None
            for ship in before.ships.values()
        ):
            raise UnsupportedLatePriorityShip("ship movement/combat outside supported scope")
        quote = quote_single_late_priority(before, specs, context)
        if (
            not quote.supported or quote.base_planet_id is None
            or quote.proposed_ship_id is None or quote.priority_point_cost is None
            or quote.owner_id is None
        ):
            raise UnsupportedLatePriorityShip("late priority admission is ambiguous")
        pid, sid = quote.base_planet_id, quote.proposed_ship_id
        priority_entry = next(
            (entry for entry in context.all_bases if entry.planet_id == pid),
            None,
        )
        if priority_entry is None or priority_entry.order is None:
            raise UnsupportedLatePriorityShip("selected base order disappeared")
        order = priority_entry.order
        noops = TurnOrders(by_player={
            owner: PlayerOrders(player_id=owner) for owner in sorted(before.players)
        })
        economy = HostEngine(PlanetaryHostPipeline().phases)

        def build(source: GameState) -> tuple[GameState, AssembledShipBalance]:
            # 999 is the PROGRAMMATIC ID ceiling, not the PQ/PPQ soft cap.
            # A strictly caller-asserted selected priority slot is adapted
            # to the older prelimit-only component assembler; do not
            # interpret its internal "prelimit" name as Host evidence.
            selected = SelectedBuildSlot(
                starbase_planet_id=pid, proposed_ship_id=sid,
                global_ship_limit=999,
                complete_global_ship_roster_asserted=True,
                queue_selection_asserted=True,
            )
            after, receipts = _execute_all_selected(
                source, specs, {
                    pid: CompleteBaseBuild(
                        blueprint=order.blueprint, warehouse=order.warehouse,
                        slot=selected, allowed_hull_ids=order.allowed_hull_ids,
                    ),
                }, 999,
            )
            if len(receipts) != 1 or receipts[0].ship_id != sid:
                raise UnsupportedLatePriorityShip("missing/extra priority ship receipt")
            return after, receipts[0]

        if placement == PLACEMENTS[0]:
            built, receipt = build(before)
            modeled, events = economy.step(built, noops, seed=seed)
        else:
            intermediate, events = economy.step(before, noops, seed=seed)
            modeled, receipt = build(intermediate)

        # Strict final blueprint identity independent of intermediate
        # component receipt; 14 economy phases must not alter this ship.
        blueprint = order.blueprint
        hull = specs.hulls[blueprint.hull_id]
        planet = before.planets[pid]
        expected = Ship(
            id=sid, owner_id=quote.owner_id,
            hull_id=blueprint.hull_id,
            x=planet.x, y=planet.y, engine_id=blueprint.engine_id,
            beam_id=blueprint.beam_id if blueprint.beam_count else None,
            torpedo_id=(blueprint.torpedo_id
                        if blueprint.torpedo_launcher_count else None),
            beam_count=blueprint.beam_count,
            torpedo_launcher_count=blueprint.torpedo_launcher_count,
            fighter_bay_count=hull.fighter_bay_count, crew=hull.crew,
        )
        if (
            modeled.ships.get(sid) != expected
            or set(modeled.ships) != set(before.ships) | {sid}
            or len(modeled.ships) != len(before.ships) + 1
            or any(modeled.ships[old_id] != old
                   for old_id, old in before.ships.items())
            or modeled.starbases != before.starbases
        ):
            raise UnsupportedLatePriorityShip("unexpected fleet/base effects")

        # Undo ONLY purchased components from cloned final surface state;
        # then compare with economic phase events against original preturn.
        economic_only = modeled.clone()
        economic_only.ships.pop(sid)
        for name in COST_FIELDS:
            amount = getattr(economic_only.planets[pid].cargo, name)
            if type(amount) is not int or amount < 0:
                raise UnsupportedLatePriorityShip("untyped final surface resources")
            setattr(
                economic_only.planets[pid].cargo, name,
                amount + getattr(receipt.purchased, name),
            )
        ledgers = _planet_ledgers(before, economic_only, events)
        if not all(row.resource_balance_exact for row in ledgers):
            raise UnsupportedLatePriorityShip("planet economy balance mismatch")
        # Point consumption was independently quoted from BEFORE, not
        # from a HostEngine mutation or unverified server receipt.
        base_points = dict(context.player_pp)
        if (
            base_points[quote.owner_id] - quote.priority_point_cost
            != dict(quote.pp_after)[quote.owner_id]
            or any(
                dict(quote.pp_after)[owner] != points
                for owner, points in base_points.items()
                if owner != quote.owner_id
            )
        ):
            raise UnsupportedLatePriorityShip("priority point debit inconsistent")
        return LatePriorityShipEconomicTurn(
            STATUS, state=modeled, priority_mode=context.mode,
            winning_base_id=pid, new_ship_id=sid,
            pp_cost=quote.priority_point_cost,
            player_pp_after=quote.pp_after,
            component_receipt=receipt,
            unused_base_warehouses=tuple(
                sorted(
                    (entry.planet_id, entry.order.warehouse)
                    for entry in context.all_bases
                    if entry.order is not None and entry.planet_id != pid
                )
            ),
            planet_balances=ledgers, economy_events=events,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("unsupported or unreconciled PP, warehouse, ship or economic inventory")
