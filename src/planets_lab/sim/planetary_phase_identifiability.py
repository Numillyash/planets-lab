"""Synthetic six-order phase identifiability, without external NuHost evidence.

A successful internal replay does not establish the accepted Host orders.
This module asks which of the six conditional M2 phase hypotheses are
OBSERVATIONALLY INDISTINGUISHABLE given one fully modeled initial state
and explicit orders. Only final full-state signatures count: event/phase
trace order is not an independent post-Host observation.

No corpus/HAR/client fetch, player API access, private capture, or file IO.
Model state fingerprints are used solely as internal equality keys; none
are returned as part of public-safe aggregate results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterator, Mapping

from planets_lab.core import GameState, Starbase
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder,
    StarbaseTechUpgradeOrder, TurnOrders,
)
from planets_lab.sim.planetary_conditional_reconciliation import PLACEMENTS, TECH_SLOTS
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_order_capture import state_fingerprint

PHASE_HYPOTHESES = tuple(
    (cargo, tech) for tech in TECH_SLOTS for cargo in PLACEMENTS
)
assert len(PHASE_HYPOTHESES) == 6


@dataclass(frozen=True, slots=True)
class PhaseEquivalenceClass:
    status: str
    placements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PhaseIdentifiability:
    status: str
    classes: tuple[PhaseEquivalenceClass, ...] = ()
    supported_placements: int = 0
    distinct_supported_endstates: int = 0
    unsupported_placements: int = 0
    uniquely_identifiable_from_successful_endstate: bool = False
    nuhost_order_execution_verified: bool = False
    independent_phase_order_verified: bool = False


def evaluate_six_phase_signatures(
    before: GameState, orders: TurnOrders, specs: NuStaticSpecs, *,
    standard_tech_level_caps: Mapping[int, int] | None,
    seed: int = 0,
) -> PhaseIdentifiability:
    """Compare complete final states of all six conditional phase orders.

    A 'failure' is merely an abstention by our incomplete research model.
    It must NOT be interpreted as an actual NuHost rejection or a distinct
    observed server outcome. No outcome/source fingerprint is exposed.
    """
    if standard_tech_level_caps is None:
        return PhaseIdentifiability("ABSTAIN_STANDARD_TECH_CAPS_UNASSERTED")
    if type(before) is not GameState or type(orders) is not TurnOrders:
        return PhaseIdentifiability("ABSTAIN_INCOMPLETE_SYNTHETIC_CONTEXT")
    if not any(
        isinstance(owner, PlayerOrders) and owner.starbase_tech_orders
        for owner in orders.by_player.values()
    ):
        return PhaseIdentifiability("ABSTAIN_NO_EXPLICIT_TECH_ORDER")
    signatures: dict[tuple[str, str], list[str]] = {}
    for cargo_placement, tech_placement in PHASE_HYPOTHESES:
        outcome = PlanetaryOrderAwareSlice(
            specs, cargo_placement, tech_placement=tech_placement,
            standard_tech_level_caps=standard_tech_level_caps,
        ).attempt_step(before, orders, seed=seed)
        if outcome.supported and outcome.state is not None:
            # Fingerprint is an internal equality key only, never published.
            key = ("MODELED", state_fingerprint(outcome.state))
        else:
            # All incomplete model paths share one non-observable bucket.
            key = ("ABSTAIN", "MODEL_UNSUPPORTED_NOT_NUHOST_REJECTION")
        signatures.setdefault(key, []).append(
            cargo_placement + "|" + tech_placement
        )
    classes = tuple(
        PhaseEquivalenceClass(
            "MODELED_SAME_FINAL_STATE" if key[0] == "MODELED" else
            "ABSTAIN_UNSUPPORTED_NOT_OBSERVED_REJECTION",
            tuple(members),
        )
        for key, members in signatures.items()
    )
    supported = sum(
        len(item.placements) for item in classes if item.status == "MODELED_SAME_FINAL_STATE"
    )
    distinct = sum(item.status == "MODELED_SAME_FINAL_STATE" for item in classes)
    assert supported + sum(
        len(item.placements) for item in classes
        if item.status.startswith("ABSTAIN_")
    ) == 6
    return PhaseIdentifiability(
        "DESCRIPTIVE_SYNTHETIC_PHASE_IDENTIFIABILITY_NOT_CAUSAL",
        classes=classes,
        supported_placements=supported,
        distinct_supported_endstates=distinct,
        unsupported_placements=6 - supported,
        uniquely_identifiable_from_successful_endstate=(
            supported == 6 and distinct == 6
        ),
    )


@dataclass(frozen=True, slots=True)
class SyntheticCandidate:
    """A fake, bounded experiment recipe; contains no real game IDs."""
    planet_mc: int
    ship_mc: int
    transfer_mc: int
    transfer_direction: str
    planet_supplies_load: int
    factory_count: int


@dataclass(frozen=True, slots=True)
class SyntheticCandidateResult:
    recipe: SyntheticCandidate
    analysis: PhaseIdentifiability


@dataclass(frozen=True, slots=True)
class SyntheticSearchReport:
    status: str
    candidates_evaluated: int
    all_six_supported_candidates: int
    distinguishable_supported_candidates: int
    candidates_with_unsupported_models: int
    best_all_supported: SyntheticCandidateResult | None
    best_partial: SyntheticCandidateResult | None
    nuhost_order_execution_verified: bool = False
    observed_host_phase_order_verified: bool = False
    historical_corpus_sampled: bool = False


def synthetic_candidates() -> Iterator[SyntheticCandidate]:
    """Fixed 96-case plan, independent of source game and corpus contents.

    Includes positive controls, cash thresholds and potential factory
    replenishment boundaries. No randomness, calibration or archive data.
    """
    cash_inputs = (
        (4000, 800),
        (2000, 600),
        (2250, 600),
        (2400, 300),
    )
    transfer_variants = (
        ("ship_to_planet", 0, 0),
        ("ship_to_planet", 300, 0),
        ("ship_to_planet", 600, 0),
        ("planet_to_ship", 300, 0),
        ("planet_to_ship", 0, 45),
        ("ship_to_planet", 0, 45),
    )
    for (planet_mc, ship_mc), (
        direction, transfer_mc, supply_load
    ), factories in product(cash_inputs, transfer_variants, (0, 10, 20, 30)):
        yield SyntheticCandidate(
            planet_mc, ship_mc, transfer_mc, direction, supply_load, factories,
        )


def materialize_synthetic_case(base: GameState, case: SyntheticCandidate) -> (
    tuple[GameState, TurnOrders]
):
    """Return freshly cloned synthetic state and explicit owner orders."""
    before = base.clone()
    if set(before.planets) != {10} or set(before.ships) != {1}:
        raise ValueError("this synthetic fixture must contain only fake P10 and S1")
    if not {1, 2}.issubset(before.players):
        raise ValueError("synthetic fixture must declare both example owners")
    before.starbases[10] = Starbase(planet_id=10, owner_id=1, tech_engine=7)
    before.planets[10].cargo.megacredits = case.planet_mc
    before.planets[10].factories = case.factory_count
    before.ships[1].cargo.megacredits = case.ship_mc
    cargo = PlanetCargoTransferOrder(
        planet_id=10, direction=case.transfer_direction,
        megacredits=case.transfer_mc,
        supplies=case.planet_supplies_load,
    )
    orders = TurnOrders(by_player={
        1: PlayerOrders(
            player_id=1,
            ship_orders=(ShipOrder(ship_id=1, planet_transfer=cargo),),
            starbase_tech_orders=(StarbaseTechUpgradeOrder(
                planet_id=10, engine=10,
            ),),
        ),
        2: PlayerOrders(player_id=2),
    })
    return before, orders


def search_synthetic_phase_discrimination(
    fixture_state: GameState, specs: NuStaticSpecs, *,
    standard_tech_level_caps: Mapping[int, int],
    max_cases: int = 96,
) -> SyntheticSearchReport:
    """Find discriminating *model* scenarios, not recommended real orders.

    Prefer a six-supported scenario, and rank its count of distinguishable
    observed final states. Separately expose the best case with unsupported
    hypotheses, which cannot be interpreted as a server rejection.
    """
    if type(max_cases) is not int or not 1 <= max_cases <= 96:
        raise ValueError("max_cases must be a strict integer in 1..96")
    best_full: SyntheticCandidateResult | None = None
    best_partial: SyntheticCandidateResult | None = None
    count = full = distinguishable = partial = 0
    for case in synthetic_candidates():
        if count >= max_cases:
            break
        before, orders = materialize_synthetic_case(fixture_state, case)
        evaluation = evaluate_six_phase_signatures(
            before, orders, specs,
            standard_tech_level_caps=standard_tech_level_caps,
        )
        if evaluation.status != "DESCRIPTIVE_SYNTHETIC_PHASE_IDENTIFIABILITY_NOT_CAUSAL":
            raise ValueError("synthetic candidate failed readiness gates")
        count += 1
        result = SyntheticCandidateResult(case, evaluation)
        if evaluation.supported_placements == 6:
            full += 1
            if evaluation.distinct_supported_endstates > 1:
                distinguishable += 1
            if (best_full is None or evaluation.distinct_supported_endstates >
                    best_full.analysis.distinct_supported_endstates):
                best_full = result
        else:
            partial += 1
            if (best_partial is None or
                (evaluation.distinct_supported_endstates,
                 evaluation.supported_placements) >
                (best_partial.analysis.distinct_supported_endstates,
                 best_partial.analysis.supported_placements)):
                best_partial = result
    return SyntheticSearchReport(
        "SYNTHETIC_PHASE_DISCRIMINABILITY_NOT_NUHOST_VERIFIED",
        count, full, distinguishable, partial, best_full, best_partial,
    )
