"""Bounded, fully explicit Classic PBP queue sidecar across consecutive turns.

Reuses separately audited #260 ordinary and #263 priority+ordinary full-turn
compositions. Carries ONLY the modeled hard ship cap, saved STANDARD pointer,
per-player PBP totals and complete per-base component warehouses. No phantom
priority-point earnings, ship ID allocations, mineral purchases or newly
appearing warehouses are allowed between transitions. Queue/warehouse plans
for each next turn are operator-specified, not independently accepted orders.

A later failure ABSTAINS the *entire* sequence, returning neither a partial
GameState nor partial intermediate receipts. This does NOT simulate real
NuHost pre/post-combat windows, contested pbN, cloning or postlimit PQ/PPQ.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.classic_uncontested_priority_pbp import (
    ClassicPriorityContext, PriorityShipOrder,
)
from planets_lab.sim.classic_standard_queue_pointer import (
    ClassicBaseQueueEntry, ClassicStandardSubphase,
)
from planets_lab.sim.classic_standard_pointer_economy_turn import (
    ClassicOrdinaryBuild,
    simulate_classic_standard_pointer_economy_turn,
)
from planets_lab.sim.classic_joint_priority_standard_turn import (
    ClassicJointContext, simulate_classic_joint_priority_standard_turn,
)
from planets_lab.sim.standard_ship_component_quote import StandardShipBlueprint
from planets_lab.sim.standard_ship_warehouse_assembly import (
    StandardComponentWarehouse, _decode_rows,
)

STATUS = "CONDITIONAL_CLASSIC_EXPLICIT_MULTITURN_CARRY_NOT_NUHOST_VERIFIED"
PLACEMENTS = ("builds_before_planetary", "builds_after_planetary")


@dataclass(frozen=True, slots=True)
class ClassicQueueCarryState:
    ship_limit: int
    last_standard_build_planet_id: int
    player_pbps: tuple[tuple[int, int], ...]
    all_base_warehouses: tuple[tuple[int, StandardComponentWarehouse], ...]


@dataclass(frozen=True, slots=True)
class ClassicBaseTurnIntent:
    planet_id: int
    blueprint: StandardShipBlueprint | None
    allowed_hull_ids: frozenset[int]


@dataclass(frozen=True, slots=True)
class ClassicExplicitTurn:
    bases: tuple[ClassicBaseTurnIntent, ...]
    placement: Literal["builds_before_planetary", "builds_after_planetary"]


@dataclass(frozen=True, slots=True)
class ClassicCarryTurnReceipt:
    turn_after: int
    queue_subphase: str
    priority_ship_id: int | None
    standard_ship_ids: tuple[int, ...]
    allocated_ship_ids: tuple[int, ...]
    pbps_after: tuple[tuple[int, int], ...]
    last_standard_pointer_after: int
    base_warehouses_after: tuple[tuple[int, StandardComponentWarehouse], ...]
    planet_balance_exact: bool


@dataclass(frozen=True, slots=True)
class ClassicCarryOutcome:
    status: str
    state: GameState | None = None
    carry_after: ClassicQueueCarryState | None = None
    turns: tuple[ClassicCarryTurnReceipt, ...] = ()
    reason: str | None = None
    player_pbps_independently_witnessed: bool = False
    standard_pointer_independently_witnessed: bool = False
    warehouses_independently_witnessed: bool = False
    host_queue_order_verified: bool = False
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedClassicCarry(ValueError):
    """Strict admission or inter-turn invariance failure."""


def _validate_initial(
    before: GameState,
    specs: NuStaticSpecs,
    carry: ClassicQueueCarryState,
    plans: tuple[ClassicExplicitTurn, ...],
) -> None:
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(carry) is not ClassicQueueCarryState
        or type(plans) is not tuple or not 1 <= len(plans) <= 8
        or type(carry.ship_limit) is not int
        or not 1 <= carry.ship_limit <= 999
        or len(before.ships) > carry.ship_limit
        or type(carry.last_standard_build_planet_id) is not int
        or not 0 <= carry.last_standard_build_planet_id <= 500
        or type(carry.player_pbps) is not tuple
        or type(carry.all_base_warehouses) is not tuple
    ):
        raise UnsupportedClassicCarry("missing complete finite Classic carry state")
    before.validate()
    players: dict[int, int] = {}
    for item in carry.player_pbps:
        if (
            type(item) is not tuple or len(item) != 2
            or type(item[0]) is not int or item[0] not in before.players
            or item[0] in players or type(item[1]) is not int
            or not 0 <= item[1] <= 100000
        ):
            raise UnsupportedClassicCarry("invalid or duplicate owner/PBP balance")
        players[item[0]] = item[1]
    if set(players) != set(before.players):
        raise UnsupportedClassicCarry("complete PBP owner roster required")
    warehouses: dict[int, StandardComponentWarehouse] = {}
    for entry in carry.all_base_warehouses:
        if (
            type(entry) is not tuple or len(entry) != 2
            or type(entry[0]) is not int or entry[0] not in before.starbases
            or entry[0] in warehouses
            or type(entry[1]) is not StandardComponentWarehouse
        ):
            raise UnsupportedClassicCarry("invalid or missing base warehouse")
        warehouse = entry[1]
        for kind, catalog in (
            ("hulls", specs.hulls),
            ("engines", specs.engines),
            ("beams", specs.beams),
            ("launchers", specs.torpedoes),
        ):
            if any(key not in catalog for key in _decode_rows(getattr(warehouse, kind))):
                raise UnsupportedClassicCarry("unknown component in an idle/active warehouse")
        warehouses[entry[0]] = warehouse
    if set(warehouses) != set(before.starbases):
        raise UnsupportedClassicCarry("complete all-base storage roster required")
    if before.metadata or before.ion_storms:
        raise UnsupportedClassicCarry("special game/storm context unsupported")
    for item in plans:
        if type(item) is not ClassicExplicitTurn or item.placement not in PLACEMENTS:
            raise UnsupportedClassicCarry("missing exact per-turn placement")
        if type(item.bases) is not tuple or len(item.bases) != len(before.starbases):
            raise UnsupportedClassicCarry("missing per-turn base order")
        ids: set[int] = set()
        for row in item.bases:
            if (
                type(row) is not ClassicBaseTurnIntent
                or type(row.planet_id) is not int
                or row.planet_id not in before.starbases
                or row.planet_id in ids
                or type(row.allowed_hull_ids) is not frozenset
            ):
                raise UnsupportedClassicCarry("unknown, duplicate or invalid base order")
            ids.add(row.planet_id)
            if row.blueprint is None:
                if row.allowed_hull_ids:
                    raise UnsupportedClassicCarry("idle base cannot assert build rights")
            elif (
                type(row.blueprint) is not StandardShipBlueprint
                or not row.allowed_hull_ids
                or any(type(h) is not int for h in row.allowed_hull_ids)
            ):
                raise UnsupportedClassicCarry("incomplete ordinary ship design or race rights")
        if ids != set(before.starbases) or not any(row.blueprint for row in item.bases):
            raise UnsupportedClassicCarry("exact complete roster and a queued ship required")


def simulate_bounded_classic_carry(
    before: GameState,
    specs: NuStaticSpecs,
    initial_carry: ClassicQueueCarryState,
    plans: tuple[ClassicExplicitTurn, ...],
    *,
    standard_rules_asserted: bool = False,
    complete_all_turn_orders_and_warehouses_asserted: bool = False,
    no_external_pbp_awards_or_interturn_mutations_asserted: bool = False,
    no_combat_movement_clone_or_nonstandard_orders_asserted: bool = False,
    seed: int = 0,
) -> ClassicCarryOutcome:
    def abstain(reason: str) -> ClassicCarryOutcome:
        return ClassicCarryOutcome("ABSTAIN_CLASSIC_MULTITURN_CARRY", reason=reason)

    if not (
        standard_rules_asserted is True
        and complete_all_turn_orders_and_warehouses_asserted is True
        and no_external_pbp_awards_or_interturn_mutations_asserted is True
        and no_combat_movement_clone_or_nonstandard_orders_asserted is True
        and type(seed) is int
    ):
        return abstain("complete bounded sequence and no external effects must be asserted")

    try:
        _validate_initial(before, specs, initial_carry, plans)
        game = before
        carry = initial_carry
        output: list[ClassicCarryTurnReceipt] = []
        original_base_owners = {pid: base.owner_id for pid, base in before.starbases.items()}
        original_players = set(before.players)
        for index, plan in enumerate(plans):
            # Recheck the actual carried game/roster after each modeled turn;
            # this loop performs ZERO external IO between these states.
            if (
                set(game.players) != original_players
                or {pid: b.owner_id for pid, b in game.starbases.items()}
                   != original_base_owners
                or len(game.ships) > carry.ship_limit
            ):
                raise UnsupportedClassicCarry("game/player/base continuity broke")
            warehouse = dict(carry.all_base_warehouses)
            queued = {
                item.planet_id: ClassicOrdinaryBuild(
                    blueprint=item.blueprint,
                    warehouse=warehouse[item.planet_id],
                    allowed_hull_ids=item.allowed_hull_ids,
                )
                for item in plan.bases if item.blueprint is not None
            }
            rows = tuple(ClassicBaseQueueEntry(
                planet_id=item.planet_id,
                owner_id=game.starbases[item.planet_id].owner_id,
                ordinary_ship_queued=item.blueprint is not None,
            ) for item in plan.bases)
            standard = ClassicStandardSubphase(
                ship_limit=carry.ship_limit,
                current_ship_count=len(game.ships),
                last_standard_build_planet_id=carry.last_standard_build_planet_id,
                bases=rows,
                player_pbps=carry.player_pbps,
                standard_phase_after_priorities_asserted=True,
                complete_starbase_roster_asserted=True,
                complete_player_pbp_balances_asserted=True,
                no_cloning_or_other_build_effects_asserted=True,
            )
            eligible = sum(points >= 21 for _, points in carry.player_pbps)
            if eligible > 1:
                raise UnsupportedClassicCarry("competing PBP owners are not modeled")
            if eligible == 1:
                priority = ClassicPriorityContext(
                    ship_limit=carry.ship_limit,
                    player_pbps=carry.player_pbps,
                    queued_base_orders={
                        pid: (PriorityShipOrder(
                            blueprint=order.blueprint,
                            warehouse=order.warehouse,
                            allowed_hull_ids=order.allowed_hull_ids,
                        ) if pid in queued else None)
                        for pid, order in (
                            (row.planet_id, queued.get(row.planet_id))
                            for row in plan.bases
                        )
                    },
                    full_fleet_and_base_roster_asserted=True,
                    complete_player_pbp_balances_asserted=True,
                    no_pb_codes_clones_or_other_priority_orders_asserted=True,
                    exact_single_precombat_priority_subphase_asserted=True,
                )
                result = simulate_classic_joint_priority_standard_turn(
                    game, specs,
                    ClassicJointContext(priority, standard, queued),
                    placement=("classic_joint_builds_before_planetary"
                               if plan.placement == PLACEMENTS[0]
                               else "classic_joint_builds_after_planetary"),
                    standard_rules_asserted=True,
                    complete_queue_and_component_scope_asserted=True,
                    no_other_ship_or_base_actions_asserted=True,
                    seed=seed + index,
                )
                if (
                    not result.supported or result.state is None
                    or result.last_standard_pointer_after is None
                ):
                    raise UnsupportedClassicCarry("priority+standard turn was unsupported")
                next_game = result.state
                points_after = result.pbps_after
                pointer_after = result.last_standard_pointer_after
                new_stock = dict(result.warehouse_after)
                priority_id = result.priority_ship_id
                ordinary_ids = result.selected_standard_ship_ids
                exact = all(r.resource_balance_exact for r in result.planet_balances)
                subphase = "PRIORITY_THEN_STANDARD"
            else:
                result = simulate_classic_standard_pointer_economy_turn(
                    game, specs, standard, queued,
                    placement=("classic_standard_before_planetary"
                               if plan.placement == PLACEMENTS[0]
                               else "classic_standard_after_planetary"),
                    standard_rules_asserted=True,
                    complete_warehouses_and_hull_rights_asserted=True,
                    no_other_ship_base_or_combat_actions_asserted=True,
                    seed=seed + index,
                )
                if (
                    not result.supported or result.state is None
                    or result.last_standard_build_planet_id_after is None
                ):
                    raise UnsupportedClassicCarry("standard-only turn was unsupported")
                next_game = result.state
                points_after = carry.player_pbps
                pointer_after = result.last_standard_build_planet_id_after
                new_stock = dict(result.warehouse_states_after)
                priority_id = None
                ordinary_ids = result.selected_ship_ids
                exact = all(r.resource_balance_exact for r in result.planet_balances)
                subphase = "STANDARD_ONLY"
            if next_game.turn != game.turn + 1 or not exact:
                raise UnsupportedClassicCarry("nonconsecutive turn or unbalanced economy")
            for pid, value in new_stock.items():
                if pid not in warehouse or type(value) is not StandardComponentWarehouse:
                    raise UnsupportedClassicCarry("unexpected warehouse identity")
                warehouse[pid] = value
            if set(warehouse) != set(original_base_owners):
                raise UnsupportedClassicCarry("warehouse roster changed")
            carried_stock = tuple(sorted(warehouse.items()))
            all_ids = ((priority_id,) if priority_id is not None else ()) + ordinary_ids
            if (
                len(set(all_ids)) != len(all_ids)
                or set(next_game.ships) != set(game.ships) | set(all_ids)
            ):
                raise UnsupportedClassicCarry("unexplained carried ship IDs")
            carry = ClassicQueueCarryState(
                ship_limit=carry.ship_limit,
                last_standard_build_planet_id=pointer_after,
                player_pbps=points_after,
                all_base_warehouses=carried_stock,
            )
            output.append(ClassicCarryTurnReceipt(
                turn_after=next_game.turn,
                queue_subphase=subphase,
                priority_ship_id=priority_id,
                standard_ship_ids=ordinary_ids,
                allocated_ship_ids=all_ids,
                pbps_after=points_after,
                last_standard_pointer_after=pointer_after,
                base_warehouses_after=carried_stock,
                planet_balance_exact=exact,
            ))
            game = next_game
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return abstain("missing queue data or unexplained inter-turn carry mutation")
    return ClassicCarryOutcome(
        STATUS, state=game, carry_after=carry, turns=tuple(output),
    )
