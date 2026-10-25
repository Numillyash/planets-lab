#!/usr/bin/env python3
"""Pin full frozen source and aggregate VCR turn/participant readiness only.

No DuckDB/site-packages needed on host; unknown VCR inputs ABSTAIN.
This does not authenticate Host combat events or cross-turn IDs.
"""
from __future__ import annotations
import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERIC = ROOT / "tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py"
SCHEMA_FIELDS = (
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
SAMPLE_SHA = "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659"
MANIFEST_SHA = "942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9"


def validate_counts(data: dict, *, pairs: int, before_rows: int,
                    after_rows: int, earlier_same_id: int) -> dict:
    if (type(data) is not dict or set(data) != set(SCHEMA_FIELDS)
        or any(type(v) is not int or v < 0 or v > 10**12 for v in data.values())
        or data["qualified_archive_pairs"] != pairs
        or data["before_vcr_rows"] != before_rows
        or data["after_vcr_rows"] != after_rows
        or data["same_id_across_adjacent_archives_not_battle_link"] != earlier_same_id):
        raise ValueError("ABSTAIN_VCR_SOURCE_FIELDS_OR_FROZEN_MARGINALS")
    for side, total in (("before",before_rows),("after",after_rows)):
        partition = sum(data[f"{side}_turn_{k}"] for k in (
            "exact","earlier","future","missing_or_invalid"))
        typed = data[f"{side}_two_participant_objectids_typed"]
        owners = data[f"{side}_two_ownerids_typed"]
        joint = data[f"{side}_exact_turn_and_typed_participants"]
        full = data[f"{side}_exact_turn_and_full_typed_participants_owners"]
        if not (
            partition == total
            and typed <= total and owners <= total
            and full <= joint <= min(typed, data[f"{side}_turn_exact"])
            and full <= owners
        ):
            raise ValueError("ABSTAIN_VCR_SOURCE_PARTITION")
    return data


def validate_report(path: Path) -> dict:
    spec=spec_from_file_location("_vcr_generic_aggregate_validation",GENERIC)
    if spec is None or spec.loader is None:
        raise ValueError("ABSTAIN_GENERIC_VALIDATOR_UNAVAILABLE")
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    p=module.validate(path)
    meta=p["metadata"]
    if (meta["metadata_frozen_selection_sha256"] != SAMPLE_SHA
        or meta["metadata_frozen_sample_pairs"] != 8550
        or meta["metadata_selected_game_count"] != 68
        or meta["all_source_perspective_members"] != 224014
        or p["baseline_sample_allowlist"]["manifest_sha256"] != MANIFEST_SHA
        or p["baseline_sample_allowlist"]["heldout_entity_sampling"] is not False):
        raise ValueError("ABSTAIN_VCR_SOURCE_WRONG_FROZEN_SELECTION")
    s=p["sample"]
    old=s["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"]
    return validate_counts(
        s["vcr_archive_temporal_input_readiness_not_host_phase"],
        pairs=old["qualified_identity_list_pair"],
        before_rows=old["before_id_rows"],
        after_rows=old["after_id_rows"],
        earlier_same_id=old["same_id_seen_in_both_archives"],
    )


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        if args.input is not None:
            print("ABSTAIN_SELFTEST_WITH_INPUT")
            return 2
        sample=dict.fromkeys(SCHEMA_FIELDS,0)
        sample.update({
            "qualified_archive_pairs":8550,
            "before_vcr_rows":21918,
            "after_vcr_rows":22414,
            "before_turn_exact":21918,
            "after_turn_exact":22414,
            "before_two_participant_objectids_typed":21918,
            "after_two_participant_objectids_typed":22414,
            "before_two_ownerids_typed":21918,
            "after_two_ownerids_typed":22414,
            "before_exact_turn_and_typed_participants":21918,
            "after_exact_turn_and_typed_participants":22414,
            "before_exact_turn_and_full_typed_participants_owners":21918,
            "after_exact_turn_and_full_typed_participants_owners":22414,
        })
        try:
            validate_counts(sample,pairs=8550,before_rows=21918,
                            after_rows=22414,earlier_same_id=0)
        except (KeyError,ValueError,TypeError):
            print("ABSTAIN_VCR_SYNTHETIC_PRECHECK")
            return 2
        print("PASS_VCR_SYNTHETIC_PRECHECK_ONLY")
        return 0
    if args.input is None:
        print("ABSTAIN_VCR_SOURCE_INPUT_REQUIRED")
        return 2
    try:
        counts=validate_report(args.input)
    except (KeyError,ValueError,TypeError,OSError,AttributeError):
        print("ABSTAIN_VCR_SOURCE_AGGREGATE")
        return 2
    print("PASS_VCR_ARCHIVE_INPUT_READINESS_NONCAUSAL")
    print("before_exact_and_participants="+str(counts["before_exact_turn_and_typed_participants"]))
    print("after_exact_and_participants="+str(counts["after_exact_turn_and_typed_participants"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
