#!/usr/bin/env python3
"""Independent stdlib-only strict gate for VCR same-turn missing-input joint.

Requires the verified original V1 frozen consensus counters unmodified and
publishes only integer aggregates, never keys/signatures/Host battle claims.
"""
from __future__ import annotations

import argparse
from importlib.util import spec_from_file_location, module_from_spec
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRIOR=ROOT/"tools/diagnostics/validate_vcr_same_turn_consensus_v1.py"
SECTION="vcr_same_turn_missingness_joint_not_host_phase"
REASONS=(
    "complete","rng_only","owner_only","catalog_only",
    "rng_owner","rng_catalog","owner_catalog","rng_owner_catalog",
)
FIELDS=(
    "qualified_original_frozen_adjacent_pairs",
    "source_observation_rows_qualified",
    "single_perspective_groups",
    "multi_perspective_groups",
    "single_source_observation_rows",
    "multi_source_observation_rows",
    "single_missing_rng_rows",
    "multi_missing_rng_rows",
    "single_missing_owner_rows",
    "multi_missing_owner_rows",
    "single_missing_catalog_rows",
    "multi_missing_catalog_rows",
    "multi_complete_signature_equal",
    "multi_complete_signature_different",
    "multi_incomplete_signature_equal",
    "multi_incomplete_signature_different",
)+tuple(f"{kind}_{reason}_groups"
        for kind in ("single","multi") for reason in REASONS)


def validate_joint(joint: object, prior: dict) -> dict:
    if (type(joint) is not dict or set(joint)!=set(FIELDS)
            or any(type(x) is not int or x<0 or x>10**12
                   for x in joint.values())):
        raise ValueError("ABSTAIN_MISSINGNESS_JOINT_ALLOWLIST")
    j=joint
    if not (
        j["qualified_original_frozen_adjacent_pairs"]==
            prior["qualified_original_frozen_adjacent_pairs"]==8550
        and j["source_observation_rows_qualified"]==
            prior["vcr_rows_qualified_same_turn_typed_participants"]==44332
        and j["single_perspective_groups"]==
            prior["single_perspective_groups"]==32120
        and j["multi_perspective_groups"]==
            prior["multi_perspective_groups"]==6106
        and j["single_source_observation_rows"]==32120
        and j["multi_source_observation_rows"]==
            prior["multi_perspective_observer_occurrences"]==12212
        and j["single_source_observation_rows"]+
            j["multi_source_observation_rows"]==
            j["source_observation_rows_qualified"]
        and sum(j[f"single_{name}_groups"] for name in REASONS)==32120
        and sum(j[f"multi_{name}_groups"] for name in REASONS)==6106
        and j["multi_complete_groups"]==
            prior["multi_perspective_strict_complete_inputs_equal"]+
            prior["multi_perspective_strict_complete_inputs_different"]==6047
        and sum(j[f"multi_{name}_groups"] for name in REASONS if name!="complete")
            ==prior["multi_perspective_strict_inputs_incomplete"]==59
        and j["single_missing_rng_rows"]+j["multi_missing_rng_rows"]==
            prior["vcr_rows_missing_explicit_combat_rng"]==323
        and j["single_missing_owner_rows"]+j["multi_missing_owner_rows"]==
            prior["vcr_rows_missing_typed_owner_pair"]==1
        and j["single_missing_catalog_rows"]+j["multi_missing_catalog_rows"]==
            prior["vcr_rows_missing_typed_weapon_catalog"]==0
        and j["multi_complete_signature_equal"]==
            prior["multi_perspective_strict_complete_inputs_equal"]==6047
        and j["multi_complete_signature_different"]==
            prior["multi_perspective_strict_complete_inputs_different"]==0
        and j["multi_incomplete_signature_equal"]+
            j["multi_incomplete_signature_different"]==59
        and j["multi_complete_signature_equal"]+
            j["multi_incomplete_signature_equal"]==
            prior["multi_perspective_complete_adapter_signature_equal"]==6106
        and j["multi_complete_signature_different"]+
            j["multi_incomplete_signature_different"]==
            prior["multi_perspective_complete_adapter_signature_different"]==0
        and all(j[f"{kind}_missing_{name}_rows"]<=j[f"{kind}_source_observation_rows"]
                for kind in ("single","multi") for name in ("rng","owner","catalog"))
        and all((sum(j[f"{kind}_{reason}_groups"] for reason in REASONS
                     if token in reason.split("_"))==0
                or j[f"{kind}_missing_{field}_rows"]>=
                     sum(j[f"{kind}_{reason}_groups"] for reason in REASONS
                         if token in reason.split("_")))
                for kind in ("single","multi")
                for token,field in (("rng","rng"),("owner","owner"),("catalog","catalog")))
    ):
        raise ValueError("ABSTAIN_MISSINGNESS_JOINT_SOURCE_CONSERVATION")
    return j


def validate_report(path: Path) -> dict:
    spec=spec_from_file_location("_prior_v1_source_consensus_validator",PRIOR)
    if spec is None or spec.loader is None:
        raise ValueError("ABSTAIN_PREVIOUS_CONSENSUS_GATE_MISSING")
    oldmod=module_from_spec(spec)
    spec.loader.exec_module(oldmod)
    prior=oldmod.validate_report(path)
    payload=json.loads(path.read_text(encoding="utf-8"))
    new=payload["sample"].get(SECTION)
    return validate_joint(new,prior)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--input",type=Path)
    args=parser.parse_args()
    if args.self_test:
        if args.input is not None:
            print("ABSTAIN_SELF_TEST_INPUT")
            return 2
        p={
            "qualified_original_frozen_adjacent_pairs":8550,
            "vcr_rows_qualified_same_turn_typed_participants":44332,
            "single_perspective_groups":32120,
            "multi_perspective_groups":6106,
            "multi_perspective_observer_occurrences":12212,
            "multi_perspective_strict_complete_inputs_equal":6047,
            "multi_perspective_strict_complete_inputs_different":0,
            "multi_perspective_strict_inputs_incomplete":59,
            "vcr_rows_missing_explicit_combat_rng":323,
            "vcr_rows_missing_typed_owner_pair":1,
            "vcr_rows_missing_typed_weapon_catalog":0,
            "multi_perspective_complete_adapter_signature_equal":6106,
            "multi_perspective_complete_adapter_signature_different":0,
        }
        j=dict.fromkeys(FIELDS,0)
        j.update(
            qualified_original_frozen_adjacent_pairs=8550,
            source_observation_rows_qualified=44332,
            single_perspective_groups=32120,multi_perspective_groups=6106,
            single_source_observation_rows=32120,multi_source_observation_rows=12212,
            single_missing_rng_rows=264,multi_missing_rng_rows=59,
            single_missing_owner_rows=1,
            single_complete_groups=31855,single_rng_only_groups=264,
            single_owner_only_groups=1,
            multi_complete_groups=6047,multi_rng_only_groups=59,
            multi_complete_signature_equal=6047,multi_incomplete_signature_equal=59,
        )
        try:
            validate_joint(j,p)
        except (KeyError,ValueError,TypeError):
            print("ABSTAIN_SYNTHETIC_JOINT_SELFTEST")
            return 2
        print("PASS_SYNTHETIC_VCR_MISSINGNESS_JOINT_ONLY")
        return 0
    if args.input is None:
        print("ABSTAIN_REAL_REPORT_INPUT_REQUIRED")
        return 2
    try:
        j=validate_report(args.input)
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        print("ABSTAIN_VCR_MISSINGNESS_JOINT_SOURCE")
        return 2
    print("PASS_VCR_MISSINGNESS_JOINT_NONCAUSAL")
    print("multi_incomplete_source_groups="+str(
        sum(j[f"multi_{r}_groups"] for r in REASONS if r!="complete")))
    print("host_diff_verified=false")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
