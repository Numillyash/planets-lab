"""M2: exact cross-tab from safe aggregate output, no 26-GiB archive."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.m2_mineral_residual_tetrad import residual_tetrad

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/diagnostics/m2_mineral_residual_tetrad_v1.py"

# These are the already PUBLISHED aggregate-only counts on runtime-logs,
# NOT private game IDs, raw planet rows, HAR captures or newly opened holdouts.
PUBLISHED = {
    "duranium": (3255, 3181, 2966, 2955),
    "molybdenum": (3256, 3184, 2947, 2939),
    "neutronium": (3256, 3178, 2983, 2976),
    "tritanium": (3256, 3185, 2950, 2943),
}


def report():
    return {
        "schema": "planets-lab.m2-public-corpus-economy-coverage.v1",
        "generation": {
            "verified_sha256": "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c",
            "read_only": True,
            "CURRENT_modified": False,
        },
        "baseline_sample_allowlist": {
            "allowed_game_count": 68, "heldout_entity_sampling": False,
        },
        "metadata": {
            "metadata_frozen_selection_sha256":
                "b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f",
            "metadata_frozen_sample_pairs": 136,
            "games_excluded_from_entity_sampling": 32,
        },
        "evidence_limits": {
            "NuHost_economic_formula_verified": False,
            "raw_trn_is_submitted_turn_orders": False,
            "default_mining_and_mutation_forecast_is_host_causal": False,
        },
        "sample": {
            "conditional_mineral_mass_balance_not_host_verified": {
                "model": "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL",
                "per_mineral": {
                    name: {
                        "candidate_default_mining_qualified": q,
                        "ground_delta_matches_default_model": g,
                        "surface_delta_matches_default_mining": s,
                        "both_stock_deltas_match_default_model": both,
                    }
                    for name, (q, g, s, both) in PUBLISHED.items()
                },
            },
        },
    }


def test_published_residuals_form_exact_disjoint_tetrad():
    data = residual_tetrad(report())
    assert data["per_mineral"]["duranium"] == {
        "qualified": 3255,
        "both_predicted_deltas_exact": 2955,
        "ground_only_exact_surface_residual": 226,
        "surface_only_exact_ground_residual": 11,
        "neither_delta_exact": 63,
        "residual_total": 300,
        "ground_exact": 3181,
        "surface_exact": 2966,
    }
    assert data["per_mineral"]["molybdenum"][
        "ground_only_exact_surface_residual"
    ] == 245
    assert data["per_mineral"]["neutronium"][
        "ground_only_exact_surface_residual"
    ] == 202
    assert data["per_mineral"]["tritanium"][
        "ground_only_exact_surface_residual"
    ] == 242
    summary = data["aggregate"]
    assert summary == {
        "qualified": 13023,
        "both_predicted_deltas_exact": 11813,
        "ground_only_exact_surface_residual": 915,
        "surface_only_exact_ground_residual": 33,
        "neither_delta_exact": 262,
        "residual_total": 1210,
        "ground_exact": 12728,
        "surface_exact": 11846,
        "fraction_both_exact_percent": 90.71,
        "fraction_ground_only_among_residuals_percent": 75.62,
    }
    assert all(value is False for value in data["next_evidence_gates"].values())


def test_ground_surface_residuals_do_not_claim_cause():
    original = report()
    original["sample"]["conditional_mineral_mass_balance_not_host_verified"][
        "per_mineral"
    ]["duranium"]["ground_delta_matches_default_model"] = 2
    with pytest.raises(ValueError, match="inconsistent"):
        residual_tetrad(original)
    original = report()
    original["sample"]["conditional_mineral_mass_balance_not_host_verified"][
        "per_mineral"
    ]["duranium"]["both_stock_deltas_match_default_model"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        residual_tetrad(original)


@pytest.mark.parametrize("kind", [
    "heldout", "sha", "selection", "host", "missing_mineral", "missing_model",
])
def test_fails_closed_if_published_evidence_identity_changes(kind):
    source = report()
    if kind == "heldout":
        source["baseline_sample_allowlist"]["heldout_entity_sampling"] = True
    elif kind == "sha":
        source["generation"]["verified_sha256"] = "0" * 64
    elif kind == "selection":
        source["metadata"]["metadata_frozen_selection_sha256"] = "0" * 64
    elif kind == "host":
        source["evidence_limits"]["NuHost_economic_formula_verified"] = True
    elif kind == "missing_mineral":
        del source["sample"]["conditional_mineral_mass_balance_not_host_verified"][
            "per_mineral"
        ]["neutronium"]
    elif kind == "missing_model":
        del source["sample"]["conditional_mineral_mass_balance_not_host_verified"][
            "model"
        ]
    with pytest.raises(ValueError):
        residual_tetrad(source)


def test_cli_uses_existing_local_report_only_and_no_overwrite(tmp_path):
    infile = tmp_path / "existing_aggregate.json"
    outfile = tmp_path / "derived_tetrad.json"
    infile.write_text(json.dumps(report()), encoding="utf-8")
    command = [
        sys.executable, str(CLI), "--input", str(infile),
        "--output", str(outfile),
    ]
    process = subprocess.run(
        command, capture_output=True, text=True, cwd=ROOT, timeout=20,
    )
    assert process.returncode == 0, process.stderr
    assert "aggregate_json_written: true" in process.stdout
    assert "13023" in process.stdout
    assert "sealed_holdout_entities_accessed: 0" in process.stdout
    assert "runtime-logs/" not in process.stdout
    recorded = json.loads(outfile.read_text())
    assert recorded["aggregate"]["ground_only_exact_surface_residual"] == 915
    repeat = subprocess.run(
        command, capture_output=True, text=True, cwd=ROOT, timeout=20,
    )
    assert repeat.returncode != 0
    assert json.loads(outfile.read_text()) == recorded


def test_qualified_zero_is_refused_without_division():
    original = report()
    for key in original["sample"]["conditional_mineral_mass_balance_not_host_verified"][
        "per_mineral"
    ]["duranium"]:
        original["sample"]["conditional_mineral_mass_balance_not_host_verified"][
            "per_mineral"
        ]["duranium"][key] = 0
    with pytest.raises(ValueError, match="inconsistent"):
        residual_tetrad(original)
