"""M2 baseline68: conditional mineral mass-balance diagnostics for archive T-1/T.

Do not use this as a NuHost mining rule proof. Archived states include
unobserved orders and special game actions. All model checks are
counterfactual *default-model* candidates with explicit input gates.
Never emit planet/game/player IDs or any raw mineral stock amount.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from planets_lab.rules.mining import (
    DEFAULT_TRANS_URANIUM_RATE, mined_amount, mining_rate_for_race,
    trans_uranium_mutation_amount,
)

MINERALS = ("neutronium", "duranium", "tritanium", "molybdenum")
SUPPORTED_STANDARD_RACES = frozenset(range(1, 12))
MODEL_LABEL = "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL"


def _unsigned(raw: Mapping[str, Any], key: str) -> int | None:
    value = raw.get(key)
    return value if type(value) is int and value >= 0 else None


def _valid_race_pair(before: Mapping[str, Any], after: Mapping[str, Any]) -> int | None:
    b, a = before.get("player"), after.get("player")
    if not isinstance(b, Mapping) or not isinstance(a, Mapping):
        return None
    one, two = b.get("raceid"), a.get("raceid")
    if (type(one) is int and one in SUPPORTED_STANDARD_RACES
            and type(two) is int and two == one):
        return one
    return None


def _magnitude(amount: int) -> str:
    """Bounded aggregate buckets to avoid leaking exact private stock deltas."""
    if amount == 0:
        return "0"
    if amount == 1:
        return "1"
    if amount <= 5:
        return "2_to_5"
    if amount <= 20:
        return "6_to_20"
    if amount <= 100:
        return "21_to_100"
    if amount <= 1000:
        return "101_to_1000"
    return "over_1000"


def profile_archive_mineral_mass_balance(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    owned_before: Mapping[int, Mapping[str, Any]],
    owned_after: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate directional/net mass balance and candidate mining forecasts.

    Pair provenance and owner-current identity gates are enforced by the
    caller. We gate the default model on same observed race, stable mines,
    stable mineral density and numeric T-1 underground stocks.

    Mineral surplus on surface does NOT identify mineral mining.
    Net total surface+ground may vary from ships, construction and other
    abilities, even if the predicted mutation matches exactly.
    """
    per_mineral: dict[str, Counter[str]] = defaultdict(Counter)
    surface_up_ground_equal_hist: dict[str, Counter[str]] = defaultdict(Counter)
    residual_magnitude: dict[str, Counter[str]] = defaultdict(Counter)
    race = _valid_race_pair(before, after)
    planet_ids = sorted(set(owned_before) & set(owned_after))
    for pid in planet_ids:
        b, a = owned_before[pid], owned_after[pid]
        mines_b, mines_a = _unsigned(b, "mines"), _unsigned(a, "mines")
        stable_mines = mines_b is not None and mines_a == mines_b
        for mineral in MINERALS:
            c = per_mineral[mineral]
            gname, dname = "ground" + mineral, "density" + mineral
            surface_before, surface_after = _unsigned(b, mineral), _unsigned(a, mineral)
            ground_before, ground_after = _unsigned(b, gname), _unsigned(a, gname)
            if any(x is None for x in (
                surface_before, surface_after, ground_before, ground_after
            )):
                c["ABSTAIN_MISSING_STOCK_FIELD"] += 1
                continue
            c["joint_stock_qualified"] += 1
            sd = surface_after - surface_before
            gd = ground_after - ground_before
            if sd > 0 and gd == 0:
                c["surface_up_ground_unchanged"] += 1
                surface_up_ground_equal_hist[mineral][_magnitude(sd)] += 1
            if sd > 0 and gd < 0:
                c["surface_up_ground_down"] += 1
            if gd > 0:
                c["ground_increased"] += 1
            if mines_b is None or mines_a is None:
                c["ABSTAIN_MINES_MISSING"] += 1
            elif mines_b != mines_a:
                c["ABSTAIN_MINES_CHANGED"] += 1
            else:
                c["mines_stable"] += 1

            density_before, density_after = _unsigned(b, dname), _unsigned(a, dname)
            if density_before is None or density_after is None:
                c["ABSTAIN_DENSITY_MISSING"] += 1
                continue
            if density_before > 100 or density_after > 100:
                c["ABSTAIN_DENSITY_OUTSIDE_STANDARD_0_TO_100"] += 1
                continue
            if density_before != density_after:
                c["ABSTAIN_DENSITY_CHANGED"] += 1
                continue
            c["density_stable_and_valid"] += 1

            mutation = trans_uranium_mutation_amount(
                density=density_before, mutation_rate=DEFAULT_TRANS_URANIUM_RATE
            )
            observed_total_change = sd + gd
            c["default_mutation_mass_balance_qualified"] += 1
            if observed_total_change == mutation:
                c["net_stock_change_equals_default_mutation"] += 1
            else:
                c["net_stock_change_differs_from_default_mutation"] += 1
            residual_magnitude[mineral][_magnitude(abs(observed_total_change - mutation))] += 1

            if not stable_mines:
                c["ABSTAIN_DEFAULT_MINING_MINES_CHANGED_OR_MISSING"] += 1
                continue
            if race is None:
                c["ABSTAIN_DEFAULT_MINING_RACE_MISSING_OR_CHANGED"] += 1
                continue

            c["candidate_default_mining_qualified"] += 1
            expected_mining = mined_amount(
                mines=mines_b, density=density_before,
                ground_amount=ground_before,
                mining_rate_percent=mining_rate_for_race(race),
                output_modifier_percent=100,
            )
            expected_ground_delta = mutation - expected_mining
            if gd == expected_ground_delta:
                c["ground_delta_matches_default_model"] += 1
            else:
                c["ground_delta_differs_from_default_model"] += 1
            if sd == expected_mining:
                c["surface_delta_matches_default_mining"] += 1
            else:
                c["surface_delta_differs_from_default_mining"] += 1
            if gd == expected_ground_delta and sd == expected_mining:
                c["both_stock_deltas_match_default_model"] += 1
            if gd == 0 and sd > 0:
                c["surface_up_ground_equal_model_qualified"] += 1
                if expected_ground_delta == 0 and expected_mining == sd:
                    c["surface_up_ground_equal_explained_by_default_candidate"] += 1
                else:
                    c["surface_up_ground_equal_unexplained_by_default_candidate"] += 1

    return {
        "evidence_status": "ARCHIVAL_NET_STOCK_HYPOTHESES_NOT_HOST_CAUSAL",
        "candidate_model": MODEL_LABEL,
        "per_mineral": {
            name: dict(sorted(counts.items()))
            for name, counts in sorted(per_mineral.items())
        },
        "surface_up_ground_equal_surface_increase_buckets": {
            name: dict(sorted(counts.items()))
            for name, counts in sorted(surface_up_ground_equal_hist.items())
        },
        "net_total_minus_default_mutation_abs_residual_buckets": {
            name: dict(sorted(counts.items()))
            for name, counts in sorted(residual_magnitude.items())
        },
        "NuHost_mining_formula_verified": False,
        "NuHost_trans_uranium_formula_verified_causally": False,
        "absence_of_unobserved_cargo_or_special_orders_verified": False,
    }
