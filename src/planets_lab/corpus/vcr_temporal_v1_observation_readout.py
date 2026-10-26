"""Replay the real frozen baseline68 VCR temporal aggregate, strictly offline.

Repeated T-1/T observer-archive VCR rows are not unique battles, accepted
Host actions or phase-verified combat. No raw IDs, corpus access or DuckDB.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_MODULE = ROOT / "src/planets_lab/corpus/starbase_link_v1_observation_readout.py"
_spec = spec_from_file_location("_pure_starbase_replay_for_vcr_v1", PREVIOUS_MODULE)
if _spec is None or _spec.loader is None:
    raise RuntimeError("ABSTAIN_STARBASE_REVIEW_MODULE_UNAVAILABLE")
_previous = module_from_spec(_spec)
_spec.loader.exec_module(_previous)
EvidenceReviewAbstain = _previous.EvidenceReviewAbstain
readout_starbase_link = _previous.readout_starbase_link

SCHEMA = "planets-lab.vcr-temporal-v1-source-scorecard.v1"
PROJECTION_SCHEMA = "planets-lab.vcr-temporal-v1-safe-projection.v1"
RUN_ID = "20261026T173212Z_67a21319e287"
SOURCE_COMMIT = "67a21319e2876280480dcb6d9fb149127b033cfb"
FIELDS = (
    "qualified_archive_pairs",
    "before_vcr_rows", "after_vcr_rows",
    "before_turn_exact", "before_turn_earlier", "before_turn_future",
    "before_turn_missing_or_invalid",
    "after_turn_exact", "after_turn_earlier", "after_turn_future",
    "after_turn_missing_or_invalid",
    "before_two_participant_objectids_typed", "after_two_participant_objectids_typed",
    "before_two_ownerids_typed", "after_two_ownerids_typed",
    "before_exact_turn_and_typed_participants", "after_exact_turn_and_typed_participants",
    "before_exact_turn_and_full_typed_participants_owners",
    "after_exact_turn_and_full_typed_participants_owners",
    "same_id_across_adjacent_archives_not_battle_link",
)
RUNTIME = {
    "source_commit": SOURCE_COMMIT,
    "source_branch": "main",
    "run_id": RUN_ID,
    "exit_code": 0,
    "economy_status": "PASS_VALIDATED_AGGREGATE",
    "cohort_status": "PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68",
    "pytest_status": "PASS",
    "pytest_cases": 3845,
    "pytest_failures": 0,
    "pytest_errors": 0,
    "pytest_skipped": 26,
    "generation_read_only": True,
    "heldout32_entities_read": False,
    "current_modified": False,
    "host_orders_verified": False,
    "host_diff_verified": False,
}

def _abstain(reason: str) -> None:
    raise EvidenceReviewAbstain(reason)


def readout_vcr_temporal(
    v5: dict[str, Any],
    v6: dict[str, Any],
    starbase: dict[str, Any],
    vcr: dict[str, Any],
) -> dict[str, Any]:
    """Accept precisely one VCR count-only extension of the earlier frozen source."""
    if any(type(arg) is not dict for arg in (v5, v6, starbase, vcr)):
        _abstain("ABSTAIN_INPUT_TYPE")
    prior = readout_starbase_link(v5, v6, starbase)
    if (set(vcr) != {"schema", "runtime", "source"}
        or vcr.get("schema") != PROJECTION_SCHEMA
        or vcr.get("runtime") != RUNTIME):
        _abstain("ABSTAIN_VCR_REAL_RUNTIME_ATTESTATION")
    if type(vcr.get("source")) is not dict:
        _abstain("ABSTAIN_VCR_SOURCE_NOT_DICT")
    old_source = starbase.get("source")
    if type(old_source) is not dict:
        _abstain("ABSTAIN_PRIOR_SOURCE_NOT_DICT")
    copied = deepcopy(vcr["source"])
    try:
        sample = copied["sample"]
        new = sample.pop("vcr_archive_temporal_input_readiness_not_host_phase")
        old_vcr = sample["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"]
    except (KeyError, TypeError, AttributeError):
        _abstain("ABSTAIN_VCR_SECTION_NOT_PRESENT")
    # All old source fields, including frozen selection, source SHA, status,
    # prior mine and base counts, ownership caveats and causal flags, must
    # replay IDENTICALLY, not just selected aggregates.
    if copied != old_source:
        _abstain("ABSTAIN_VCR_PRIOR_FROZEN_SOURCE_CHANGED")
    if type(new) is not dict or set(new) != set(FIELDS):
        _abstain("ABSTAIN_VCR_FIXED_COUNTER_ALLOWLIST")
    if any(type(value) is not int or value < 0 or value > 10**12
           for value in new.values()):
        _abstain("ABSTAIN_VCR_COUNTER_NOT_STRICT_POSITIVE_OR_ZERO_INT")
    q = new["qualified_archive_pairs"]
    before = new["before_vcr_rows"]
    after = new["after_vcr_rows"]
    continuity = new["same_id_across_adjacent_archives_not_battle_link"]
    if not (
        q == prior["provenance"]["observational_pairs"] == 8550
        and q == old_vcr["qualified_identity_list_pair"]
        and before == old_vcr["before_id_rows"] == 21918
        and after == old_vcr["after_id_rows"] == 22414
        and continuity == old_vcr["same_id_seen_in_both_archives"] == 0
        and prior["inference_gates"]["host_diff_verified_by_this_readout"] is False
    ):
        _abstain("ABSTAIN_VCR_FROZEN_IDENTITY_MARGINALS")
    for name, total in (("before", before), ("after", after)):
        exact = new[f"{name}_turn_exact"]
        parts = new[f"{name}_two_participant_objectids_typed"]
        owners = new[f"{name}_two_ownerids_typed"]
        joint = new[f"{name}_exact_turn_and_typed_participants"]
        full = new[f"{name}_exact_turn_and_full_typed_participants_owners"]
        if not (
            total == sum(new[f"{name}_turn_{tag}"] for tag in (
                "exact", "earlier", "future", "missing_or_invalid"))
            and 0 <= parts <= total
            and 0 <= owners <= total
            and 0 <= joint <= min(exact, parts)
            and 0 <= full <= min(joint, owners)
        ):
            _abstain("ABSTAIN_VCR_TEMPORAL_INPUT_CONSERVATION")
    all_rows = before + after
    raw_exact = new["before_turn_exact"] + new["after_turn_exact"]
    typed = (new["before_two_participant_objectids_typed"]
             + new["after_two_participant_objectids_typed"])
    owners = new["before_two_ownerids_typed"] + new["after_two_ownerids_typed"]
    joined = (new["before_exact_turn_and_typed_participants"]
              + new["after_exact_turn_and_typed_participants"])
    full = (new["before_exact_turn_and_full_typed_participants_owners"]
            + new["after_exact_turn_and_full_typed_participants_owners"])
    return {
        "schema": SCHEMA,
        "status": "PASS_VCR_FROZEN_TEMPORAL_INPUT_SOURCE_NOT_HOST_CAUSAL",
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_ONLY",
        "provenance": {
            "runtime_run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "frozen_selection_sha256": prior["provenance"]["frozen_selection_sha256"],
            "metadata_games": 100,
            "baseline_entity_games": 68,
            "sealed_entity_games_read": 0,
            "observational_pairs": q,
            "previous_starbase_complete_projection_matched": True,
            "new_source_aggregate_validated": True,
        },
        "vcr_observer_archive_rows_not_unique_battles": {
            "rows_before": before,
            "rows_after": after,
            "rows_total": all_rows,
            "raw_turn_equals_archive_turn": raw_exact,
            "raw_turn_earlier": (new["before_turn_earlier"] + new["after_turn_earlier"]),
            "raw_turn_future": (new["before_turn_future"] + new["after_turn_future"]),
            "raw_turn_missing_or_invalid": (
                new["before_turn_missing_or_invalid"] + new["after_turn_missing_or_invalid"]),
            "both_participant_objectids_typed": typed,
            "both_ownerids_typed": owners,
            "exact_turn_and_both_participants": joined,
            "exact_turn_and_participants_and_owners": full,
            "qualified_exact_turn_participants_but_owners_incomplete": joined - full,
            "same_generic_id_across_adjacent_archives_not_battle_link": continuity,
            "archive_pair_lists_both_empty": old_vcr["empty_lists_both"],
            "partition_conservation_verified": True,
        },
        "inference_gates": {
            "typed_same_turn_vcr_inputs_observed": True,
            "unique_battles_counted": False,
            "duplicate_observer_perspectives_deduplicated": False,
            "cross_turn_vcr_id_is_stable_battle_key": False,
            "combat_input_payloads_replay_validated_by_this_readout": False,
            "combat_results_host_diff_verified_by_this_readout": False,
            "independent_host_phase_receipts_authenticated": False,
            "accepted_host_orders_authenticated": False,
        },
    }
