"""M2 evidence publication: whitelist only aggregate-only baseline68 reports."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py"
WRAPPER = ROOT / "tools/run-m2-public100-economy-coverage-v1-with-evidence.sh"
SHA = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"


def valid_aggregate() -> dict:
    return {
        "schema": "planets-lab.m2-public-corpus-economy-coverage.v1",
        "status": "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL",
        "generation": {
            "name": "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb",
            "verified_sha256": SHA,
            "read_only": True,
            "CURRENT_modified": False,
        },
        "baseline_sample_allowlist": {
            "manifest_sha256": "9" * 64,
            "allowed_game_count": 68,
            "heldout_entity_sampling": False,
        },
        "metadata": {
            "all_games_in_source_metadata": 100,
            "all_source_perspective_members": 224014,
            "identity_valid_members": 222536,
            "metadata_invalid_or_embedded_turn_mismatch": 1478,
            "ambiguous_duplicate_perspective_turn_keys": 0,
            "potential_adjacent_same_perspective_pairs": 221091,
            "games_with_adjacent_perspective_pairs": 100,
            "games_allowed_for_entity_sampling": 68,
            "games_excluded_from_entity_sampling": 32,
            "metadata_selected_game_count": 68,
            "metadata_frozen_sample_pairs": 136,
            "metadata_frozen_selection_sha256": "b" * 64,
            "selection_frozen_before_entity_reconstruction": True,
        },
        "sample": {
            "sample_status_counts": {
                "SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID": 136,
            },
            "individual_numeric_field_directions": {
                "neutronium": {
                    "qualified": 3769,
                    "increased": 3448,
                    "unchanged": 184,
                    "decreased": 137,
                },
            },
            "conditional_mineral_mass_balance_not_host_verified": {
                "model": "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL",
                "per_mineral": {
                    "duranium": {
                        "joint_stock_qualified": 3769,
                        "candidate_default_mining_qualified": 3255,
                        "both_stock_deltas_match_default_model": 2955,
                    },
                },
                "surface_up_ground_equal_surface_increase_buckets": {
                    "duranium": {"2_to_5": 2411, "1": 315},
                },
                "net_total_minus_default_mutation_abs_residual_buckets": {
                    "duranium": {"0": 3446, "1": 3},
                },
            },
        },
        "evidence_limits": {
            "raw_trn_is_submitted_turn_orders": False,
            "T_minus_1_to_T_stock_change_identifies_action": False,
            "NuHost_economic_formula_verified": False,
            "NuHost_ship_build_cost_verified": False,
            "is_independent_game_disjoint_host_validation": False,
            "may_be_used_to_plan_fresh_independent_subcohorts": True,
        },
    }


def check(tmp_path: Path, content: dict):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--input", str(path)],
        cwd=ROOT, capture_output=True, text=True, timeout=15,
    )


def test_publish_existing_accepts_valid_aggregate_without_reopening_corpus(tmp_path):
    proc = check(tmp_path, valid_aggregate())
    assert proc.returncode == 0, proc.stderr
    assert "existing_M2_aggregate_report: validated" in proc.stdout
    assert "baseline_allowed_games: 68" in proc.stdout
    assert "heldout_entity_sampling: false" in proc.stdout
    assert "NuHost" not in proc.stdout
    assert "224014" not in proc.stdout


def test_publish_existing_rejects_raw_records_and_secrets(tmp_path):
    cases = []
    with_raw = valid_aggregate()
    with_raw["raw_planets"] = [{"planet": 1, "apikey": "leak"}]
    cases.append(with_raw)
    nested_raw = valid_aggregate()
    nested_raw["sample"]["individual_numeric_field_directions"]["planet_rows"] = [
        {"id": 1, "name": "private"}
    ]
    cases.append(nested_raw)
    nested_string = valid_aggregate()
    nested_string["sample"]["sample_status_counts"]["apikey"] = "secret"
    cases.append(nested_string)
    for case in cases:
        result = check(tmp_path, case)
        assert result.returncode != 0
        assert "secret" not in result.stdout + result.stderr
        assert "private" not in result.stdout + result.stderr


def test_publish_existing_rejects_wrong_generation_or_heldout_access(tmp_path):
    cases = []
    wrong_hash = valid_aggregate()
    wrong_hash["generation"]["verified_sha256"] = "a" * 64
    cases.append(wrong_hash)
    heldout = valid_aggregate()
    heldout["baseline_sample_allowlist"]["heldout_entity_sampling"] = True
    cases.append(heldout)
    wrong_games = valid_aggregate()
    wrong_games["metadata"]["games_allowed_for_entity_sampling"] = 100
    cases.append(wrong_games)
    host_verified = valid_aggregate()
    host_verified["evidence_limits"]["NuHost_economic_formula_verified"] = True
    cases.append(host_verified)
    not_readonly = valid_aggregate()
    not_readonly["generation"]["CURRENT_modified"] = True
    cases.append(not_readonly)
    for case in cases:
        assert check(tmp_path, case).returncode != 0


def test_publication_wrapper_is_shell_valid_and_fail_closed_on_bad_paths():
    syntax = subprocess.run(
        ["bash", "-n", str(WRAPPER)],
        cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert syntax.returncode == 0, syntax.stderr
    source = WRAPPER.read_text(encoding="utf-8")
    assert "--publish-existing" in source
    assert "--include" in source
    assert "run-with-runtime-evidence.sh" in source
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in source
    assert source.index("python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py") < source.index(
        'exec bash tools/run-with-runtime-evidence.sh'
    )
    env = dict(os.environ)
    env["M2_CORPUS_COVERAGE_OUTPUT"] = "../private.har"
    denied = subprocess.run(
        ["bash", str(WRAPPER), "--publish-existing"],
        cwd=ROOT, capture_output=True, text=True, timeout=10, env=env,
    )
    assert denied.returncode == 64
    assert "unsafe" in denied.stderr or "only artifacts" in denied.stderr



def test_extended_surface_context_is_aggregate_only_for_runtime_logs(tmp_path):
    value = valid_aggregate()
    value["sample"]["surface_residual_context_not_host_verified"] = {
        "per_mineral_residual_classes": {
            "duranium": {"ground_exact_surface_residual": 2},
        },
        "per_mineral_class_covariates": {
            "duranium": {
                "ground_exact_surface_residual": {
                    "one_ship_opposite_cargo_delta_candidate": 1,
                },
            },
        },
        "per_mineral_class_residual_magnitude_buckets": {
            "duranium": {
                "ground_exact_surface_residual": {"6_to_20": 2},
            },
        },
        "source_quality_abstentions_and_limitations": {
            "OWNER_SHIP_INFOTURN_UNAVAILABLE": 1,
        },
        "game_cluster_residual_count_buckets": {
            "ground_exact_surface_residual": {"2_to_5": 1},
        },
    }
    ok = check(tmp_path, value)
    assert ok.returncode == 0, ok.stderr
    value["sample"]["surface_residual_context_not_host_verified"][
        "raw_secret_ship_list"
    ] = [{"id": 9, "apikey": "DO_NOT_SHARE"}]
    bad = check(tmp_path, value)
    assert bad.returncode != 0
    assert "DO_NOT_SHARE" not in bad.stderr + bad.stdout
