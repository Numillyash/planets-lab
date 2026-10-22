"""Consecutive conditional late-PQ turns with explicit externally supplied loss.

The single-slot #271 economic turn ends at the PQ soft cap. A next
single-slot turn is NOT reachable unless some EXTERNAL process frees a
ship slot. Never invent a Host battle, recycling, random base choice or
resource event: between consecutive modeled turns an operator must
provide both the ID of exactly one inert, cargo-empty ship removed and
a complete preturn GameState matching the prior modeled output MINUS
that one ship and NOTHING ELSE.

This is a counterfactual boundary ledger, NOT a NuHost loss simulator or
an independently observed boundary. One later unsupported step ABSTAINS
the entire sequence, returning no partial state, receipts, PP or stock.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from planets_lab.core import Cargo, GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.late_pq_external_regular_economy import (
    LatePQBase, LatePQContext, LatePQOutcome,
    simulate_late_pq_external_selected_economic_turn,
)
from planets_lab.sim.standard_ship_component_quote import StandardShipBlueprint
from planets_lab.sim.standard_ship_warehouse_assembly import (
    StandardComponentWarehouse, _decode_rows,
)

STATUS = "CONDITIONAL_MULTITURN_PQ_EXTERNAL_LOSS_CARRY_NOT_NUHOST_VERIFIED"
PLACEMENTS = ("late_pq_build_before_economy", "late_pq_build_after_economy")


@dataclass(frozen=True, slots=True)
class LatePQCarry:
    soft_ship_limit: int
    player_pp: tuple[tuple[int, int], ...]
    base_warehouses: tuple[tuple[int, StandardComponentWarehouse], ...]


@dataclass(frozen=True, slots=True)
class LatePQTurnBase:
    planet_id: int
    blueprint: StandardShipBlueprint | None
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class LatePQExplicitTurn:
    bases: tuple[LatePQTurnBase, ...]
    selected_planet_id: int
    selected_ship_id: int
    placement: Literal[
        "late_pq_build_before_economy", "late_pq_build_after_economy",
    ]
    external_removed_ship_id: int | None = None
    externally_supplied_preturn_state: GameState | None = None
    external_single_inert_ship_loss_asserted: bool = False


@dataclass(frozen=True, slots=True)
class LatePQCarryReceipt:
    turn_after: int
    externally_removed_ship_id: int | None
    selected_base_id: int
    built_ship_id: int
    player_pp_after: tuple[tuple[int, int], ...]
    base_warehouses_after: tuple[tuple[int, StandardComponentWarehouse], ...]
    planet_balance_exact: bool
    conditional_external_loss_only: bool = True


@dataclass(frozen=True, slots=True)
class LatePQCarryOutcome:
    status: str
    state: GameState | None = None
    carry_after: LatePQCarry | None = None
    turns: tuple[LatePQCarryReceipt, ...] = ()
    reason: str | None = None
    externally_removed_ship_independently_verified: bool = False
    random_pq_selection_independently_verified: bool = False
    accepted_orders_verified: bool = False
    nuhost_execution_verified: bool = False
    nuhost_phase_order_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedLatePQCarry(ValueError):
    """Atomic abstention for unsupported conditional carry or loss boundary."""


def _checked_warehouse_map(
    before: GameState, specs: NuStaticSpecs, carry: LatePQCarry,
) -> dict[int, StandardComponentWarehouse]:
    if (
        type(carry) is not LatePQCarry
        or type(carry.soft_ship_limit) is not int
        or not 10 <= carry.soft_ship_limit <= 999
        or type(carry.base_warehouses) is not tuple
        or len(carry.base_warehouses) != len(before.starbases)
        or type(carry.player_pp) is not tuple
    ):
        raise UnsupportedLatePQCarry("incomplete typed global PQ sidecar")

    points: dict[int, int] = {}
    for row in carry.player_pp:
        if (
            type(row) is not tuple or len(row) != 2
            or type(row[0]) is not int or row[0] not in before.players
            or row[0] in points or type(row[1]) is not int
            or not 0 <= row[1] <= 1000000
        ):
            raise UnsupportedLatePQCarry("untrusted or duplicate owner PP")
        points[row[0]] = row[1]
    if set(points) != set(before.players):
        raise UnsupportedLatePQCarry("incomplete PP owner roster")

    warehouses: dict[int, StandardComponentWarehouse] = {}
    for item in carry.base_warehouses:
        if (
            type(item) is not tuple or len(item) != 2
            or type(item[0]) is not int
            or item[0] not in before.starbases
            or item[0] in warehouses
            or type(item[1]) is not StandardComponentWarehouse
        ):
            raise UnsupportedLatePQCarry("duplicate or missing base warehouse")
        warehouse = item[1]
        for kind, catalog in (
            ("hulls", specs.hulls), ("engines", specs.engines),
            ("beams", specs.beams), ("launchers", specs.torpedoes),
        ):
            if any(cid not in catalog for cid in _decode_rows(
                getattr(warehouse, kind)
            )):
                raise UnsupportedLatePQCarry("unknown component in an idle warehouse")
        warehouses[item[0]] = warehouse
    if set(warehouses) != set(before.starbases):
        raise UnsupportedLatePQCarry("incomplete base inventory roster")
    return warehouses


def _check_preturn_external_loss(
    prior: GameState,
    plan: LatePQExplicitTurn,
    soft_limit: int,
) -> GameState:
    if (
        type(plan.external_removed_ship_id) is not int
        or type(plan.externally_supplied_preturn_state) is not GameState
        or plan.external_single_inert_ship_loss_asserted is not True
        or len(prior.ships) != soft_limit
    ):
        raise UnsupportedLatePQCarry("next PQ slot requires externally recorded single loss")
    sid = plan.external_removed_ship_id
    removed = prior.ships.get(sid)
    if (
        type(removed) is not Ship
        or removed.cargo != Cargo()
        or removed.fighters != 0 or removed.torpedoes != 0
        or removed.unresolved_ammo != 0 or removed.warp != 0
        or removed.damage != 0 or removed.mission is not None
        or removed.mission1_target_id is not None
        or removed.mission2_target_id is not None
    ):
        raise UnsupportedLatePQCarry("external loss not an inert empty known ship")
    expected = prior.clone()
    expected.ships.pop(sid)
    observed = plan.externally_supplied_preturn_state
    if observed != expected or len(observed.ships) != soft_limit - 1:
        raise UnsupportedLatePQCarry("full external preturn differs beyond single ship loss")
    observed.validate()
    # Never mutate caller-provided snapshot or infer its source.
    return observed


def simulate_bounded_late_pq_external_loss_carry(
    before: GameState,
    specs: NuStaticSpecs,
    initial: LatePQCarry,
    plans: tuple[LatePQExplicitTurn, ...],
    *,
    standard_rules_asserted: bool = False,
    complete_all_turn_queues_and_warehouses_asserted: bool = False,
    exact_external_loss_snapshots_asserted: bool = False,
    no_other_interturn_planet_pp_fleet_mutations_asserted: bool = False,
    seed: int = 0,
) -> LatePQCarryOutcome:
    def abstain(reason: str) -> LatePQCarryOutcome:
        return LatePQCarryOutcome("ABSTAIN_MULTITURN_PQ_EXTERNAL_LOSS", reason=reason)

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(initial) is not LatePQCarry
        or type(plans) is not tuple or not 2 <= len(plans) <= 6
        or type(seed) is not int
        or standard_rules_asserted is not True
        or complete_all_turn_queues_and_warehouses_asserted is not True
        or exact_external_loss_snapshots_asserted is not True
        or no_other_interturn_planet_pp_fleet_mutations_asserted is not True
    ):
        return abstain("missing complete multi-turn external-boundary contract")
    try:
        before.validate()
        carry = initial
        warehouses = _checked_warehouse_map(before, specs, carry)
        if len(before.ships) != carry.soft_ship_limit - 1:
            raise UnsupportedLatePQCarry("initial game is not one slot below soft cap")
        original_players = before.players
        original_starbases = before.starbases
        game = before
        receipts: list[LatePQCarryReceipt] = []

        for index, plan in enumerate(plans):
            if (
                type(plan) is not LatePQExplicitTurn
                or plan.placement not in PLACEMENTS
                or type(plan.selected_planet_id) is not int
                or type(plan.selected_ship_id) is not int
                or type(plan.bases) is not tuple
                or len(plan.bases) != len(original_starbases)
                or game.players != original_players
                or game.starbases != original_starbases
            ):
                raise UnsupportedLatePQCarry("missing complete turn or broken owners")
            if index == 0:
                if (
                    plan.external_removed_ship_id is not None
                    or plan.externally_supplied_preturn_state is not None
                    or plan.external_single_inert_ship_loss_asserted is not False
                ):
                    raise UnsupportedLatePQCarry("initial turn cannot invent an external loss")
                source = game
            else:
                source = _check_preturn_external_loss(
                    game, plan, carry.soft_ship_limit,
                )
            # A prior step's stock and points are the SOLE inputs to the
            # next modeled build. No replenishment or external PP awards.
            if _checked_warehouse_map(source, specs, carry) != warehouses:
                raise UnsupportedLatePQCarry("carried stock sidecar mismatch")
            seen: set[int] = set()
            base_rows: list[LatePQBase] = []
            for item in plan.bases:
                if (
                    type(item) is not LatePQTurnBase
                    or type(item.planet_id) is not int
                    or item.planet_id not in original_starbases
                    or item.planet_id in seen
                    or type(item.allowed_hull_ids) is not frozenset
                    or any(type(h) is not int for h in item.allowed_hull_ids)
                ):
                    raise UnsupportedLatePQCarry("missing/duplicate base plan or rights")
                seen.add(item.planet_id)
                if item.blueprint is None:
                    if item.allowed_hull_ids:
                        raise UnsupportedLatePQCarry("idle base has queued hull rights")
                elif type(item.blueprint) is not StandardShipBlueprint:
                    raise UnsupportedLatePQCarry("invalid queued ship blueprint")
                base_rows.append(LatePQBase(
                    planet_id=item.planet_id,
                    warehouse=warehouses[item.planet_id],
                    blueprint=item.blueprint,
                    allowed_hull_ids=(item.allowed_hull_ids
                                      if item.blueprint is not None else None),
                ))
            if seen != set(original_starbases):
                raise UnsupportedLatePQCarry("incomplete turn base roster")

            context = LatePQContext(
                soft_ship_limit=carry.soft_ship_limit,
                selected_planet_id=plan.selected_planet_id,
                selected_ship_id=plan.selected_ship_id,
                all_bases=tuple(base_rows),
                player_pp=carry.player_pp,
                complete_fleet_planets_all_buildable_bases_and_warehouses_asserted=True,
                caller_explicit_random_selected_base_asserted=True,
                no_priority_cloning_mining_stations_or_other_actions_asserted=True,
                default_regular_zero_pp_no_idle_pp_income_asserted=True,
            )
            result: LatePQOutcome = simulate_late_pq_external_selected_economic_turn(
                source, specs, context, placement=plan.placement,
                standard_rules_asserted=True,
                full_independent_economic_inventory_asserted=True,
                seed=seed + index,
            )
            if (
                not result.supported or result.state is None
                or result.ship_receipt is None
                or result.selected_base_id != plan.selected_planet_id
                or result.ship_receipt.ship_id != plan.selected_ship_id
                or result.player_pp_after != carry.player_pp
                or result.state.turn != source.turn + 1
                or not all(x.resource_balance_exact for x in result.planet_balances)
                or set(result.state.ships) != set(source.ships) | {
                    plan.selected_ship_id
                }
            ):
                raise UnsupportedLatePQCarry("unreconciled selected PQ turn")
            after_stock = dict(result.warehouses_after)
            if (
                len(result.warehouses_after) != len(original_starbases)
                or set(after_stock) != set(original_starbases)
                or any(
                    after_stock[pid] != stock
                    for pid, stock in warehouses.items()
                    if pid != plan.selected_planet_id
                )
            ):
                raise UnsupportedLatePQCarry("unselected warehouse moved")
            carry = LatePQCarry(
                soft_ship_limit=carry.soft_ship_limit,
                player_pp=result.player_pp_after,
                base_warehouses=tuple(sorted(after_stock.items())),
            )
            warehouses = after_stock
            game = result.state
            receipts.append(LatePQCarryReceipt(
                turn_after=game.turn,
                externally_removed_ship_id=plan.external_removed_ship_id,
                selected_base_id=plan.selected_planet_id,
                built_ship_id=plan.selected_ship_id,
                player_pp_after=carry.player_pp,
                base_warehouses_after=carry.base_warehouses,
                planet_balance_exact=True,
            ))
        return LatePQCarryOutcome(
            STATUS, state=game, carry_after=carry, turns=tuple(receipts),
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("unsupported full-queue, economic or externally supplied loss boundary")
