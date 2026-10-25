"""Offline, fail-closed readout of the real validated v6 minefield joint source.

This is NOT a NuHost mine decay/sweep/phase oracle. Repeated T-1/T
observer archive occurrences are not independent Host actions.
No DB, server connection, orders or per-object identifiers are read here.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from planets_lab.corpus.nonplanet_v5_evidence_review import (
    EvidenceReviewAbstain, review_published_v5,
)

SCHEMA = "planets-lab.minefield-v6-joint-observation-readout.v1"
V6_FIXTURE_SCHEMA = "planets-lab.minefield-v6-safe-aggregate-projection.v1"
RUN_ID = "20261025T002616Z_cd6140b03aa5"
COMMIT = "cd6140b03aa5be714f9245a9a4966f97a9fbbf5a"
SELECTION = "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659"
JOINT = (
    "same_id_fresh_own_center_stable_numeric_units_joint",
    "same_id_fresh_own_center_stable_units_increased_joint_not_causal",
    "same_id_fresh_own_center_stable_units_decreased_joint_not_causal",
    "same_id_fresh_own_center_stable_units_unchanged_joint_not_causal",
    "same_id_fresh_own_center_stable_units_changed_joint_not_causal",
)
RUNTIME = {
    "run_id": RUN_ID,
    "source_commit": COMMIT,
    "source_branch": "main",
    "exit_code": 0,
    "stage_economy_status": "PASS_VALIDATED_AGGREGATE",
    "stage_pytest_status": "PASS",
    "stage_baseline_cohort": "PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68",
    "database_read_only": True,
    "heldout32_entities_read": False,
    "current_modified": False,
    "accepted_host_orders_verified": False,
    "host_diff_verified": False,
}


def _abstain(code: str) -> None:
    raise EvidenceReviewAbstain(code)


def readout_v6_joint(
    original_v5: Mapping[str, Any],
    v6_safe: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-validate v5 and v6 *same frozen selection* without corpus access.

    Accept only an exact projection of published v6 source margins: all v5
    counters must replay identically, and precisely five new joint counts
    may be added under minefields. Reject any extra keys/raw identifiers.
    """
    if not isinstance(original_v5, dict) or not isinstance(v6_safe, dict):
        _abstain("ABSTAIN_INPUT_TYPE")
    review_published_v5(original_v5)
    if set(v6_safe) != {"schema", "runtime", "source"} or (
        v6_safe.get("schema") != V6_FIXTURE_SCHEMA
        or v6_safe.get("runtime") != RUNTIME
    ):
        _abstain("ABSTAIN_V6_RUNTIME_PROVENANCE")
    source = v6_safe.get("source")
    if not isinstance(source, dict) or set(source) != set(original_v5):
        _abstain("ABSTAIN_SOURCE_PROJECTION_ROOT")
    projected = deepcopy(source)
    try:
        mine = projected["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
        raw_mine = source["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
    except (KeyError, TypeError):
        _abstain("ABSTAIN_SOURCE_SECTION_MISSING")
    if not isinstance(mine, dict) or not isinstance(raw_mine, dict):
        _abstain("ABSTAIN_MINE_SECTION_TYPE")
    old_mine = original_v5["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
    if set(mine) != set(old_mine) | set(JOINT):
        _abstain("ABSTAIN_V6_JOINT_COUNTER_SCHEMA")
    counts = {key: mine[key] for key in JOINT}
    if any(type(v) is not int or not 0 <= v <= 10**12 for v in counts.values()):
        _abstain("ABSTAIN_JOINT_INVALID_COUNT")
    for name in JOINT:
        del mine[name]
    # Equality covers every pinned generation, sample, status, observational
    # source marginal, section and causal-flag, not just four cherry-picked.
    if projected != original_v5:
        _abstain("ABSTAIN_V5_V6_FROZEN_MARGIN_MISMATCH")
    # Independently call the existing source-review gate, including the
    # 100-meta / baseline68 / 8550 SHA / sealed32 / Host-causal gates.
    v5 = review_published_v5(projected)
    n, increased, decreased, unchanged, changed = (counts[k] for k in JOINT)
    old_counts = old_mine
    fresh = old_counts["same_id_current_own_verified_both_archives"]
    stable_changed = old_counts["same_id_owner_center_stable_units_changed_not_causal"]
    shared = old_counts["same_id_seen_in_both_archives"]
    lo, hi = max(0, fresh + stable_changed - shared), min(fresh, stable_changed)
    if not (
        n == increased + decreased + unchanged
        and changed == increased + decreased
        and changed <= stable_changed
        and changed <= old_counts["same_id_integer_units_changed_not_host_attribution"]
        and n <= fresh
        and n <= old_counts["same_id_nonnegative_integer_units_both"]
        and lo <= changed <= hi
        and v5["provenance"]["frozen_selection_sha256"] == SELECTION
    ):
        _abstain("ABSTAIN_JOINT_COUNT_CONSERVATION")
    return {
        "schema": SCHEMA,
        "status": "PASS_FROZEN_COHORT_JOINT_OBSERVATION_NOT_CAUSAL",
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_ONLY",
        "provenance": {
            "runtime_run_id": RUN_ID,
            "source_commit": COMMIT,
            "frozen_selection_sha256": SELECTION,
            "metadata_games": 100,
            "baseline_entity_games": 68,
            "sealed_entity_games_read": 0,
            "observational_pairs": 8550,
            "v5_marginals_replayed_identically": True,
            "source_report_validated": True,
        },
        "minefield_observation_occurrences_not_unique_events": {
            "same_id_across_archives": shared,
            "fresh_owned_both_archives": fresh,
            "fresh_owned_stable_center_numeric_units_joint": n,
            "fresh_owned_excluded_from_stable_numeric_joint": fresh - n,
            "joint_units_increased": increased,
            "joint_units_decreased": decreased,
            "joint_units_unchanged": unchanged,
            "joint_units_changed": changed,
            "joint_units_change_consistency_verified": True,
            "previously_unknown_fresh_and_stable_changed_intersection_exact": changed,
            "v5_marginal_intersection_lower_bound": lo,
            "v5_marginal_intersection_upper_bound": hi,
        },
        "inference_gates": {
            "same_row_fresh_owned_and_units_joint_observed": True,
            "unique_minefield_entities_counted": False,
            "independent_host_turn_events_counted": False,
            "minefield_decay_phase_authenticated": False,
            "ship_beam_or_fighter_sweep_phase_authenticated": False,
            "mine_hit_overlap_placement_phase_authenticated": False,
            "accepted_host_orders_authenticated": False,
            "independent_host_phase_receipts_authenticated": False,
            "host_diff_verified_by_this_readout": False,
        },
    }
