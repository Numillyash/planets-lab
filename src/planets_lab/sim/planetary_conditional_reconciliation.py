"""Bounded M2 replay-vs-observed reconciliation with explicit order provenance.

The comparison reuses the existing order-aware planetary pipeline for both
hypothetical transfer placements. It does not reverse-infer player orders from
archived mineral/cargo differences and does not claim NuHost parity. Complete
pre/post GameState observations and complete pre-Host orders must be asserted
or owner-capture admitted by the caller before any conditional comparison.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

from planets_lab.core import Cargo, GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.orders import TurnOrders
from planets_lab.sim.planet_cargo_transfer_phase import TRANSFER_FIELDS
from planets_lab.sim.planetary_order_aware_slice import (
    MINERALS,
    PhaseResourceBalance,
    PlanetaryOrderAwareSlice,
)
from planets_lab.sim.planetary_owner_capture import (
    aggregate_owner_observations,
)

PLACEMENTS = ("transfer_before_planetary", "transfer_after_planetary")
RESOURCE_SECTIONS = ("planets", "ships", "ground")
ORDER_SOURCE_ASSERTED = "CALLER_ASSERTED_COMPLETE_ORDERS_NOT_SERVER_VERIFIED"


@dataclass(frozen=True, slots=True)
class PlacementComparison:
    placement: str
    status: str
    resource_exact: bool = False
    full_model_state_exact: bool = False
    # Positive values are observed minus the conditional simulation.
    resource_residuals: dict[str, dict[int, dict[str, int]]] = field(default_factory=dict)
    balances: tuple[PhaseResourceBalance, ...] = ()
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ConditionalTransitionReconciliation:
    status: str
    placements: tuple[PlacementComparison, ...] = ()
    full_match_placements: tuple[str, ...] = ()
    resource_match_placements: tuple[str, ...] = ()
    order_source: str | None = None
    abstain_reason: str | None = None
    nuhost_orders_executed_verified: bool = False
    nuhost_phase_placement_verified: bool = False
    independent_host_parity_verified: bool = False


def _inventory(state: GameState) -> dict[str, dict[int, dict[str, int]]]:
    sections = {
        "planets": {
            planet_id: {name: getattr(planet.cargo, name) for name in TRANSFER_FIELDS}
            for planet_id, planet in sorted(state.planets.items())
        },
        "ships": {
            ship_id: {name: getattr(ship.cargo, name) for name in TRANSFER_FIELDS}
            for ship_id, ship in sorted(state.ships.items())
        },
        "ground": {
            planet_id: {
                mineral: getattr(planet, "ground_" + mineral).amount
                for mineral in MINERALS
            }
            for planet_id, planet in sorted(state.planets.items())
        },
    }
    for entities in sections.values():
        for fields in entities.values():
            if any(type(amount) is not int or amount < 0 for amount in fields.values()):
                raise ValueError("incomplete or nonphysical numeric resource snapshot")
    return sections


def _resource_difference(
    expected: dict[str, dict[int, dict[str, int]]],
    observed: dict[str, dict[int, dict[str, int]]],
) -> dict[str, dict[int, dict[str, int]]]:
    if any(expected[section].keys() != observed[section].keys()
           for section in RESOURCE_SECTIONS):
        raise ValueError("observed resource entities do not match model entities")
    result: dict[str, dict[int, dict[str, int]]] = {}
    for section in RESOURCE_SECTIONS:
        rows: dict[int, dict[str, int]] = {}
        for entity_id, values in expected[section].items():
            if values.keys() != observed[section][entity_id].keys():
                raise ValueError("resource field coverage mismatch")
            delta = {
                name: observed[section][entity_id][name] - amount
                for name, amount in values.items()
                if observed[section][entity_id][name] != amount
            }
            if delta:
                rows[entity_id] = delta
        if rows:
            result[section] = rows
    return result


def _ledger_reconciles(
    before: dict[str, dict[int, dict[str, int]]],
    modeled: dict[str, dict[int, dict[str, int]]],
    balances: tuple[PhaseResourceBalance, ...],
) -> bool:
    """Every phase delta must telescope to its modeled end inventory."""
    accum = {
        section: {
            entity_id: {name: 0 for name in values}
            for entity_id, values in before[section].items()
        }
        for section in RESOURCE_SECTIONS
    }
    for balance in balances:
        by_section = {
            "planets": balance.planet_cargo_delta,
            "ships": balance.ship_cargo_delta,
            "ground": balance.ground_mineral_delta,
        }
        for section, entities in by_section.items():
            for entity_id, values in entities.items():
                if entity_id not in accum[section]:
                    return False
                for name, delta in values.items():
                    if name not in accum[section][entity_id] or type(delta) is not int:
                        return False
                    accum[section][entity_id][name] += delta
    return all(
        accum[section][entity_id][name]
        == modeled[section][entity_id][name] - before[section][entity_id][name]
        for section in RESOURCE_SECTIONS
        for entity_id, values in before[section].items()
        for name in values
    )


def _check_bounded_pair(before: GameState, after: GameState) -> None:
    if type(before) is not GameState or type(after) is not GameState:
        raise ValueError("both observations must be complete GameState values")
    before.validate()
    after.validate()
    if (type(before.game_id) is not type(after.game_id)
            or before.game_id != after.game_id or after.turn != before.turn + 1):
        raise ValueError("game identity or adjacent turn provenance mismatch")
    if (before.players != after.players
            or before.planets.keys() != after.planets.keys()
            or before.ships.keys() != after.ships.keys()):
        raise ValueError("player/planet/ship roster changed outside bounded slice")
    if before.starbases or after.starbases or before.ion_storms or after.ion_storms:
        raise ValueError("starbases and ion storms are outside bounded slice")
    for planet_id, original in before.planets.items():
        new = after.planets[planet_id]
        if (original.x, original.y) != (new.x, new.y):
            raise ValueError("planet position changed")
        if original.owner_id is not None and original.owner_id != new.owner_id:
            raise ValueError("planet ownership changed outside colonization support")
    for ship_id, original in before.ships.items():
        new = after.ships[ship_id]
        # A cargo-only comparison cannot silently treat movement, ship capture,
        # outfitting, ammunition use or combat as a modeled transfer operation.
        if replace(original, cargo=Cargo()) != replace(new, cargo=Cargo()):
            raise ValueError("ship noncargo state changed outside bounded slice")


def _full_model_state_exact(modeled: GameState, observed: GameState) -> bool:
    # Never couple a gameplay match to private capture metadata.
    return all(
        getattr(modeled, attr) == getattr(observed, attr)
        for attr in ("game_id", "turn", "players", "planets", "ships", "starbases", "ion_storms")
    )


def reconcile_explicit_orders(
    before: GameState,
    observed_after: GameState,
    orders: TurnOrders,
    specs: NuStaticSpecs,
    *,
    complete_orders: bool = False,
    complete_snapshots: bool = False,
    seed: int = 0,
) -> ConditionalTransitionReconciliation:
    """Compare two conditional phase placements against one complete observed T.

    A caller declaration of completeness is NOT independent authentication of
    submitted Host orders, source clocks, or NuHost rule selection. Historical
    records without orders must never pass by substituting TurnOrders.empty().
    """
    if complete_orders is not True or complete_snapshots is not True:
        return ConditionalTransitionReconciliation(
            "ABSTAIN_INCOMPLETE_ORDER_OR_SNAPSHOT_COVERAGE",
            abstain_reason="complete independent orders and full snapshots required",
        )
    try:
        _check_bounded_pair(before, observed_after)
        pre_inventory = _inventory(before)
        observed_inventory = _inventory(observed_after)
    except (ValueError, AttributeError, TypeError) as exc:
        return ConditionalTransitionReconciliation(
            "ABSTAIN_UNSUPPORTED_PAIR", abstain_reason=str(exc),
        )

    comparisons: list[PlacementComparison] = []
    for placement in PLACEMENTS:
        outcome = PlanetaryOrderAwareSlice(specs, placement).attempt_step(
            before, orders, seed=seed
        )
        if not outcome.supported or outcome.state is None:
            comparisons.append(PlacementComparison(
                placement, "ABSTAIN_PLACEMENT_UNSUPPORTED",
                reason=outcome.abstain_reason or "no supported model outcome",
            ))
            continue
        modeled_inventory = _inventory(outcome.state)
        if not _ledger_reconciles(pre_inventory, modeled_inventory, outcome.balances):
            return ConditionalTransitionReconciliation(
                "ABSTAIN_INTERNAL_RESOURCE_LEDGER",
                abstain_reason="phase balances do not reconcile to modeled inventories",
            )
        residuals = _resource_difference(modeled_inventory, observed_inventory)
        comparisons.append(PlacementComparison(
            placement=placement,
            status="CONDITIONAL_MODELED",
            resource_exact=not residuals,
            full_model_state_exact=(
                not residuals and _full_model_state_exact(outcome.state, observed_after)
            ),
            resource_residuals=residuals,
            balances=outcome.balances,
        ))
    full = tuple(c.placement for c in comparisons if c.full_model_state_exact)
    resources = tuple(c.placement for c in comparisons if c.resource_exact)
    supported = any(c.status == "CONDITIONAL_MODELED" for c in comparisons)
    if not supported:
        return ConditionalTransitionReconciliation(
            "ABSTAIN_NO_SUPPORTED_PLACEMENT", placements=tuple(comparisons),
            order_source=ORDER_SOURCE_ASSERTED,
            abstain_reason="both conditional placements rejected the supplied orders",
        )
    status = (
        "CONDITIONAL_FULL_MATCH_BOTH_PLACEMENTS_NOT_CAUSAL" if len(full) == 2
        else "CONDITIONAL_FULL_MATCH_ONE_PLACEMENT_NOT_CAUSAL" if full
        else "CONDITIONAL_RESOURCE_ONLY_MATCH_NOT_CAUSAL" if resources
        else "CONDITIONAL_UNATTRIBUTED_MISMATCH"
    )
    return ConditionalTransitionReconciliation(
        status=status, placements=tuple(comparisons),
        full_match_placements=full, resource_match_placements=resources,
        order_source=ORDER_SOURCE_ASSERTED,
    )


def reconcile_owner_observations(
    before: GameState,
    observed_after: GameState,
    envelopes: Sequence[object],
    specs: NuStaticSpecs,
    *,
    owner_keyrings: Mapping[int, Mapping[str, bytes]],
    observed_host_start_utc: str | None,
    complete_snapshots: bool = False,
    seed: int = 0,
) -> ConditionalTransitionReconciliation:
    """Admit all owner-signed pre-Host records before conditional differential.

    The signatures authenticate the operators' local records, not Host receipt
    or the timestamp's physical truth; independent parity remains unverified.
    """
    admission = aggregate_owner_observations(
        envelopes, before,
        owner_keyrings=owner_keyrings,
        observed_host_start_utc=observed_host_start_utc,
    )
    if not admission.admitted or admission.orders is None:
        return ConditionalTransitionReconciliation(
            admission.status, abstain_reason=admission.reason,
        )
    result = reconcile_explicit_orders(
        before, observed_after, admission.orders, specs,
        complete_orders=True, complete_snapshots=complete_snapshots, seed=seed,
    )
    return replace(result, order_source=admission.status)
