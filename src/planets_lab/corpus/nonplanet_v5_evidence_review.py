"""Validated *descriptive* source-readiness scorecard from published v5 counts.

Reads ONLY prior sanitized aggregate JSON, NOT corpus DB or original
member records. All outputs are fixed text labels and bounded integer
counts, with no game/player/object IDs, positions or orders.
Presence and ID continuity in observer archives NEVER prove a NuHost
Host-phase outcome. In particular, separately counted 'fresh' and
'changed mine units' subsets cannot be intersected without a joint
cross-tab; this module computes only rigorous intersection bounds.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCHEMA = "planets-lab.nonplanet-v5-source-readiness-review.v1"
GENERATION = "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
GENERATION_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
FROZEN_SELECTION_SHA256 = "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659"
SECTIONS = ("minefields", "ships", "starbases", "vcrs", "ionstorms")
REQUIRED = (
    "qualified_identity_list_pair",
    "before_id_rows",
    "after_id_rows",
    "same_id_seen_in_both_archives",
    "id_only_before_archive_not_host_destruction",
    "id_only_after_archive_not_host_construction",
    "same_id_owner_unchanged",
    "same_id_owner_changed_not_host_capture",
    "same_id_owner_untyped_abstain",
    "same_id_current_own_verified_both_archives",
    "same_id_owner_own_but_infoturn_missing_or_stale",
)
MINE_KEYS = (
    "same_id_nonnegative_integer_units_both",
    "same_id_integer_units_changed_not_host_attribution",
    "same_id_owner_center_stable_units_changed_not_causal",
)
ALLOWED_COUNT_KEYS = frozenset(REQUIRED + MINE_KEYS + ("empty_lists_both", "ABSTAIN_MISSING_SECTION_LIST", "ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID"))


class EvidenceReviewAbstain(ValueError):
    """Invalid/noncomparable source aggregate: refuse qualitative promotion."""


def _mapping(data: object, code: str) -> Mapping[str, Any]:
    if not isinstance(data, dict):
        raise EvidenceReviewAbstain(code)
    return data


def _count(data: Mapping[str, Any], key: str) -> int:
    number = data.get(key, 0)
    if type(number) is not int or number < 0 or number > 10**12:
        raise EvidenceReviewAbstain("ABSTAIN_INVALID_COUNTER")
    return number


def _require(data: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    if any(k not in data for k in keys):
        raise EvidenceReviewAbstain("ABSTAIN_MISSING_REQUIRED_COUNTER")


def _validate_section(name: str, source: Mapping[str, Any], selected: int) -> dict[str, int]:
    _require(source, REQUIRED + (MINE_KEYS if name == "minefields" else ()))
    if any(k not in ALLOWED_COUNT_KEYS or (name != "minefields" and k in MINE_KEYS) for k in source):
        raise EvidenceReviewAbstain("ABSTAIN_UNEXPECTED_SOURCE_COUNTER")
    counters = {k: _count(source, k) for k in source}
    if any(not k.isascii() or not k.replace("_", "").isalnum()
           for k in counters):
        raise EvidenceReviewAbstain("ABSTAIN_UNSAFE_AGGREGATE_KEY")
    qualified = counters["qualified_identity_list_pair"]
    missing = counters.get("ABSTAIN_MISSING_SECTION_LIST", 0)
    malformed = counters.get("ABSTAIN_MALFORMED_OR_DUPLICATE_ENTITY_ID", 0)
    before = counters["before_id_rows"]
    after = counters["after_id_rows"]
    shared = counters["same_id_seen_in_both_archives"]
    owner_ok = counters["same_id_owner_unchanged"]
    owner_changed = counters["same_id_owner_changed_not_host_capture"]
    owner_unknown = counters["same_id_owner_untyped_abstain"]
    fresh = counters["same_id_current_own_verified_both_archives"]
    stale_own = counters["same_id_owner_own_but_infoturn_missing_or_stale"]
    if not (
        qualified + missing + malformed == selected
        and shared + counters["id_only_before_archive_not_host_destruction"] == before
        and shared + counters["id_only_after_archive_not_host_construction"] == after
        and owner_ok + owner_changed + owner_unknown == shared
        and fresh + stale_own <= owner_ok
    ):
        raise EvidenceReviewAbstain("ABSTAIN_COUNTER_CONSERVATION_VIOLATION")
    if name == "minefields":
        numeric = counters[MINE_KEYS[0]]
        changed = counters[MINE_KEYS[1]]
        stable = counters[MINE_KEYS[2]]
        if not (stable <= changed <= numeric <= shared):
            raise EvidenceReviewAbstain("ABSTAIN_MINE_UNITS_COUNTER_VIOLATION")
    return counters


def review_published_v5(report: Mapping[str, Any]) -> dict[str, Any]:
    """Only allow an exact source-pinned, completed, noncausal v5 report."""
    doc = _mapping(report, "ABSTAIN_INVALID_REPORT")
    if (doc.get("schema") != "planets-lab.m2-public-corpus-economy-coverage.v1"
            or doc.get("status") != "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL"):
        raise EvidenceReviewAbstain("ABSTAIN_WRONG_REPORT_SCHEMA_OR_STATUS")
    gen = _mapping(doc.get("generation"), "ABSTAIN_MISSING_GENERATION")
    if (gen.get("name") != GENERATION
            or gen.get("verified_sha256") != GENERATION_SHA256
            or gen.get("read_only") is not True
            or gen.get("CURRENT_modified") is not False):
        raise EvidenceReviewAbstain("ABSTAIN_WRONG_OR_MUTABLE_GENERATION")
    allow = _mapping(doc.get("baseline_sample_allowlist"), "ABSTAIN_BASELINE_COHORT")
    if (allow.get("allowed_game_count") != 68
            or type(allow.get("allowed_game_count")) is not int
            or allow.get("heldout_entity_sampling") is not False):
        raise EvidenceReviewAbstain("ABSTAIN_BASELINE_COHORT")
    meta = _mapping(doc.get("metadata"), "ABSTAIN_METADATA")
    selected = _count(meta, "metadata_frozen_sample_pairs")
    if (
        meta.get("all_games_in_source_metadata") != 100
        or meta.get("all_source_perspective_members") != 224014
        or meta.get("metadata_selected_game_count") != 68
        or meta.get("games_excluded_from_entity_sampling") != 32
        or selected != 8550
        or meta.get("metadata_frozen_selection_sha256") != FROZEN_SELECTION_SHA256
        or meta.get("selection_frozen_before_entity_reconstruction") is not True
    ):
        raise EvidenceReviewAbstain("ABSTAIN_WRONG_OBSERVATIONAL_POPULATION")
    limits = _mapping(doc.get("evidence_limits"), "ABSTAIN_LIMITS")
    for key in (
        "archive_identity_or_mine_unit_changes_prove_host_phase",
        "nonplanet_section_counts_prove_sweeping_or_combat",
        "T_minus_1_to_T_stock_change_identifies_action",
    ):
        if limits.get(key) is not False:
            raise EvidenceReviewAbstain("ABSTAIN_HOST_CAUSAL_PROMOTION")
    sample = _mapping(doc.get("sample"), "ABSTAIN_SAMPLE")
    statuses = _mapping(sample.get("sample_status_counts"), "ABSTAIN_SAMPLE_STATUS")
    if _count(statuses, "SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID") != selected:
        raise EvidenceReviewAbstain("ABSTAIN_PAYLOAD_IDENTITY_NOT_FULLY_QUALIFIED")
    sections = _mapping(
        sample.get("nonplanet_archive_identity_readiness_not_host_phase"),
        "ABSTAIN_NONPLANET_SOURCE_MISSING",
    )
    if set(sections) != set(SECTIONS):
        raise EvidenceReviewAbstain("ABSTAIN_UNEXPECTED_SOURCE_SECTIONS")
    summaries: dict[str, dict[str, Any]] = {}
    for name in SECTIONS:
        raw = _mapping(sections[name], "ABSTAIN_NONPLANET_SECTION")
        counts = _validate_section(name, raw, selected)
        shared = counts["same_id_seen_in_both_archives"]
        fresh = counts["same_id_current_own_verified_both_archives"]
        owner_unknown = counts["same_id_owner_untyped_abstain"]
        if shared == 0:
            state = "ABSTAIN_NO_CROSS_TURN_ID_CONTINUITY"
        elif name in ("starbases", "ionstorms") and owner_unknown == shared:
            state = ("ABSTAIN_OWNER_PROVENANCE_UNTYPED" if name == "starbases"
                     else "ID_ONLY_STORM_NO_OWNER_CAUSALITY")
        elif fresh > 0:
            state = "OBSERVED_ID_AND_FRESH_OWN_SOURCE_ONLY"
        else:
            state = "OBSERVED_ID_ONLY_OWNER_FRESHNESS_UNPROVEN"
        summaries[name] = {
            "source_state": state,
            "qualified_pair_count": counts["qualified_identity_list_pair"],
            "matching_observer_archive_id_occurrences": shared,
            "current_own_observer_archive_matches": fresh,
            "typed_owner_unavailable_id_occurrences": owner_unknown,
            "interturn_absent_id_matches_not_host_events": (
                counts["id_only_before_archive_not_host_destruction"]
                + counts["id_only_after_archive_not_host_construction"]
            ),
            "independent_host_mechanism_verified": False,
        }
    mine = _validate_section("minefields", sections["minefields"], selected)
    fresh = mine["same_id_current_own_verified_both_archives"]
    stable_changed = mine["same_id_owner_center_stable_units_changed_not_causal"]
    shared = mine["same_id_seen_in_both_archives"]
    # Exact Fréchet set-intersection bounds, nothing inferred as a joint observation.
    lower = max(0, fresh + stable_changed - shared)
    upper = min(fresh, stable_changed)
    summaries["minefields"]["stable_owner_center_and_changed_units_archive_occurrences"] = stable_changed
    summaries["minefields"]["joint_fresh_and_stable_changed_lower_bound"] = lower
    summaries["minefields"]["joint_fresh_and_stable_changed_upper_bound"] = upper
    summaries["minefields"]["exact_fresh_and_stable_changed_joint_observations_known"] = False

    return {
        "schema": SCHEMA,
        "status": "PASS_SOURCE_READINESS_CLASSIFICATION_NOT_HOST_CAUSAL",
        "provenance": {
            "generation_sha256": GENERATION_SHA256,
            "frozen_selection_sha256": FROZEN_SELECTION_SHA256,
            "baseline_games_entity_scope": 68,
            "sealed_games_entity_scope": 0,
            "observational_archive_pairs": selected,
        },
        "sections": summaries,
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_SOURCE_ONLY",
        "accepted_host_orders_authenticated": False,
        "actual_host_phase_receipts_authenticated": False,
        "host_diff_verified": False,
    }
