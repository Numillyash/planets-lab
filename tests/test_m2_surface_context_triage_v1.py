"""M2 full frozen baseline68 contextual triage: aggregate-only, no DuckDB."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.m2_surface_context_triage import (
    analyze_surface_context_aggregate,
    PUBLISHED_BY_MINERAL, MINERAL_CLASSES,
)

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/diagnostics/m2_surface_context_triage_v1.py"


def synthetic_aggregate():
    context_classes = {}
    context_covars = {}
    context_buckets = {}
    for mineral, counts in PUBLISHED_BY_MINERAL.items():
        context_classes[mineral] = dict(zip(MINERAL_CLASSES, counts))
        context_covars[mineral] = {}
        context_buckets[mineral] = {}
        for cls, n in zip(MINERAL_CLASSES, counts):
            opposite = 1 if cls == "ground_exact_surface_residual" else 0
            context_covars[mineral][cls] = {
                "planet_coordinates_qualified": n,
                "owner_ship_section_pair_qualified": n,
                "owner_ship_observed_at_site_both": n // 4,
                "one_ship_opposite_cargo_delta_candidate": opposite,
                "opposite_cargo_ship_both_freshness_explicit": opposite,
                "opposite_cargo_ship_freshness_unverified": 0,
                "owner_starbase_explicit_at_planet_both": n // 3,
                "planetlinked_base_both_any_owner_provenance": n // 3,
                "observed_starbase_tech_changed": n // 6,
                "structure_and_tax_controls_qualified": n,
                "structure_or_tax_controls_changed": n // 5,
            }
            # Exact surface residual zero if BOTH or surface-only exact.
            name = "0" if cls in (
                "both_exact", "surface_exact_ground_residual"
            ) else "2_to_5"
            context_buckets[mineral][cls] = {name: n}
    return {
        "schema": "planets-lab.m2-public-corpus-economy-coverage.v1",
        "generation": {
            "verified_sha256": "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c",
            "read_only": True, "CURRENT_modified": False,
        },
        "baseline_sample_allowlist": {
            "allowed_game_count": 68,
            "heldout_entity_sampling": False,
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
            "same_site_owner_ship_observation_proves_cargo_transfer": False,
            "no_owner_ship_observed_excludes_ship_actions": False,
            "starbase_at_planet_means_ship_construction_executed": False,
        },
        "sample": {
            "conditional_mineral_mass_balance_not_host_verified": {
                "model": "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL",
            },
            "surface_residual_context_not_host_verified": {
                "per_mineral_residual_classes": context_classes,
                "per_mineral_class_covariates": context_covars,
                "per_mineral_class_residual_magnitude_buckets": context_buckets,
                "game_cluster_residual_count_buckets": {
                    "both_exact": {"over_100": 68},
                    "ground_exact_surface_residual": {"6_to_20": 68},
                    "surface_exact_ground_residual": {"0": 35, "1": 33},
                    "neither_exact": {"2_to_5": 68},
                },
                "source_quality_abstentions_and_limitations": {},
                "game_cluster_surface_context_count_buckets": {
                    "owner_ship_observed_at_site_both": {"2_to_5": 68},
                    "one_ship_opposite_cargo_delta_candidate": {"1": 4, "0": 64},
                    "multiple_ship_cargo_sum_opposite_candidate_not_order": {"0": 68},
                    "ownerless_base_planetlinked_both_not_owner_proof": {"0": 68},
                    "owner_starbase_explicit_at_planet_both": {"21_to_100": 68},
                },
            },
        },
    }


def test_published_denominators_and_ship_exposure_rates_are_descriptive():
    report = analyze_surface_context_aggregate(synthetic_aggregate())
    assert report["residual_classes_all_minerals"] == {
        "both_exact": 11813,
        "ground_exact_surface_residual": 915,
        "surface_exact_ground_residual": 33,
        "neither_exact": 262,
    }
    residual = report["by_outcome"]["ground_exact_surface_residual"]
    assert residual["observations"] == 915
    assert residual["ship_arrays_and_planet_coords_qualified"] == 915
    assert residual["single_opposite_ship_cargo_delta_candidate"] == 4
    assert residual["multi_ship_cargo_sum_opposite_candidate_not_order"] == 0
    assert residual["ownerless_base_planetlinked_at_both_not_owner_proof"] == 0
    assert residual["planetlinked_base_at_both_any_owner_provenance"] > 0
    assert report["game_cluster_surface_context_count_buckets"][
        "one_ship_opposite_cargo_delta_candidate"
    ] == {"0": 64, "1": 4}
    assert residual["opposite_ship_freshness_both_explicit"] == 4
    assert residual["site_ship_at_both_percent_of_qualified"] is not None
    assert report["surface_only_residual_magnitude_buckets"] == {
        "2_to_5": 915,
    }
    assert report["evidence_limits"]["NuHost_order_execution_verified"] is False
    assert report["source"]["heldout_entity_games"] == 0
    encoded = json.dumps(report)
    assert '"game_id"' not in encoded and '"planetid"' not in encoded


@pytest.mark.parametrize("corruption", [
    "heldout", "sha", "sample", "host_causal", "denominator",
    "ship_exposure", "ship_freshness", "magnitude", "clusters",
    "ownerless_base_link", "multiship_candidate", "game_context_hist",
])
def test_invalid_evidence_fails_closed(corruption):
    v = synthetic_aggregate()
    ctx = v["sample"]["surface_residual_context_not_host_verified"]
    c = ctx["per_mineral_class_covariates"]["duranium"]["ground_exact_surface_residual"]
    if corruption == "heldout":
        v["baseline_sample_allowlist"]["heldout_entity_sampling"] = True
    elif corruption == "sha":
        v["generation"]["verified_sha256"] = "0" * 64
    elif corruption == "sample":
        v["metadata"]["metadata_frozen_selection_sha256"] = "0" * 64
    elif corruption == "host_causal":
        v["evidence_limits"]["same_site_owner_ship_observation_proves_cargo_transfer"] = True
    elif corruption == "denominator":
        ctx["per_mineral_residual_classes"]["duranium"]["ground_exact_surface_residual"] += 1
    elif corruption == "ship_exposure":
        c["owner_ship_observed_at_site_both"] = 9999
    elif corruption == "ship_freshness":
        c["opposite_cargo_ship_both_freshness_explicit"] = 99
    elif corruption == "magnitude":
        ctx["per_mineral_class_residual_magnitude_buckets"]["duranium"][
            "ground_exact_surface_residual"
        ] = {"21_to_100": 1}
    elif corruption == "clusters":
        ctx["game_cluster_residual_count_buckets"]["both_exact"] = {"0": 67}
    elif corruption == "ownerless_base_link":
        c["ownerless_base_planetlinked_both_not_owner_proof"] = 9999
    elif corruption == "multiship_candidate":
        c["multiple_ship_cargo_sum_opposite_candidate_not_order"] = 99
    elif corruption == "game_context_hist":
        ctx["game_cluster_surface_context_count_buckets"][
            "one_ship_opposite_cargo_delta_candidate"
        ] = {"0": 67}
    with pytest.raises(ValueError):
        analyze_surface_context_aggregate(v)


def test_cli_offline_generates_separate_report_no_overwrite(tmp_path):
    input_path, out_path = tmp_path / "report.json", tmp_path / "triage.json"
    input_path.write_text(json.dumps(synthetic_aggregate()), encoding="utf-8")
    cmd = [
        sys.executable, str(CLI), "--input", str(input_path),
        "--output", str(out_path),
    ]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "aggregate_summary_written: true" in p.stdout
    assert "915" in p.stdout
    assert "NuHost_order_execution_verified: false" in p.stdout
    assert "777001" not in p.stdout
    assert json.loads(out_path.read_text())["by_outcome"][
        "ground_exact_surface_residual"
    ]["observations"] == 915
    repeat = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert repeat.returncode != 0
    assert json.loads(out_path.read_text())["schema"] == (
        "planets-lab.m2-surface-context-aggregate-triage.v1"
    )


def test_wrapper_integrates_one_read_only_corpus_run_and_both_evidence_outputs():
    inner = ROOT / "tools/run-m2-public100-surface-context-v1.sh"
    outer = ROOT / "tools/run-m2-public100-surface-context-v1-with-evidence.sh"
    for path in (inner, outer):
        check = subprocess.run(
            ["bash", "-n", str(path)], cwd=ROOT, capture_output=True,
            text=True, timeout=10,
        )
        assert check.returncode == 0, check.stderr
    inner_text = inner.read_text()
    assert inner_text.count("bash tools/run-m2-public100-economy-coverage-v1.sh") == 1
    assert "m2_validate_corpus_aggregate_evidence_v1.py" in inner_text
    assert "m2_surface_context_triage_v1.py" in inner_text
    assert inner_text.index("bash tools/run-m2-public100-economy-coverage-v1.sh") < (
        inner_text.index("m2_surface_context_triage_v1.py")
    )
    outer_text = outer.read_text()
    assert outer_text.count('--include "$OUT"') == 1
    assert outer_text.count('--include "$SUMMARY"') == 1
    assert "run-with-runtime-evidence.sh" in outer_text
    assert "m2-public100-surface-context-v1" in outer_text


def test_wrapper_rejects_insecure_output_without_spawning_docker():
    outer = ROOT / "tools/run-m2-public100-surface-context-v1-with-evidence.sh"
    env = dict(os.environ)
    env["M2_CORPUS_COVERAGE_OUTPUT"] = "../user-private.json"
    p = subprocess.run(["bash", str(outer)], cwd=ROOT,
                       capture_output=True, text=True, timeout=10, env=env)
    assert p.returncode == 64
    assert "aggregate" in p.stderr



def test_offline_cli_standalone_no_site_packages_no_duckdb(tmp_path):
    """Reproduces server failure: Python has no installed DuckDB.

    Python -I -S forbids site-packages entirely and ignores PYTHONPATH,
    so the CLI must not import planets_lab.corpus/__init__.py.
    """
    infile, outfile = tmp_path / "source.json", tmp_path / "recovery.json"
    infile.write_text(json.dumps(synthetic_aggregate()), encoding="utf-8")
    p = subprocess.run([
        sys.executable, "-I", "-S", str(CLI),
        "--input", str(infile), "--output", str(outfile),
    ], cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert json.loads(outfile.read_text())["by_outcome"][
        "ground_exact_surface_residual"
    ]["observations"] == 915


def test_recovery_mode_never_reruns_corpus_and_refuses_missing_report(tmp_path):
    inner = ROOT / "tools/run-m2-public100-surface-context-v1.sh"
    outer = ROOT / "tools/run-m2-public100-surface-context-v1-with-evidence.sh"
    inner_text, outer_text = inner.read_text(), outer.read_text()
    assert "MODE=" in inner_text and "--complete-existing" in inner_text
    assert "MODE=" in outer_text and "--complete-existing" in outer_text
    assert 'INNER_ARGS=(--complete-existing)' in outer_text
    assert 'm2-public100-surface-context-recovered-v1' in outer_text
    assert 'bash tools/run-m2-public100-economy-coverage-v1.sh' in inner_text
    assert inner_text.index('bash tools/run-m2-public100-economy-coverage-v1.sh') > (
        inner_text.index('elif [[ $# -eq 0 ]]')
    )
    assert outer_text.index(
        'm2_validate_corpus_aggregate_evidence_v1.py'
    ) < outer_text.index('exec bash tools/run-with-runtime-evidence.sh')
    assert outer_text.count('--include "$OUT"') == 1
    assert outer_text.count('--include "$SUMMARY"') == 1

    env = dict(os.environ)
    # Under approved shape, but no file exists. Must abort before
    # trying to publish evidence, import DuckDB, or launch Docker.
    env["M2_CORPUS_COVERAGE_OUTPUT"] = (
        "artifacts/planetary/m2-public100-no-existing-report-"
        + tmp_path.name + "/report.json"
    )
    process = subprocess.run(
        ["bash", str(outer), "--complete-existing"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=10,
    )
    assert process.returncode == 73
    assert "existing report required" in process.stderr
    assert "runtime_evidence: published" not in process.stdout



def test_surface_evidence_wrapper_auto_recovers_existing_report_without_flag(
    tmp_path,
):
    """The exact user incident: copied bare runner command after corpus success.

    Intercept bash AFTER actual outer wrapper validation, so no Git push,
    Docker, database read or corpus SHA256 can occur in this test.
    """
    import shutil
    import uuid

    outer = ROOT / "tools/run-m2-public100-surface-context-v1-with-evidence.sh"
    relative_dir = (
        "artifacts/planetary/"
        f"m2-public100-auto-recovery-test-{uuid.uuid4().hex}"
    )
    folder = ROOT / relative_dir
    folder.mkdir(parents=True)
    report_file = folder / "report.json"

    # Construct a complete, known aggregate-only public100 V1 shape, so
    # the REAL privacy/provenance validator runs before the mocked publisher.
    value = synthetic_aggregate()
    value["status"] = (
        "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL"
    )
    value["generation"]["name"] = (
        "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
    )
    value["baseline_sample_allowlist"]["manifest_sha256"] = "9" * 64
    value["metadata"] = {
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
        "metadata_frozen_selection_sha256":
            "b6a09b95e2a8a6d261cb5d4180be45eb601711df9865cf0b44457ad17b84068f",
        "selection_frozen_before_entity_reconstruction": True,
    }
    value["evidence_limits"].update({
        "T_minus_1_to_T_stock_change_identifies_action": False,
        "NuHost_ship_build_cost_verified": False,
    })
    value["sample"]["conditional_mineral_mass_balance_not_host_verified"].update({
        "per_mineral": {},
        "surface_up_ground_equal_surface_increase_buckets": {},
        "net_total_minus_default_mutation_abs_residual_buckets": {},
    })

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    bash_call = tmp_path / "bash_invocation.txt"
    fake_bash = fake_bin / "bash"
    fake_bash.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$M2_TEST_FAKE_BASH_LOG"\n',
        encoding="utf-8",
    )
    fake_bash.chmod(0o755)
    env = dict(os.environ)
    env["M2_CORPUS_COVERAGE_OUTPUT"] = str(report_file.relative_to(ROOT))
    env["M2_TEST_FAKE_BASH_LOG"] = str(bash_call)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    try:
        # A fresh report path with no existing report means normal mode.
        fresh = subprocess.run(
            ["/bin/bash", str(outer)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
        )
        assert fresh.returncode == 0, fresh.stdout + fresh.stderr
        assert "m2-public100-surface-context-v1" in bash_call.read_text()
        assert "m2-public100-surface-context-recovered-v1" not in bash_call.read_text()

        report_file.write_text(json.dumps(value), encoding="utf-8")
        bash_call.unlink()
        # Crucial: user forgot --complete-existing; never rerun the DB.
        recovered = subprocess.run(
            ["/bin/bash", str(outer)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
        )
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
        assert "M2 recovery auto-detected" in recovered.stdout
        invocation = bash_call.read_text()
        assert "m2-public100-surface-context-recovered-v1" in invocation
        assert "--complete-existing" in invocation
        assert not (folder / "triage.json").exists()
        assert json.loads(report_file.read_text()) == value

        # A completed triage is never overwritten, even without a flag.
        (folder / "triage.json").write_text("protected", encoding="utf-8")
        bash_call.unlink()
        refused = subprocess.run(
            ["/bin/bash", str(outer)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
        )
        assert refused.returncode == 73
        assert "refusing overwrite" in refused.stderr
        assert not bash_call.exists()
        assert (folder / "triage.json").read_text() == "protected"
    finally:
        shutil.rmtree(folder)



def add_v3_joint_data(report):
    ctx = report["sample"]["surface_residual_context_not_host_verified"]
    ctx["per_mineral_surface_residual_joint_cargo_base"] = {}
    for mineral, source in PUBLISHED_BY_MINERAL.items():
        n = source[1]
        ctx["per_mineral_surface_residual_joint_cargo_base"][mineral] = {
            "qualified_surface_residual": n,
            "single_only_cargo_candidate": 1,
            "no_exact_cargo_candidate": n - 1,
            "any_exact_opposite_cargo_candidate": 1,
            "cargo_candidate_positive_surface_residual": 1,
            "ownerless_planetlinked_tech_changed": 0,
            "base_tech_change_and_cargo_candidate": 0,
            "base_tech_change_no_cargo_candidate": 0,
        }
    ctx["planet_transition_residual_events_not_independent_actions"] = {
        "planet_windows_any_surface_residual": 315,
        "residual_mineral_multiplicity_1": 115,
        "residual_mineral_multiplicity_4": 200,
        "planet_windows_any_single_cargo": 4,
        "planet_windows_any_cargo_candidate": 4,
    }
    ctx["game_cluster_planet_residual_events_count_buckets"] = {
        "planet_windows_any_surface_residual": {"2_to_5": 68},
        "planet_windows_any_single_cargo": {"0": 64, "1": 4},
        "planet_windows_any_multiship_cargo": {"0": 68},
        "planet_windows_any_cargo_candidate": {"0": 64, "1": 4},
        "planet_windows_any_planetlinked_base": {"0": 68},
        "planet_windows_any_base_tech_change": {"0": 68},
        "planet_windows_base_tech_and_cargo_candidate": {"0": 68},
    }
    return report


def test_v3_disjoint_cargo_and_planet_window_multiplicity_summary():
    report = analyze_surface_context_aggregate(
        add_v3_joint_data(synthetic_aggregate())
    )
    j = report["disjoint_surface_residual_cargo_and_base_v3_not_host_orders"]
    assert j == {
        "observations": 915,
        "single_ship_only": 4,
        "multiship_only": 0,
        "both_ship_methods_overlap": 0,
        "no_exact_cargo_candidate": 911,
        "union_distinct_mineral_observations": 4,
        "ownerless_base_tech_change": 0,
        "base_tech_and_cargo_candidate": 0,
        "base_tech_without_cargo_candidate": 0,
    }
    windows = report["deduplicated_planet_transition_events_not_host_actions"]
    assert windows["planet_windows_any_surface_residual"] == 315
    assert windows["residual_mineral_multiplicity_4"] == 200
    assert report["game_cluster_planet_transition_event_buckets"][
        "planet_windows_any_cargo_candidate"
    ] == {"0": 64, "1": 4}
    assert report["evidence_limits"]["NuHost_order_execution_verified"] is False


@pytest.mark.parametrize("invalid", [
    "overlap", "missing_mineral", "tech", "incomplete", "planet_weighted",
    "game_zero_count", "candidate_sign", "marginal",
])
def test_v3_joint_fail_closed_on_inconsistent_archive_aggregates(invalid):
    value = add_v3_joint_data(synthetic_aggregate())
    ctx = value["sample"]["surface_residual_context_not_host_verified"]
    j = ctx["per_mineral_surface_residual_joint_cargo_base"]["duranium"]
    if invalid == "overlap":
        j["both_single_and_multiship_candidate"] = 1
    elif invalid == "missing_mineral":
        del ctx["per_mineral_surface_residual_joint_cargo_base"]["duranium"]
    elif invalid == "tech":
        j["ownerless_planetlinked_tech_changed"] = 4
    elif invalid == "incomplete":
        del ctx["game_cluster_planet_residual_events_count_buckets"]
    elif invalid == "planet_weighted":
        ctx["planet_transition_residual_events_not_independent_actions"][
            "residual_mineral_multiplicity_4"
        ] = 199
    elif invalid == "game_zero_count":
        ctx["game_cluster_planet_residual_events_count_buckets"][
            "planet_windows_any_cargo_candidate"
        ] = {"0": 67}
    elif invalid == "candidate_sign":
        j["cargo_candidate_positive_surface_residual"] = 0
    elif invalid == "marginal":
        j["single_only_cargo_candidate"] = 0
    with pytest.raises(ValueError):
        analyze_surface_context_aggregate(value)
