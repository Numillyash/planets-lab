"""Bounded synthetic multi-turn *economic* reconciliation contract.

Reuses the opt-in structure-plus-14-phase conditional HostEngine without
changing canonical NuHost ordering or the V1/V2 signed PlayerOrders schema.

For every turn AND every observed planet, independently sum emitted
production, tax, mining, mutation, construction and decay events, then
compare expected MC/supplies/mineral/structure differences with the
actual modeled pre/post snapshots. Any unsupported case or imbalance
ABSTAINS for the WHOLE SEQUENCE, never exposing a partial trajectory.
Event compatibility is an internal consistency check, not a receipt
that NuHost executed orders or used the chosen phase placement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from planets_lab.core import GameState
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.planetary_structure_turn_slice import (
    STRUCTURE_PLACEMENTS, simulate_explicit_structure_turn,
)
from planets_lab.sim.standard_structure_build import StructureBuildTargets

MINERALS = ("neutronium", "duranium", "tritanium", "molybdenum")
STRUCTURES = ("defense_posts", "factories", "mines")
CONTRACT_STATUS = "CONDITIONAL_MULTITURN_STANDARD_ECONOMY_BALANCED_NOT_NUHOST_VERIFIED"
MAX_TURNS = 8


class UnsupportedEconomicLedger(ValueError):
    """An unaccounted or inconsistent resource change invalidates the run."""


@dataclass(frozen=True, slots=True)
class StructureTurnPlan:
    targets_by_player: Mapping[int, tuple[StructureBuildTargets, ...]]
    placement: str
    automatic_supply_sale_enabled: bool = False


@dataclass(frozen=True, slots=True)
class PlanetEconomicBalance:
    planet_id: int
    supplies_produced: int = 0
    taxes_collected: int = 0
    construction_supplies: int = 0
    construction_supplies_sold: int = 0
    construction_mc_spent: int = 0
    mined_minerals: tuple[int, int, int, int] = (0, 0, 0, 0)
    ground_minerals_mutated: tuple[int, int, int, int] = (0, 0, 0, 0)
    built_defense_posts: int = 0
    built_factories: int = 0
    built_mines: int = 0
    structures_decayed: tuple[int, int, int] = (0, 0, 0)
    resource_balance_exact: bool = True


@dataclass(frozen=True, slots=True)
class MultiTurnCheckpoint:
    turn_before: int
    turn_after: int
    placement: str
    planet_balances: tuple[PlanetEconomicBalance, ...]
    events: tuple[HostEvent, ...]
    end_state: GameState
    resource_balance_exact: bool = True
    nuhost_execution_verified: bool = False


@dataclass(frozen=True, slots=True)
class MultiTurnEconomicOutcome:
    status: str
    final_state: GameState | None = None
    checkpoints: tuple[MultiTurnCheckpoint, ...] = ()
    reason: str | None = None
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False
    nuhost_phase_placement_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == CONTRACT_STATUS


def _detail_int(event: HostEvent, name: str) -> int:
    fields = dict(event.details)
    if len(fields) != len(event.details):
        raise UnsupportedEconomicLedger("repeated event detail key")
    raw = fields.get(name)
    if raw is None or not raw.isdecimal():
        raise UnsupportedEconomicLedger("missing nonnegative integer event detail")
    return int(raw)


def _decay_count(event: HostEvent, name: str) -> int:
    details = dict(event.details)
    if len(details) != len(event.details):
        raise UnsupportedEconomicLedger("repeated structure decay detail key")
    raw = details.get(name)
    if type(raw) is not str or raw.count("->") != 1:
        raise UnsupportedEconomicLedger("invalid structure decay details")
    a, b = raw.split("->")
    if not a.isdecimal() or not b.isdecimal() or int(b) > int(a):
        raise UnsupportedEconomicLedger("unsupported structure growth in decay phase")
    return int(a) - int(b)


def _planet_ledgers(
    previous: GameState,
    current: GameState,
    events: tuple[HostEvent, ...],
) -> tuple[PlanetEconomicBalance, ...]:
    if (set(previous.planets) != set(current.planets)
            or set(previous.players) != set(current.players)
            or previous.game_id != current.game_id
            or current.turn != previous.turn + 1):
        raise UnsupportedEconomicLedger("changed identities or nonadjacent turn")
    budget = {
        pid: {
            "produced": 0, "taxes": 0, "built_supplies": 0,
            "sold": 0, "spent": 0, "mined": [0] * 4,
            "mutated": [0] * 4, "built_structures": [0] * 3,
            "decayed": [0] * 3,
        }
        for pid in previous.planets
    }
    for event in events:
        phase = event.phase
        if phase not in (
            "factory_supplies", "tax_collection",
            "standard_structure_build_conditional", "mineral_mining",
            "trans_uranium_mutation", "structure_decay",
        ):
            continue
        if event.entity_type != "planet" or type(event.entity_id) is not int:
            raise UnsupportedEconomicLedger("resource event lacks exact planet identity")
        row = budget.get(event.entity_id)
        if row is None:
            raise UnsupportedEconomicLedger("resource event references unknown planet")
        if phase == "factory_supplies":
            row["produced"] += _detail_int(event, "supplies")
        elif phase == "tax_collection":
            row["taxes"] += _detail_int(event, "collected")
        elif phase == "standard_structure_build_conditional":
            row["built_supplies"] += _detail_int(event, "supplies_for_building")
            row["sold"] += _detail_int(event, "supplies_sold")
            row["spent"] += _detail_int(event, "mc_spent")
            for i, name in enumerate(STRUCTURES):
                row["built_structures"][i] += _detail_int(event, "built_" + name)
        elif phase == "mineral_mining":
            for i, mineral in enumerate(MINERALS):
                row["mined"][i] += _detail_int(event, mineral)
        elif phase == "trans_uranium_mutation":
            for i, mineral in enumerate(MINERALS):
                row["mutated"][i] += _detail_int(event, mineral)
        elif phase == "structure_decay":
            for i, name in enumerate(("defense", "factories", "mines")):
                row["decayed"][i] += _decay_count(event, name)
    results: list[PlanetEconomicBalance] = []
    for pid in sorted(previous.planets):
        before, after = previous.planets[pid], current.planets[pid]
        if before.owner_id != after.owner_id:
            raise UnsupportedEconomicLedger("ownership changed during bounded research turn")
        row = budget[pid]
        if (after.cargo.megacredits - before.cargo.megacredits
                != row["taxes"] + row["sold"] - row["spent"]
                or after.cargo.supplies - before.cargo.supplies
                != row["produced"] - row["sold"] - row["built_supplies"]):
            raise UnsupportedEconomicLedger("MC/supplies delta not explained by modeled phases")
        for i, mineral in enumerate(MINERALS):
            ground_name = "ground_" + mineral
            if (getattr(after.cargo, mineral) - getattr(before.cargo, mineral)
                    != row["mined"][i]
                    or getattr(after, ground_name).amount
                       - getattr(before, ground_name).amount
                    != -row["mined"][i] + row["mutated"][i]):
                raise UnsupportedEconomicLedger("surface/ground mineral balance unexplained")
        for i, structure in enumerate(STRUCTURES):
            if (getattr(after, structure) - getattr(before, structure)
                    != row["built_structures"][i] - row["decayed"][i]):
                raise UnsupportedEconomicLedger("structure change unexplained")
        results.append(PlanetEconomicBalance(
            planet_id=pid,
            supplies_produced=row["produced"],
            taxes_collected=row["taxes"],
            construction_supplies=row["built_supplies"],
            construction_supplies_sold=row["sold"],
            construction_mc_spent=row["spent"],
            mined_minerals=tuple(row["mined"]),
            ground_minerals_mutated=tuple(row["mutated"]),
            built_defense_posts=row["built_structures"][0],
            built_factories=row["built_structures"][1],
            built_mines=row["built_structures"][2],
            structures_decayed=tuple(row["decayed"]),
        ))
    return tuple(results)


def simulate_multiturn_standard_economy(
    before: GameState,
    schedule: tuple[StructureTurnPlan, ...],
    *,
    standard_rules_asserted: bool = False,
    complete_structure_target_scope_asserted: bool = False,
    seed: int = 0,
) -> MultiTurnEconomicOutcome:
    """Execute at most eight adjacent conditional turns, all or nothing."""
    def abstain(reason: str) -> MultiTurnEconomicOutcome:
        return MultiTurnEconomicOutcome("ABSTAIN_MULTITURN_STANDARD_ECONOMY", reason=reason)

    if (type(schedule) is not tuple or not 1 <= len(schedule) <= MAX_TURNS
            or type(before) is not GameState or type(seed) is not int):
        return abstain("invalid initial state, seed or fixed turn budget")
    if (standard_rules_asserted is not True
            or complete_structure_target_scope_asserted is not True):
        return abstain("standard rules and full-owner targets not asserted")
    for plan in schedule:
        if (type(plan) is not StructureTurnPlan
                or plan.placement not in STRUCTURE_PLACEMENTS
                or type(plan.automatic_supply_sale_enabled) is not bool):
            return abstain("invalid phase placement or per-turn intent")
    original = before
    checkpoints: list[MultiTurnCheckpoint] = []
    for index, plan in enumerate(schedule):
        step = simulate_explicit_structure_turn(
            original, plan.targets_by_player,
            placement=plan.placement,
            standard_rules_asserted=True,
            complete_structure_target_scope_asserted=True,
            automatic_supply_sale_enabled=plan.automatic_supply_sale_enabled,
            seed=seed + index,
        )
        if not step.supported or step.state is None:
            return abstain("unsupported or incomplete inner conditional turn")
        try:
            budgets = _planet_ledgers(original, step.state, step.events)
        except (UnsupportedEconomicLedger, TypeError, ValueError, AttributeError):
            return abstain("unexplained or inconsistent modeled economic delta")
        checkpoints.append(MultiTurnCheckpoint(
            turn_before=original.turn,
            turn_after=step.state.turn,
            placement=plan.placement,
            planet_balances=budgets,
            events=step.events,
            end_state=step.state,
        ))
        original = step.state
    return MultiTurnEconomicOutcome(
        status=CONTRACT_STATUS,
        final_state=original,
        checkpoints=tuple(checkpoints),
    )
