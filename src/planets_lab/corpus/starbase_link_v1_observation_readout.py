"""Fail-closed, offline readout of an existing sanitized starbase source survey.

No DuckDB/Host import, reconstruction, orders or entity identities.
This module validates the *full old v6 safe projection* against the new
starbase survey, not just selected convenient counters. Observations
are repeated observer T-1/T perspectives, never causal Host actions.
"""
from __future__ import annotations
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MOD_PATH = ROOT / "src/planets_lab/corpus/minefield_v6_observation_readout.py"
_spec = spec_from_file_location("_pure_v6_replay_starbase", MOD_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("ABSTAIN_V6_REVIEW_MISSING")
_previous = module_from_spec(_spec)
_spec.loader.exec_module(_previous)
EvidenceReviewAbstain = _previous.EvidenceReviewAbstain
readout_v6_joint = _previous.readout_v6_joint

SCHEMA = "planets-lab.starbase-link-v1-source-scorecard.v1"
PROJECTION_SCHEMA = "planets-lab.starbase-link-v1-safe-projection.v1"
RUN_ID = "20261025T110236Z_7fd6ded29b14"
SOURCE_COMMIT = "7fd6ded29b14462a367f96a6871b6dc37c533356"
LINK_FIELDS = (
    "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS",
    "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED",
    "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT",
    "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED",
    "qualified_source_list_pairs",
    "same_id_planet_linked_base_current_both_archives",
    "same_id_planet_linked_base_infoturn_missing_any",
    "same_id_planet_linked_base_infoturn_stale_or_invalid_any",
    "same_id_planet_linked_current_own_both_archives",
    "same_id_starbase_observer_occurrences",
)
RUNTIME = {
    "source_commit": SOURCE_COMMIT,
    "source_branch": "main",
    "run_id": RUN_ID,
    "exit_code": 0,
    "economy_status": "PASS_VALIDATED_AGGREGATE",
    "cohort_status": "PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68",
    "pytest_status": "PASS",
    "pytest_cases": 3789,
    "pytest_failures": 0,
    "pytest_errors": 0,
    "pytest_skipped": 26,
    "generation_read_only": True,
    "heldout32_entities_read": False,
    "current_modified": False,
    "host_orders_verified": False,
    "host_diff_verified": False,
}


def abstain(message: str) -> None:
    raise EvidenceReviewAbstain(message)


def readout_starbase_link(
    v5_reference: dict[str, Any],
    v6_reference: dict[str, Any],
    starbase_projection: dict[str, Any],
) -> dict[str, Any]:
    if not all(type(x) is dict for x in (
        v5_reference, v6_reference, starbase_projection
    )):
        abstain("ABSTAIN_PROJECTION_TYPE")
    # Existing v6 counts and full original source are independently pinned.
    prior = readout_v6_joint(v5_reference, v6_reference)
    if (set(starbase_projection) != {"schema", "runtime", "source"}
        or starbase_projection["schema"] != PROJECTION_SCHEMA
        or starbase_projection["runtime"] != RUNTIME):
        abstain("ABSTAIN_STARBASE_RUNTIME")
    payload = starbase_projection["source"]
    previous = v6_reference.get("source")
    if type(payload) is not dict or type(previous) is not dict:
        abstain("ABSTAIN_STARBASE_SOURCE_TYPE")
    canonical = deepcopy(payload)
    try:
        mine = canonical["sample"]
        new_link = mine.pop("starbase_planet_archive_link_not_host_phase")
        previous_starbase = mine["nonplanet_archive_identity_readiness_not_host_phase"]["starbases"]
    except (KeyError, TypeError, AttributeError):
        abstain("ABSTAIN_STARBASE_SECTION_ABSENT")
    if canonical != previous:
        abstain("ABSTAIN_STARBASE_PRIOR_SOURCE_CHANGED")
    if type(new_link) is not dict or set(new_link) != set(LINK_FIELDS):
        abstain("ABSTAIN_STARBASE_NEW_FIELD_ALLOWLIST")
    if any(type(x) is not int or x < 0 or x > 10**12 for x in new_link.values()):
        abstain("ABSTAIN_STARBASE_NONNEGATIVE_INTEGERS")
    q = new_link["qualified_source_list_pairs"]
    same = new_link["same_id_starbase_observer_occurrences"]
    own = new_link["same_id_planet_linked_current_own_both_archives"]
    current = new_link["same_id_planet_linked_base_current_both_archives"]
    missing = new_link["same_id_planet_linked_base_infoturn_missing_any"]
    stale = new_link["same_id_planet_linked_base_infoturn_stale_or_invalid_any"]
    residual = new_link["ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED"]
    ambiguous = sum(new_link[k] for k in (
        "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS",
        "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED",
        "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT",
    ))
    if not (
        q == prior["provenance"]["observational_pairs"] == 8550
        and q == previous_starbase["qualified_identity_list_pair"]
        and same == previous_starbase["same_id_seen_in_both_archives"] == 346222
        and own + residual + ambiguous == same
        and current + missing + stale == own
        and current <= own <= same
        and prior["inference_gates"]["host_diff_verified_by_this_readout"] is False
    ):
        abstain("ABSTAIN_STARBASE_PARTITION_CONSERVATION")
    return {
        "schema": SCHEMA,
        "status": "PASS_STARBASE_OBSERVER_ARCHIVE_PLANET_LINK_NOT_HOST_CAUSAL",
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_ONLY",
        "provenance": {
            "runtime_run_id": RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "frozen_selection_sha256": prior["provenance"]["frozen_selection_sha256"],
            "metadata_games": 100,
            "baseline_entity_games": 68,
            "sealed_entity_games_read": 0,
            "observational_pairs": 8550,
            "previous_v6_complete_projection_matched": True,
            "new_source_aggregate_validated": True,
        },
        "starbase_observer_archive_occurrences_not_unique_events": {
            "same_id_both_archives": same,
            "planet_link_own_current_both_archives": own,
            "base_info_current_both_archives": current,
            "linked_planet_but_base_infoturn_missing_any": missing,
            "linked_planet_but_base_infoturn_stale_or_invalid_any": stale,
            "own_current_planet_link_unqualified": residual,
            "other_ambiguous_anchor_or_conflicting_owner": ambiguous,
            "partition_conservation_verified": True,
        },
        "inference_gates": {
            "fresh_own_planet_linked_base_observed": True,
            "unique_starbase_entities_counted": False,
            "independent_host_turn_events_counted": False,
            "base_link_proves_buildable_resources": False,
            "base_link_proves_accepted_ship_build": False,
            "base_link_proves_executed_host_construction": False,
            "accepted_host_orders_authenticated": False,
            "independent_host_phase_receipts_authenticated": False,
            "host_diff_verified_by_this_readout": False,
        },
    }
