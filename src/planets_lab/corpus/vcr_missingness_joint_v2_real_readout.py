"""Offline fail-closed replay of genuine 2026-10-27 VCR missingness joint.

Only safe count-only projections of previously published runtime evidence.
No source DB access, unique Host battles, orders, RNG imputation or C5 logic.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]


def _module(name: str, path: Path) -> Any:
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("ABSTAIN_PREVIOUS_FROZEN_VALIDATOR_MISSING")
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


_v1 = _module("_real_frozen_vcr_v1_for_v2_readout",
              _ROOT / "src/planets_lab/corpus/vcr_same_turn_v1_observation_readout.py")
_joint = _module("_real_frozen_vcr_joint_v2_validator",
                 _ROOT / "tools/diagnostics/validate_vcr_same_turn_missingness_joint_v2.py")
EvidenceReviewAbstain = _v1.EvidenceReviewAbstain
SCHEMA = "planets-lab.vcr-missingness-joint-v2-real-observation-readout.v1"
PROJECTION_SCHEMA = "planets-lab.vcr-missingness-joint-v2-real-safe-projection.v1"
SECTION = "vcr_same_turn_missingness_joint_not_host_phase"
V1_SECTION = "vcr_same_turn_perspective_consensus_not_host_phase"
RUN_ID = "20261027T022626Z_5836580b8252"
SOURCE_SHA = "5836580b82529150c92b5f323758d91f47206b0c"
RUNTIME = {
    "run_id": RUN_ID,
    "source_commit": SOURCE_SHA,
    "source_branch": "main",
    "started_at_utc": "2026-10-27T02:26:26Z",
    "finished_at_utc": "2026-10-27T03:02:45Z",
    "exit_code": 0,
    "source_dirty": False,
    "build_status": "PASS",
    "preflight": "PASS_PINNED_PUBLIC100_BASELINE68",
    "cohort_status": "PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68",
    "pytest_status": "PASS",
    "pytest_cases": 3920,
    "pytest_failures": 0,
    "pytest_errors": 0,
    "pytest_skipped": 26,
    "economy_status": "PASS_VALIDATED_AGGREGATE",
    "generation_read_only": True,
    "heldout32_entities_read": False,
    "current_modified": False,
    "host_orders_verified": False,
    "host_diff_verified": False,
}


def _abstain(reason: str) -> None:
    raise EvidenceReviewAbstain(reason)


def readout_real_vcr_missingness(
    v5: dict[str, Any],
    v6: dict[str, Any],
    previous_same_turn: dict[str, Any],
    missingness: dict[str, Any],
) -> dict[str, Any]:
    """Replay the entire prior common V1 projection and 32 exclusive counters."""
    if any(type(x) is not dict for x in (v5, v6, previous_same_turn, missingness)):
        _abstain("ABSTAIN_INPUT_TYPE")
    old_score = _v1.readout_vcr_same_turn(v5, v6, previous_same_turn)
    if (set(missingness) != {"schema", "runtime", "source"}
            or missingness.get("schema") != PROJECTION_SCHEMA
            or missingness.get("runtime") != RUNTIME):
        _abstain("ABSTAIN_JOINT_REAL_RUNTIME_ATTESTATION")
    raw = missingness.get("source")
    previous = previous_same_turn.get("source")
    if type(raw) is not dict or type(previous) is not dict:
        _abstain("ABSTAIN_JOINT_SOURCE_TYPE")
    projected = deepcopy(raw)
    try:
        joint = projected["sample"].pop(SECTION)
        v1 = projected["sample"][V1_SECTION]
    except (KeyError, TypeError, AttributeError):
        _abstain("ABSTAIN_JOINT_MISSING_SOURCE")
    if projected != previous:
        _abstain("ABSTAIN_JOINT_PREVIOUS_FROZEN_SOURCE_DRIFT")
    if type(joint) is not dict or set(joint) != set(_joint.FIELDS):
        _abstain("ABSTAIN_JOINT_ONLY_FIXED_SCHEMA")
    try:
        _joint.validate_joint(joint, v1)
    except (ValueError, KeyError, TypeError):
        _abstain("ABSTAIN_JOINT_SOURCE_CONSERVATION")
    if not (
        old_score["selected_same_turn_source_groups_not_host_battles"]["multi_observer_groups"] == 6106
        and old_score["selected_same_turn_source_groups_not_host_battles"]["strict_inputs_incomplete"] == 59
        and old_score["provenance"]["frozen_adjacent_archive_pairs"] == 8550
        and old_score["inference_gates"]["host_combat_result_differential_verified"] is False
        and joint["multi_rng_only_groups"] == 59
        and joint["multi_missing_rng_rows"] == 118
        and joint["single_rng_only_groups"] == 205
        and joint["single_missing_rng_rows"] == 205
        and joint["single_owner_only_groups"] == 1
        and joint["single_missing_owner_rows"] == 1
        and joint["multi_missing_owner_rows"] == 0
        and joint["multi_complete_groups"] == 6047
        and joint["single_complete_groups"] == 31914
        and joint["multi_incomplete_signature_equal"] == 59
        and joint["multi_incomplete_signature_different"] == 0
        and all(joint[k] == 0 for k in (
            "multi_owner_only_groups", "multi_catalog_only_groups",
            "multi_rng_owner_groups", "multi_rng_catalog_groups",
            "multi_owner_catalog_groups", "multi_rng_owner_catalog_groups",
            "single_catalog_only_groups", "single_rng_owner_groups",
            "single_rng_catalog_groups", "single_owner_catalog_groups",
            "single_rng_owner_catalog_groups",
            "multi_missing_catalog_rows", "single_missing_catalog_rows"))
    ):
        _abstain("ABSTAIN_REAL_JOINT_EXACT_OBSERVED_COUNTS")
    return {
        "schema": SCHEMA,
        "status": "PASS_REAL_FROZEN_VCR_MISSINGNESS_JOINT_NONCAUSAL",
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_ONLY",
        "provenance": {
            "run_id": RUN_ID,
            "source_commit": SOURCE_SHA,
            "metadata_games": 100,
            "baseline_entity_games": 68,
            "sealed_entity_games_read": 0,
            "frozen_archive_pairs": 8550,
            "frozen_selection_sha256": old_score["provenance"]["frozen_selection_sha256"],
            "entire_prior_v1_safe_projection_identical": True,
            "prior_v5_v6_gates_passed": True,
            "run_test_and_read_only_attestation_verified": True,
        },
        "selected_archive_group_and_row_missingness_not_host_battles": {
            "total_source_rows": 44332,
            "same_turn_groups": 38226,
            "singleton_groups": 32120,
            "multi_observer_groups": 6106,
            "singleton_complete_groups": 31914,
            "singleton_rng_only_groups": 205,
            "singleton_owner_only_groups": 1,
            "multi_complete_groups": 6047,
            "multi_rng_only_groups": 59,
            "multi_rng_missing_archive_rows": 118,
            "singleton_rng_missing_archive_rows": 205,
            "all_rng_missing_archive_rows": 323,
            "singleton_owner_pair_untyped_archive_rows": 1,
            "multi_owner_pair_untyped_archive_rows": 0,
            "catalog_missing_archive_rows": 0,
            "all_overlapping_source_group_missingness_categories_zero": True,
            "multi_incomplete_signature_equal": 59,
            "multi_incomplete_signature_different": 0,
            "complete_multi_signature_equal": 6047,
            "all_count_conservation_verified": True,
        },
        "inference_gates": {
            "selected_source_missingness_intersection_known": True,
            "rng_absence_default_known": False,
            "rng_absence_means_zero": False,
            "rng_values_semantically_validated": False,
            "missing_rng_imputed": False,
            "incomplete_multi_groups_promoted_to_replay_ready": False,
            "unique_independent_host_battles_counted": False,
            "all_baseline_games_battles_exhaustively_sampled": False,
            "accepted_host_orders_authenticated": False,
            "host_phase_receipts_authenticated": False,
            "host_combat_results_diff_verified": False,
            "changes_to_runtime_battle_logic": False,
        },
    }
