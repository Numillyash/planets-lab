#!/usr/bin/env python3
"""Frozen 8550-pair SAME TURN VCR source consensus aggregate validator.

Only fixed integers; this audit does not establish unique battles,
authenticated Host combat inputs, or an accepted Host phase receipt.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[2]
GENERIC = ROOT / "tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py"
SELECTION = "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659"
MANIFEST = "942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9"
SECTION = "vcr_same_turn_perspective_consensus_not_host_phase"
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

def validate_counts(c: object, *, original_pairs: int) -> dict:
    if (type(c) is not dict or set(c) != set(FIELDS)
            or any(type(x) is not int or x < 0 or x > 10**12
                   for x in c.values())
            or c["qualified_original_frozen_adjacent_pairs"] != original_pairs
            or original_pairs != 8550):
        raise ValueError("ABSTAIN_VCR_CONSENSUS_FIXED_SOURCE_SCHEMA")
    members = c["unique_frozen_archive_members_examined"]
    rows = c["vcr_rows_in_unique_member_archives"]
    qualified = c["vcr_rows_qualified_same_turn_typed_participants"]
    groups = c["same_turn_observation_groups"]
    multi = c["multi_perspective_groups"]
    if not (
        0 <= members <= 17100
        and 0 <= rows <= 44332
        and members == sum(c[x] for x in (
            "qualified_member_vcr_lists",
            "ABSTAIN_MEMBER_VCR_LIST_MISSING_OR_UNTYPED",
            "ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE"))
        and rows == qualified + sum(c[x] for x in (
            "vcr_rows_unqualified_atomic_member_abstain",
            "vcr_rows_unqualified_turn_or_participant",
            "vcr_rows_unqualified_unserializable_input"))
        and c["source_observation_rows_in_qualified_groups"] == qualified
        and groups == c["single_perspective_groups"] + multi
        and multi == (c["multi_perspective_groups_two_observers"]
                      + c["multi_perspective_groups_three_or_more_observers"])
        and 2*multi <= c["multi_perspective_observer_occurrences"] <= qualified
        and (c["multi_perspective_observer_occurrences"]
             + c["single_perspective_groups"] == qualified)
        and multi == sum(c[x] for x in (
            "multi_perspective_strict_inputs_incomplete",
            "multi_perspective_strict_complete_inputs_equal",
            "multi_perspective_strict_complete_inputs_different"))
        and all(multi == c[f"multi_perspective_{field}_equal"]
                + c[f"multi_perspective_{field}_different"]
                for field in ("vcr_payload","weapon_catalog","combat_rng_settings",
                              "complete_adapter_signature"))
        and all(c[x] <= qualified for x in (
            "vcr_rows_missing_typed_weapon_catalog",
            "vcr_rows_missing_explicit_combat_rng",
            "vcr_rows_missing_typed_owner_pair"))
    ):
        raise ValueError("ABSTAIN_VCR_CONSENSUS_CONSERVATION")
    return c

def validate_report(path: Path) -> dict:
    spec = spec_from_file_location("_generic_m2_consensus_gate", GENERIC)
    if spec is None or spec.loader is None:
        raise ValueError("ABSTAIN_GENERIC_SOURCE_GATE")
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    data=module.validate(path)
    m=data["metadata"];b=data["baseline_sample_allowlist"]
    if (m["metadata_frozen_selection_sha256"] != SELECTION
        or m["metadata_frozen_sample_pairs"] != 8550
        or m["metadata_selected_game_count"] != 68
        or m["all_source_perspective_members"] != 224014
        or b["manifest_sha256"] != MANIFEST
        or b["allowed_game_count"] != 68
        or b["heldout_entity_sampling"] is not False
        or data["evidence_limits"].get("nonplanet_section_counts_prove_sweeping_or_combat") is not False):
        raise ValueError("ABSTAIN_UNPINNED_SAME_TURN_SOURCE")
    result=data["sample"][SECTION]
    q=data["sample"]["sample_status_counts"]["SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID"]
    return validate_counts(result, original_pairs=q)

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        if args.input is not None:
            print("ABSTAIN_SELFTEST_WITH_INPUT")
            return 2
        d=dict.fromkeys(FIELDS,0)
        d.update(qualified_original_frozen_adjacent_pairs=8550,
                 unique_frozen_archive_members_examined=2,
                 qualified_member_vcr_lists=2,
                 vcr_rows_in_unique_member_archives=2,
                 vcr_rows_qualified_same_turn_typed_participants=2,
                 source_observation_rows_in_qualified_groups=2,
                 same_turn_observation_groups=1,multi_perspective_groups=1,
                 multi_perspective_groups_two_observers=1,
                 multi_perspective_observer_occurrences=2,
                 multi_perspective_vcr_payload_equal=1,
                 multi_perspective_weapon_catalog_equal=1,
                 multi_perspective_combat_rng_settings_equal=1,
                 multi_perspective_complete_adapter_signature_equal=1,
                 multi_perspective_strict_complete_inputs_equal=1)
        try:
            validate_counts(d,original_pairs=8550)
        except (ValueError,KeyError,TypeError):
            print("ABSTAIN_SYNTHETIC_CONSENSUS_SELF_TEST")
            return 2
        print("PASS_VCR_SAME_TURN_CONSENSUS_SYNTHETIC_SELF_TEST_ONLY")
        return 0
    if args.input is None:
        print("ABSTAIN_VCR_CONSENSUS_SOURCE_REQUIRED")
        return 2
    try:
        counts=validate_report(args.input)
    except (ValueError,OSError,KeyError,TypeError,AttributeError, json.JSONDecodeError):
        print("ABSTAIN_VCR_CONSENSUS_SOURCE")
        return 2
    print("PASS_FROZEN_VCR_SAME_TURN_SOURCE_ONLY")
    print("multi_perspective_groups="+str(counts["multi_perspective_groups"]))
    print("host_diff_verified=false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
