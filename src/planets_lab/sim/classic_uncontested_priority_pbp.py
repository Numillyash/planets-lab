"""One unequivocal Classic PBP priority build, MODEL-ONLY intermediate phase.

Only the narrow case where exactly one player has >=21 PBPs and exactly
one of that player's complete explicitly listed bases has an ordinary
priority-capable ship queued. No pbN codes, priority ties, competing bases,
clones, combat, middle/late interleavings or inferred Host order.

The model uses the documented ceil(hull mass / 50), maximum 20 PBP,
threshold >=21 for admission, and a known free lowest Classic ship ID.
All owner PBP balances, orders, warehouse inventories and Host phase
start are ASSERTED, never authenticated by local execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs, ResourceCost
from planets_lab.sim.standard_ship_component_quote import StandardShipBlueprint
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    CompleteBaseBuild, _execute_all_selected,
)

STATUS = "CONDITIONAL_UNCONTESTED_CLASSIC_PBP_PRIORITY_BUILD_NOT_NUHOST_VERIFIED"


class UnsupportedPbpPriority(ValueError):
    """Missing independent queue scope; no partially built ship is returned."""


@dataclass(frozen=True, slots=True)
class PriorityShipOrder:
    blueprint: StandardShipBlueprint
    warehouse: StandardComponentWarehouse
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class ClassicPriorityContext:
    ship_limit: int
    player_pbps: tuple[tuple[int, int], ...]
    queued_base_orders: Mapping[int, PriorityShipOrder | None]
    full_fleet_and_base_roster_asserted: bool = False
    complete_player_pbp_balances_asserted: bool = False
    no_pb_codes_clones_or_other_priority_orders_asserted: bool = False
    exact_single_precombat_priority_subphase_asserted: bool = False


@dataclass(frozen=True, slots=True)
class PbpPriorityOutcome:
    status: str
    phase_state: GameState | None = None
    selected_base_planet_id: int | None = None
    built_ship_id: int | None = None
    hull_mass: int | None = None
    pbp_cost: int | None = None
    player_pbps_after: tuple[tuple[int, int], ...] = ()
    warehouse_after: StandardComponentWarehouse | None = None
    purchased_materials: ResourceCost | None = None
    reason: str | None = None
    independently_witnessed_pbp_balance: bool = False
    independently_witnessed_queue_selection: bool = False
    independently_witnessed_ship_id: bool = False
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def documented_classic_priority_cost(hull_mass: int) -> int | None:
    """1 PBP per 50 KT or fraction; capped at 20 (normal Classic hull)."""
    if type(hull_mass) is not int or hull_mass <= 0:
        return None
    return min(20, (hull_mass + 49) // 50)


def simulate_uncontested_classic_pbp_priority(
    before: GameState,
    specs: NuStaticSpecs,
    context: ClassicPriorityContext,
    *,
    standard_rules_asserted: bool = False,
    complete_warehouse_and_hull_rights_asserted: bool = False,
) -> PbpPriorityOutcome:
    def abstain(reason: str) -> PbpPriorityOutcome:
        return PbpPriorityOutcome("ABSTAIN_CLASSIC_PRIORITY_BUILD", reason=reason)

    if (
        type(before) is not GameState
        or type(specs) is not NuStaticSpecs
        or type(context) is not ClassicPriorityContext
        or standard_rules_asserted is not True
        or complete_warehouse_and_hull_rights_asserted is not True
        or context.full_fleet_and_base_roster_asserted is not True
        or context.complete_player_pbp_balances_asserted is not True
        or context.no_pb_codes_clones_or_other_priority_orders_asserted is not True
        or context.exact_single_precombat_priority_subphase_asserted is not True
        or type(context.ship_limit) is not int
        or not 1 <= context.ship_limit <= 999
        or type(context.queued_base_orders) is not dict
        or type(context.player_pbps) is not tuple
    ):
        return abstain("exact standard Classic priority phase/roster/warehouse declarations required")
    try:
        before.validate()
        if before.metadata or before.ion_storms:
            raise UnsupportedPbpPriority("special game modes unsupported")
        if (set(context.queued_base_orders) != set(before.starbases)
                or len(context.queued_base_orders) < 2
                or len(before.ships) >= context.ship_limit
                or set(before.players) != {
                    row[0] for row in context.player_pbps
                    if type(row) is tuple and len(row) == 2
                }):
            raise UnsupportedPbpPriority("unknown real base/fleet/owner scope or hard limit")
        points: dict[int, int] = {}
        for row in context.player_pbps:
            if (type(row) is not tuple or len(row) != 2
                    or type(row[0]) is not int or row[0] not in before.players
                    or row[0] in points or type(row[1]) is not int
                    or not 0 <= row[1] <= 100000):
                raise UnsupportedPbpPriority("missing/duplicate player PBP balance")
            points[row[0]] = row[1]
        priority_eligible = [owner for owner, value in points.items() if value >= 21]
        if len(priority_eligible) != 1:
            raise UnsupportedPbpPriority("competition, ties or no eligible PBP owner")
        owner = priority_eligible[0]
        candidates: list[tuple[int, PriorityShipOrder]] = []
        for pid, item in context.queued_base_orders.items():
            planet = before.planets.get(pid)
            base = before.starbases.get(pid)
            if (type(pid) is not int or planet is None or base is None
                    or base.owner_id != planet.owner_id
                    or planet.owner_id not in before.players):
                raise UnsupportedPbpPriority("inconsistent planetary base ownership")
            if item is not None:
                if (type(item) is not PriorityShipOrder
                        or type(item.blueprint) is not StandardShipBlueprint
                        or type(item.warehouse) is not StandardComponentWarehouse
                        or type(item.allowed_hull_ids) is not frozenset):
                    raise UnsupportedPbpPriority("malformed priority-capable base order")
                if planet.owner_id == owner:
                    candidates.append((pid, item))
        if len(candidates) != 1:
            raise UnsupportedPbpPriority("multiple or missing eligible-owner priority ship candidates")
        if any(
            ship.warp != 0 or ship.damage != 0 or ship.mission is not None
            or ship.mission1_target_id is not None
            or ship.mission2_target_id is not None
            for ship in before.ships.values()
        ):
            raise UnsupportedPbpPriority("moving or combat-interacting fleet unsupported")
        pid, intent = candidates[0]
        hull = specs.hulls.get(intent.blueprint.hull_id)
        if hull is None:
            raise UnsupportedPbpPriority("unknown hull for PBP cost")
        mass = hull.mass
        pbp_cost = documented_classic_priority_cost(mass)
        if pbp_cost is None:
            raise UnsupportedPbpPriority("invalid hull mass")
        # Starting PBP >=21 always covers a normal capped <=20 PBP cost.
        if points[owner] < pbp_cost:
            raise UnsupportedPbpPriority("insufficient spendable PBP")
        selected_id = next(
            (sid for sid in range(1, context.ship_limit + 1)
             if sid not in before.ships),
            None,
        )
        if selected_id is None:
            raise UnsupportedPbpPriority("no available Classic ship number")
        from planets_lab.sim.standard_ship_warehouse_assembly import SelectedBuildSlot
        chosen = SelectedBuildSlot(
            starbase_planet_id=pid,
            proposed_ship_id=selected_id,
            global_ship_limit=context.ship_limit,
            complete_global_ship_roster_asserted=True,
            queue_selection_asserted=True,
        )
        phase, receipts = _execute_all_selected(
            before, specs,
            {pid: CompleteBaseBuild(
                blueprint=intent.blueprint, warehouse=intent.warehouse,
                slot=chosen, allowed_hull_ids=intent.allowed_hull_ids,
            )},
            context.ship_limit,
        )
        if (len(receipts) != 1
                or receipts[0].ship_id != selected_id
                or receipts[0].starbase_planet_id != pid
                or phase.turn != before.turn):
            raise UnsupportedPbpPriority("unexplained priority build receipt or Host turn advancement")
        after_pp = dict(points)
        after_pp[owner] -= pbp_cost
        return PbpPriorityOutcome(
            STATUS, phase_state=phase, selected_base_planet_id=pid,
            built_ship_id=selected_id, hull_mass=mass, pbp_cost=pbp_cost,
            player_pbps_after=tuple(sorted(after_pp.items())),
            warehouse_after=receipts[0].warehouse_after,
            purchased_materials=receipts[0].purchased,
        )
    except (UnsupportedPbpPriority, ValueError, TypeError,
            AttributeError, KeyError, OverflowError):
        return abstain("unknown PBP, base selection or material/ship inventory")
