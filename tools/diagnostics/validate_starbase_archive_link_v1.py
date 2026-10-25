#!/usr/bin/env python3
"""Strict *aggregate-only* gate for optional frozen starbase→planet source audit.

Host python -I -S compatible, no DuckDB or raw entity loads here.
"""
from __future__ import annotations
import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_GATE = ROOT / "tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py"
SCHEMA_KEYS = (
    "qualified_source_list_pairs",
    "same_id_starbase_observer_occurrences",
    "same_id_planet_linked_current_own_both_archives",
    "same_id_planet_linked_base_current_both_archives",
    "same_id_planet_linked_base_infoturn_missing_any",
    "same_id_planet_linked_base_infoturn_stale_or_invalid_any",
    "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED",
    "ABSTAIN_SAME_ID_ANCHOR_MISSING_OR_CHANGED",
    "ABSTAIN_SAME_ID_ANCHOR_AMBIGUOUS",
    "ABSTAIN_SAME_ID_BASE_OWNER_CONFLICT",
)
PIN_SELECTION = "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659"
PIN_MANIFEST = "942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9"


def _generic_validate(path: Path):
    spec = spec_from_file_location("_pure_m2_aggregate_gate", BASE_GATE)
    if spec is None or spec.loader is None:
        raise ValueError("ABSTAIN_GENERIC_GATE_MODULE_NOT_FOUND")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(path)


def validate_links(link: dict, *, selected: int, shared: int,
                   qualified_old: int) -> None:
    if (type(selected) is not int or selected <= 0
        or type(shared) is not int or shared < 0
        or type(qualified_old) is not int or qualified_old != selected
        or not isinstance(link, dict) or set(link) != set(SCHEMA_KEYS)
        or any(type(value) is not int or value < 0 or value > 10**12
               for value in link.values())):
        raise ValueError("ABSTAIN_STARBASE_LINK_SCHEMA")
    q = link["qualified_source_list_pairs"]
    same = link["same_id_starbase_observer_occurrences"]
    own = link["same_id_planet_linked_current_own_both_archives"]
    fresh = link["same_id_planet_linked_base_current_both_archives"]
    noinfo = link["same_id_planet_linked_base_infoturn_missing_any"]
    stale = link["same_id_planet_linked_base_infoturn_stale_or_invalid_any"]
    excluded = sum(link[k] for k in SCHEMA_KEYS if k.startswith("ABSTAIN_SAME_ID_"))
    if not (
        q == selected == 8550
        and same == shared == 346222
        and own + excluded == same
        and fresh + noinfo + stale == own
    ):
        raise ValueError("ABSTAIN_STARBASE_LINK_CONSERVATION")


def validate_report(path: Path) -> dict:
    report = _generic_validate(path)
    meta = report["metadata"]
    source = report["sample"]
    previous = source["nonplanet_archive_identity_readiness_not_host_phase"]["starbases"]
    if (meta["metadata_frozen_selection_sha256"] != PIN_SELECTION
        or meta["metadata_frozen_sample_pairs"] != 8550
        or meta["metadata_selected_game_count"] != 68
        or meta["all_source_perspective_members"] != 224014
        or report["baseline_sample_allowlist"]["manifest_sha256"] != PIN_MANIFEST
        or "starbase_planet_archive_link_not_host_phase" not in source):
        raise ValueError("ABSTAIN_UNPINNED_STARBASE_POPULATION")
    result = source["starbase_planet_archive_link_not_host_phase"]
    validate_links(result, selected=8550,
                   shared=previous["same_id_seen_in_both_archives"],
                   qualified_old=previous["qualified_identity_list_pair"])
    for flag in ("host_diff_verified", "independent_host_phase_receipts_authenticated"):
        if report.get(flag) is True:
            raise ValueError("ABSTAIN_HOST_VERIFIED_PROMOTION")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        if args.input is not None:
            print("ABSTAIN_SELF_TEST_INPUT")
            return 2
        synthetic = dict.fromkeys(SCHEMA_KEYS, 0)
        synthetic.update({
            "qualified_source_list_pairs": 8550,
            "same_id_starbase_observer_occurrences": 346222,
            "same_id_planet_linked_current_own_both_archives": 7,
            "same_id_planet_linked_base_current_both_archives": 2,
            "same_id_planet_linked_base_infoturn_missing_any": 4,
            "same_id_planet_linked_base_infoturn_stale_or_invalid_any": 1,
            "ABSTAIN_SAME_ID_PLANET_LINK_OR_OWNER_UNQUALIFIED": 346215,
        })
        try:
            validate_links(synthetic, selected=8550, shared=346222,
                           qualified_old=8550)
        except ValueError:
            print("ABSTAIN_STARBASE_LINK_SYNTHETIC_SELF_TEST")
            return 2
        print("PASS_STARBASE_LINK_SYNTHETIC_SELF_TEST_ONLY")
        return 0
    if args.input is None:
        print("ABSTAIN_INPUT_REQUIRED")
        return 2
    try:
        counts = validate_report(args.input)
    except (ValueError, KeyError, TypeError, OSError):
        print("ABSTAIN_STARBASE_LINK_SOURCE")
        return 2
    print("PASS_STARBASE_PLANET_LINK_OBSERVATIONAL_ONLY")
    print("linked_own_archive_occurrences=" +
          str(counts["same_id_planet_linked_current_own_both_archives"]))
    print("linked_base_fresh_archive_occurrences=" +
          str(counts["same_id_planet_linked_base_current_both_archives"]))
    print("host_diff_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
