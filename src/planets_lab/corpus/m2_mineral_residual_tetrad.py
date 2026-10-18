"""M2: disjoint residual taxonomy from a published AGGREGATE corpus report.

Offline postprocessing only. No DuckDB, game API, private state, or
runtime Host proof. Preserve the sealed holdout and original source
report; never mistake correlated planet-mineral observations for
independent validation samples.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCHEMA = "planets-lab.m2-mineral-residual-tetrad.v1"
INPUT_SCHEMA = "planets-lab.m2-public-corpus-economy-coverage.v1"
SOURCE_SHA = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
SELECTION_SHA = "b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f"
MINERALS = ("neutronium", "duranium", "tritanium", "molybdenum")
CATEGORIES = (
    "both_predicted_deltas_exact",
    "ground_only_exact_surface_residual",
    "surface_only_exact_ground_residual",
    "neither_delta_exact",
)


def _count(obj: Mapping[str, Any], key: str) -> int:
    x = obj.get(key, 0)
    if type(x) is not int or x < 0:
        raise ValueError(f"invalid nonnegative aggregate count: {key}")
    return x


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def residual_tetrad(report: Mapping[str, Any]) -> dict[str, Any]:
    """Extract exact (ground yes/no) × (surface yes/no) cross-tab.

    Derive the four disjoint categories by inclusion/exclusion from
    the count totals in the already-published mineral model section.
    Entirely aggregate arithmetic. This *does not* identify reasons
    for a surface residual or assert Host implementation parity.
    """
    _require(report.get("schema") == INPUT_SCHEMA, "unexpected M2 source schema")
    generation = report.get("generation")
    baseline = report.get("baseline_sample_allowlist")
    metadata = report.get("metadata")
    limits = report.get("evidence_limits")
    _require(isinstance(generation, Mapping) and
             generation.get("verified_sha256") == SOURCE_SHA and
             generation.get("read_only") is True and
             generation.get("CURRENT_modified") is False, "wrong corpus generation")
    _require(isinstance(baseline, Mapping) and
             baseline.get("allowed_game_count") == 68 and
             baseline.get("heldout_entity_sampling") is False, "heldout violation")
    _require(isinstance(metadata, Mapping) and
             metadata.get("metadata_frozen_selection_sha256") == SELECTION_SHA and
             metadata.get("metadata_frozen_sample_pairs") == 136 and
             metadata.get("games_excluded_from_entity_sampling") == 32,
             "source cohort changed")
    _require(isinstance(limits, Mapping) and all(
        limits.get(k) is False for k in (
            "NuHost_economic_formula_verified", "raw_trn_is_submitted_turn_orders",
            "default_mining_and_mutation_forecast_is_host_causal",
        )
    ), "must preserve noncausal evidence limits")
    sample = report.get("sample")
    _require(isinstance(sample, Mapping), "no aggregate sample")
    model = sample.get("conditional_mineral_mass_balance_not_host_verified")
    _require(isinstance(model, Mapping) and model.get("model") == (
        "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL"
    ), "not published default conditional model")
    by_mineral = model.get("per_mineral")
    _require(isinstance(by_mineral, Mapping) and set(by_mineral) == set(MINERALS),
             "incomplete mineral model results")

    totals = {key: 0 for key in (*CATEGORIES, "qualified", "residual_total",
                                  "ground_exact", "surface_exact")}
    per_mineral: dict[str, Any] = {}
    for mineral in MINERALS:
        counts = by_mineral[mineral]
        _require(isinstance(counts, Mapping), "invalid aggregate mineral counts")
        q = _count(counts, "candidate_default_mining_qualified")
        g = _count(counts, "ground_delta_matches_default_model")
        s = _count(counts, "surface_delta_matches_default_mining")
        both = _count(counts, "both_stock_deltas_match_default_model")
        _require(q > 0 and 0 <= both <= min(g, s) <= q and
                 max(g, s) <= q, "inconsistent fitted sample denominators")
        ground_only = g - both
        surface_only = s - both
        neither = q - g - s + both
        _require(neither >= 0, "inconsistent overlap of exact ground and surface")
        residuals = q - both
        _require(ground_only + surface_only + neither == residuals,
                 "cross-tab count mismatch")
        described = {
            "qualified": q,
            "both_predicted_deltas_exact": both,
            "ground_only_exact_surface_residual": ground_only,
            "surface_only_exact_ground_residual": surface_only,
            "neither_delta_exact": neither,
            "residual_total": residuals,
            "ground_exact": g,
            "surface_exact": s,
        }
        for key, value in described.items():
            totals[key] += value
        per_mineral[mineral] = described

    # Aggregate proportions use mineral×planet-pair as a unit,
    # not 13K independent games / player decisions / Host executions.
    totals["fraction_both_exact_percent"] = round(
        100 * totals["both_predicted_deltas_exact"] / totals["qualified"], 2
    )
    totals["fraction_ground_only_among_residuals_percent"] = round(
        100 * totals["ground_only_exact_surface_residual"] /
        totals["residual_total"], 2
    )
    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_ARCHIVAL_RESIDUAL_CROSS_TAB_NOT_HOST_CAUSAL",
        "source": {
            "generation_sha256": SOURCE_SHA,
            "selection_sha256": SELECTION_SHA,
            "source_model": model["model"],
            "baseline_entity_games": 68,
            "sealed_holdout_entity_games": 0,
        },
        "per_mineral": per_mineral,
        "aggregate": totals,
        "next_evidence_gates": {
            "surface_only_mismatch_means_cargo_transfer_proven": False,
            "ground_mismatch_implies_mining_formula_wrong": False,
            "observations_independent_at_planet_mineral_level": False,
            "host_executed_order_trace_available": False,
        },
    }
