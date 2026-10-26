"""Strict offline replay of the successful same-turn multi-observer VCR source.

The source reports selected archive observations, NOT independent Host battle
executions, accepted orders, battle outcome oracle, or representative sampling.
No DuckDB, runtime host, member identifiers, VCR keys or signatures are exported.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_V6 = _ROOT / "src/planets_lab/corpus/minefield_v6_observation_readout.py"
_spec = spec_from_file_location("_same_turn_preexisting_frozen_v6_gate", _V6)
if _spec is None or _spec.loader is None:
    raise RuntimeError("ABSTAIN_PRIOR_FROZEN_V6_VALIDATOR_MISSING")
_previous = module_from_spec(_spec)
_spec.loader.exec_module(_previous)
EvidenceReviewAbstain = _previous.EvidenceReviewAbstain
readout_v6_joint = _previous.readout_v6_joint

SCHEMA = "planets-lab.vcr-same-turn-v1-observation-readout.v1"
PROJECTION_SCHEMA = "planets-lab.vcr-same-turn-v1-safe-projection.v1"
SECTION = "vcr_same_turn_perspective_consensus_not_host_phase"
RUN = "20261026T202552Z_96f6f595a25c"
SOURCE = "96f6f595a25c3ef3e47fa01a2ef2b3386e5f7b7e"
RUNTIME = {
    "run_id": RUN,
    "source_commit": SOURCE,
    "source_branch": "main",
    "exit_code": 0,
    "started_at_utc": "2026-10-26T20:25:52Z",
    "finished_at_utc": "2026-10-26T21:00:19Z",
    "build_status": "PASS",
    "preflight": "PASS_PINNED_PUBLIC100_BASELINE68",
    "cohort_status": "PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68",
    "pytest_status": "PASS",
    "pytest_cases": 3884,
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
FIELDS = (
    "qualified_original_frozen_adjacent_pairs",
    "unique_frozen_archive_members_examined",
    "qualified_member_vcr_lists",
    "ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED",
    "ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE",
    "vcr_rows_in_unique_member_archives",
    "vcr_rows_unqualified_atomic_member_abstain",
    "vcr_rows_unqualified_turn_or_participant",
    "vcr_rows_unqualified_unserializable_input",
    "vcr_rows_qualified_same_turn_typed_participants",
    "vcr_rows_missing_typed_weapon_catalog",
    "vcr_rows_missing_explicit_combat_rng",
    "vcr_rows_missing_typed_owner_pair",
    "source_observation_rows_in_qualified_groups",
    "same_turn_observation_groups",
    "single_perspective_groups",
    "multi_perspective_groups",
    "multi_perspective_observer_occurrences",
    "multi_perspective_groups_two_observers",
    "multi_perspective_groups_three_or_more_observers",
    "multi_perspective_vcr_payload_equal",
    "multi_perspective_vcr_payload_different",
    "multi_perspective_weapon_catalog_equal",
    "multi_perspective_weapon_catalog_different",
    "multi_perspective_combat_rng_settings_equal",
    "multi_perspective_combat_rng_settings_different",
    "multi_perspective_complete_adapter_signature_equal",
    "multi_perspective_complete_adapter_signature_different",
    "multi_perspective_strict_inputs_incomplete",
    "multi_perspective_strict_complete_inputs_equal",
    "multi_perspective_strict_complete_inputs_different",
)


def _fail(reason: str) -> None:
    raise EvidenceReviewAbstain(reason)


def readout_vcr_same_turn(
    original_v5: dict[str, Any],
    frozen_v6: dict[str, Any],
    same_turn: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed on any old-source drift, unknown count or causal gate."""
    if any(type(x) is not dict for x in (original_v5, frozen_v6, same_turn)):
        _fail("ABSTAIN_SOURCE_INPUT_TYPE")
    prior = readout_v6_joint(original_v5, frozen_v6)
    if (set(same_turn) != {"schema", "runtime", "source"}
            or same_turn.get("schema") != PROJECTION_SCHEMA
            or same_turn.get("runtime") != RUNTIME):
        _fail("ABSTAIN_SAME_TURN_RUNTIME_ATTESTATION")
    source = same_turn.get("source")
    old_source = frozen_v6.get("source")
    if type(source) is not dict or type(old_source) is not dict:
        _fail("ABSTAIN_FROZEN_SOURCE_TYPE")
    projected = deepcopy(source)
    try:
        sample = projected["sample"]
        counters = sample.pop(SECTION)
        status = sample["sample_status_counts"]
        old = sample["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"]
    except (KeyError, TypeError, AttributeError):
        _fail("ABSTAIN_SAME_TURN_SOURCE_SECTION_MISSING")
    # Compare ALL old published v6 source fields, not just VCR row counts:
    # generation, manifest, selection, all mineral/mine/ship/base/ion data,
    # plus all explicit limits must be exactly equal.
    if projected != old_source:
        _fail("ABSTAIN_V6_FROZEN_SOURCE_PARITY")
    if (type(counters) is not dict or set(counters) != set(FIELDS)
            or any(type(v) is not int or v < 0 or v > 10**12
                   for v in counters.values())):
        _fail("ABSTAIN_FIXED_SANITIZED_COUNT_ALLOWLIST")
    c = counters
    q = c["qualified_original_frozen_adjacent_pairs"]
    members = c["unique_frozen_archive_members_examined"]
    observed = c["vcr_rows_in_unique_member_archives"]
    qual = c["vcr_rows_qualified_same_turn_typed_participants"]
    groups = c["same_turn_observation_groups"]
    singles = c["single_perspective_groups"]
    multi = c["multi_perspective_groups"]
    occurrences = c["multi_perspective_observer_occurrences"]
    complete = c["multi_perspective_strict_complete_inputs_equal"]
    incomplete = c["multi_perspective_strict_inputs_incomplete"]
    conflict = c["multi_perspective_strict_complete_inputs_different"]
    if not (
        prior["provenance"]["observational_pairs"] == q == 8550
        and q == old["qualified_identity_list_pair"]
        and status["SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID"] == q
        and members == 17100 == 2 * q
        and members == (c["qualified_member_vcr_lists"]
                         + c["ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED"]
                         + c["ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE"])
        and observed == qual + sum(c[k] for k in (
            "vcr_rows_unqualified_atomic_member_abstain",
            "vcr_rows_unqualified_turn_or_participant",
            "vcr_rows_unqualified_unserializable_input"))
        and observed == old["before_id_rows"] + old["after_id_rows"] == 44332
        and observed == qual == c["source_observation_rows_in_qualified_groups"]
        and groups == singles + multi
        and occurrences + singles == qual
        and 2 * multi <= occurrences
        and multi == (c["multi_perspective_groups_two_observers"]
                      + c["multi_perspective_groups_three_or_more_observers"])
        and multi == complete + conflict + incomplete
        and all(multi == c["multi_perspective_" + family + "_equal"]
                + c["multi_perspective_" + family + "_different"]
                for family in ("vcr_payload", "weapon_catalog",
                               "combat_rng_settings", "complete_adapter_signature"))
        and all(c[k] <= qual for k in (
            "vcr_rows_missing_typed_weapon_catalog",
            "vcr_rows_missing_explicit_combat_rng",
            "vcr_rows_missing_typed_owner_pair"))
        and old["same_id_seen_in_both_archives"] == 0
        and prior["inference_gates"]["host_diff_verified_by_this_readout"] is False
    ):
        _fail("ABSTAIN_SAME_TURN_PARTITION_OR_FROZEN_MARGINALS")
    # Observed full signatures can agree despite missing mandatory fields.
    # A strict match is only the subset that has fully typed provenance.
    if not (complete <= c["multi_perspective_complete_adapter_signature_equal"]
            and conflict <= c["multi_perspective_complete_adapter_signature_different"]
            and incomplete <= multi):
        _fail("ABSTAIN_STRICT_COMPLETENESS_MONOTONICITY")
    return {
        "schema": SCHEMA,
        "status": "PASS_SAME_TURN_VCR_SOURCE_CONSENSUS_NOT_HOST_CAUSAL",
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_ONLY",
        "provenance": {
            "run_id": RUN,
            "source_commit": SOURCE,
            "frozen_selection_sha256": prior["provenance"]["frozen_selection_sha256"],
            "metadata_games": 100,
            "baseline_entity_games": 68,
            "sealed_entity_games_read": 0,
            "frozen_adjacent_archive_pairs": q,
            "entire_previous_v6_source_matched": True,
            "real_runtime_status_validated": True,
        },
        "selected_same_turn_source_groups_not_host_battles": {
            "distinct_archive_members": members,
            "source_vcr_observation_rows": observed,
            "qualified_same_turn_typed_participant_rows": qual,
            "same_turn_group_count": groups,
            "single_observer_groups": singles,
            "two_observer_groups": c["multi_perspective_groups_two_observers"],
            "three_or_more_observer_groups": c["multi_perspective_groups_three_or_more_observers"],
            "multi_observer_groups": multi,
            "multi_observer_source_occurrences": occurrences,
            "raw_vcr_payload_equal": c["multi_perspective_vcr_payload_equal"],
            "raw_vcr_payload_different": c["multi_perspective_vcr_payload_different"],
            "weapon_catalog_equal": c["multi_perspective_weapon_catalog_equal"],
            "weapon_catalog_different": c["multi_perspective_weapon_catalog_different"],
            "rng_settings_equal": c["multi_perspective_combat_rng_settings_equal"],
            "rng_settings_different": c["multi_perspective_combat_rng_settings_different"],
            "full_adapter_signature_equal_even_if_incomplete":
                c["multi_perspective_complete_adapter_signature_equal"],
            "full_adapter_signature_different": c["multi_perspective_complete_adapter_signature_different"],
            "strict_complete_equal": complete,
            "strict_complete_different": conflict,
            "strict_inputs_incomplete": incomplete,
            "source_rows_missing_explicit_rng": c["vcr_rows_missing_explicit_combat_rng"],
            "source_rows_missing_owner_pair": c["vcr_rows_missing_typed_owner_pair"],
            "source_rows_missing_typed_weapon_catalog": c["vcr_rows_missing_typed_weapon_catalog"],
            "all_counter_conservation_verified": True,
        },
        "inference_gates": {
            "same_turn_multi_perspective_source_consensus_observed": True,
            "all_source_games_or_battles_examined": False,
            "random_independent_sample": False,
            "accepted_host_orders_authenticated": False,
            "host_combat_result_differential_verified": False,
            "host_phase_receipt_authenticated": False,
            "new_host_execution_witnessed": False,
            "vcr_id_cross_turn_stable_battle_key": False,
            "missing_rng_means_replay_ready": False,
            "same_turn_agreement_proves_game_mechanics": False,
        },
    }
