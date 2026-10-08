"""Conditional Classic combat outcome ensemble, without a factual VCR seed.

This is a *single known engagement* evaluator. The caller supplies both sides'
already-resolved combat setup, weapon catalog, and combat RNG mode. The input
MUST omit VCR seed and both VCR combat masses; those are generated here from
explicit hull specs and a documented but stochastic right-side carrier bonus.

Uniform independent seed weighting and independent Bernoulli(0.60) mass-bonus
weighting are SCENARIO ASSUMPTIONS, not recovered NuHost global-RNG rules.
Unknown effective combat modifiers, side assignment, or precombat state are
not reconstructed by this module.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .classic import ReplayUnsupported
from .nu import replay_nuhost_from_nu_catalog


CLASSIC_START_SEEDS = tuple(range(1, 119))


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _validate_known_setup(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if "seed" in payload:
        raise ReplayUnsupported("factual VCR seed is forbidden in ensemble input")
    sides: list[Mapping[str, Any]] = []
    for name in ("left", "right"):
        side = payload.get(name)
        if not isinstance(side, Mapping):
            raise ReplayUnsupported(f"{name}: precombat side input missing")
        if "mass" in side:
            raise ReplayUnsupported(f"{name}: factual VCR mass is forbidden in ensemble input")
        for key in (
            "objectid", "hullid", "raceid", "beamcount", "launchercount",
            "baycount", "beamid", "torpedoid", "shield", "damage", "crew",
            "torpedos", "fighters", "beamkillbonus", "beamchargerate",
            "torpchargerate", "torpmisspercent", "crewdefensepercent",
        ):
            if _int(side.get(key)) is None:
                raise ReplayUnsupported(f"{name}: unresolved effective combat field {key}")
        if side["hullid"] <= 0:
            raise ReplayUnsupported("v1 supports ship-vs-ship only")
        sides.append(side)
    for name in ("leftownerid", "rightownerid"):
        if _int(payload.get(name)) is None:
            raise ReplayUnsupported(f"unresolved combat owner {name}")
    return sides[0], sides[1]


def evaluate_conditional_classic(
    payload_without_seed_or_mass: Mapping[str, Any],
    *,
    beams: Sequence[Mapping[str, Any]],
    torpedoes: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any],
    left_hull_mass: int,
    right_hull_mass: int,
    assumed_no_other_mass_modifiers: bool,
    seed_values: Sequence[int] = CLASSIC_START_SEEDS,
    right_carrier_bonus_probability: float = 0.60,
) -> dict[str, Any]:
    """Exhaustively weight (seed, combat-mass) scenarios for one known pair.

    Zero/negative side hull masses, unqualified bonus assumptions, incomplete
    effective fields, empty/duplicate/invalid seeds and unsupported Classic RNG
    fail closed. No inputs are mutated.
    """
    left, right = _validate_known_setup(payload_without_seed_or_mass)
    if assumed_no_other_mass_modifiers is not True:
        raise ReplayUnsupported(
            "other combat-mass modifiers unresolved: explicit scenario assumption required"
        )
    if (
        _int(left_hull_mass) is None or left_hull_mass <= 0
        or _int(right_hull_mass) is None or right_hull_mass <= 0
    ):
        raise ReplayUnsupported("independent hull catalog mass missing or invalid")
    if (
        isinstance(right_carrier_bonus_probability, bool)
        or not isinstance(right_carrier_bonus_probability, (float, int))
        or not 0 <= right_carrier_bonus_probability <= 1
    ):
        raise ReplayUnsupported("carrier bonus probability invalid")

    seeds = tuple(seed_values)
    if (
        not seeds or len(set(seeds)) != len(seeds)
        or any(_int(seed) is None or seed not in CLASSIC_START_SEEDS for seed in seeds)
    ):
        raise ReplayUnsupported("seed ensemble must be a nonempty unique subset of 1..118")


    # Horwasp mass is clan-dependent and may change between combats.
    # We cannot silently use Classic hull mass in a probability evaluator.
    if left["raceid"] == 12 or right["raceid"] == 12:
        raise ReplayUnsupported(
            "Horwasp clan-dependent combat mass is unresolved in Classic ensemble"
        )

    # Cross-game observations include a Federation hull below 140 KT whose
    # +50 Federation bonus moves it above 140 KT before the +360 branch.
    # The ordering/eligibility rule is not yet independently established.
    # Do not produce a misleading single-branch distribution here.
    if (
        right["raceid"] == 1 and right_hull_mass < 140
        and right_hull_mass + 50 >= 140
        and left["baycount"] > 0
    ):
        raise ReplayUnsupported(
            "Federation-adjusted 140 KT anti-carrier eligibility unresolved"
        )

    left_mass = left_hull_mass + (50 if left["raceid"] == 1 else 0)
    right_mass = right_hull_mass + (50 if right["raceid"] == 1 else 0)
    carrier_eligible = bool(right_hull_mass >= 140 and left["baycount"] > 0)
    if carrier_eligible:
        masses = [
            (right_mass, 1 - float(right_carrier_bonus_probability), "no_bonus"),
            (right_mass + 360, float(right_carrier_bonus_probability), "carrier_plus_360"),
        ]
        masses = [(mass, prob, label) for mass, prob, label in masses if prob > 0]
    else:
        masses = [(right_mass, 1.0, "no_bonus")]

    # This dict contains only caller-known, current-encounter fields.
    # Neither factual seed nor factual combat mass enters the evaluator.
    base = deepcopy(dict(payload_without_seed_or_mass))
    outcome_probability: defaultdict[str, float] = defaultdict(float)
    side_probability: dict[str, defaultdict[str, float]] = {
        "left": defaultdict(float), "right": defaultdict(float)
    }
    side_expected: dict[str, defaultdict[str, float]] = {
        "left": defaultdict(float), "right": defaultdict(float)
    }
    scenario_count = 0
    weight_total = 0.0
    for mass, mass_probability, _label in masses:
        for seed in seeds:
            trial = deepcopy(base)
            trial["seed"] = seed
            trial["left"]["mass"] = left_mass
            trial["right"]["mass"] = mass
            terminal = replay_nuhost_from_nu_catalog(
                trial, beams=beams, torpedoes=torpedoes, settings=settings
            )
            weight = mass_probability / len(seeds)
            scenario_count += 1
            weight_total += weight
            result = terminal.get("result")
            if not isinstance(result, list):
                raise ReplayUnsupported("Classic replay result shape unresolved")
            outcome_probability["+".join(sorted(result))] += weight
            for side_name in ("left", "right"):
                side_result = terminal.get(side_name)
                if not isinstance(side_result, Mapping):
                    raise ReplayUnsupported("Classic replay terminal side missing")
                for flag in ("destroyed", "captured", "survived"):
                    if side_result.get(flag) is True:
                        side_probability[side_name][flag] += weight
                for field in ("shield", "damage", "crew", "torpedoes", "fighters"):
                    value = _int(side_result.get(field))
                    if value is None:
                        raise ReplayUnsupported(f"Classic replay terminal {field} unresolved")
                    side_expected[side_name][field] += weight * value

    def clean(values: Mapping[str, float]) -> dict[str, float]:
        return {key: round(value, 10) for key, value in sorted(values.items())}

    return {
        "schema": "planets-lab.combat-conditional-ensemble.v1",
        "status": "CONDITIONAL_SCENARIO_MODEL_NOT_HOST_PROBABILITIES",
        "side_ids": {
            "left": left["objectid"],
            "right": right["objectid"],
        },
        "scenario_count": scenario_count,
        "seed_count": len(seeds),
        "seed_assumption": "uniform_1_to_118" if seeds == CLASSIC_START_SEEDS else "uniform_explicit_subset",
        "seed_values": list(seeds),
        "carrier_eligible": carrier_eligible,
        "mass_scenarios": [
            {"right_mass": mass, "assumed_probability": round(prob, 10), "branch": label}
            for mass, prob, label in masses
        ],
        "left_mass": left_mass,
        "total_probability": round(weight_total, 10),
        "outcome_probabilities": clean(outcome_probability),
        "sides": {
            side: {
                "probabilities": clean(side_probability[side]),
                "expected_terminal": clean(side_expected[side]),
            }
            for side in ("left", "right")
        },
        "evidence_boundary": (
            "The encounter's sides, identity, effective weapons, ammunition, "
            "shields, crew, race, modifiers and combat RNG setting MUST already "
            "be known. This module generates ONLY possible seeds and documented "
            "combat masses; other mass modifiers are explicitly assumed absent. "
            "Seed uniformity and independence of the +360 Bernoulli event are "
            "scenario weights, NOT observed Host RNG probabilities. Not an "
            "independent NuHost input generator; never use a future VCR as "
            "a causal input."
        ),
    }
