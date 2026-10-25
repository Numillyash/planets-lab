#!/usr/bin/env python3
"""Fail-closed gate for publishing ONLY the aggregate M2 corpus coverage report.

Validates the produced JSON before it is copied by the existing
tools/run-with-runtime-evidence.sh. Does not read any DuckDB and does
not print per-game/player/planet information or any report payload.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SCHEMA = "planets-lab.m2-public-corpus-economy-coverage.v1"
EXPECTED_GENERATION = "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
ROOT_FIELDS = {
    "schema", "status", "generation", "baseline_sample_allowlist",
    "metadata", "sample", "evidence_limits",
}
METADATA_FIELDS = {
    "all_games_in_source_metadata", "all_source_perspective_members",
    "identity_valid_members", "metadata_invalid_or_embedded_turn_mismatch",
    "ambiguous_duplicate_perspective_turn_keys",
    "potential_adjacent_same_perspective_pairs",
    "games_with_adjacent_perspective_pairs",
    "games_allowed_for_entity_sampling", "games_excluded_from_entity_sampling",
    "metadata_selected_game_count", "metadata_frozen_sample_pairs",
    "metadata_frozen_selection_sha256",
    "selection_frozen_before_entity_reconstruction",
}
SAMPLE_FIELDS = {
    "sample_status_counts", "owner_current_counts",
    "qualified_planet_field_family_pairs", "net_state_differences_not_mechanics",
    "section_rows_across_sampled_perspectives",
    "individual_numeric_field_directions",
    "surface_ground_joint_signs_not_mining_attribution",
    "observable_structure_and_tax_controls",
    "conditional_mineral_mass_balance_not_host_verified",
    "surface_residual_context_not_host_verified",
    "nonplanet_section_observability_not_host_phase",
    "nonplanet_archive_identity_readiness_not_host_phase",
    "starbase_planet_archive_link_not_host_phase",
    "vcr_archive_temporal_input_readiness_not_host_phase",
}
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


def _aggregate_only(data: object, *, section: str) -> None:
    """Nested aggregate payloads must be counters, never raw records."""
    if not isinstance(data, dict):
        raise ValueError(f"{section}: expected aggregate object")
    for key, value in data.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", key):
            raise ValueError(f"{section}: invalid key")
        if isinstance(value, dict):
            _aggregate_only(value, section=section)
        elif type(value) is not int or value < 0:
            raise ValueError(f"{section}: non-count value")
        # Lists, strings, booleans, null and raw payloads are NEVER
        # admissible within an aggregate count section.


def validate(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != ROOT_FIELDS:
        raise ValueError("unexpected report root keys; refuse to publish")
    if payload["schema"] != SCHEMA or payload["status"] != (
        "CORPUS_METADATA_CENSUS_AND_BOUNDED_OWNER_CURRENT_SAMPLE_NOT_HOST_CAUSAL"
    ):
        raise ValueError("wrong aggregate report schema/status")
    g = payload["generation"]
    if not isinstance(g, dict) or set(g) != {
        "name", "verified_sha256", "read_only", "CURRENT_modified",
    } or g["name"] != EXPECTED_GENERATION or g["verified_sha256"] != EXPECTED_SHA:
        raise ValueError("unexpected corpus generation/provenance")
    if g["read_only"] is not True or g["CURRENT_modified"] is not False:
        raise ValueError("corpus read-only/CURRENT integrity not confirmed")
    baseline = payload["baseline_sample_allowlist"]
    if not isinstance(baseline, dict) or set(baseline) != {
        "manifest_sha256", "allowed_game_count", "heldout_entity_sampling",
    } or baseline["allowed_game_count"] != 68 or (
        baseline["heldout_entity_sampling"] is not False
    ) or not isinstance(baseline["manifest_sha256"], str) or not HEX64.fullmatch(
        baseline["manifest_sha256"]
    ):
        raise ValueError("unverified baseline68/heldout boundary")
    metadata = payload["metadata"]
    if not isinstance(metadata, dict) or set(metadata) != METADATA_FIELDS:
        raise ValueError("unexpected metadata shape")
    if not isinstance(metadata["metadata_frozen_selection_sha256"], str) or (
        not HEX64.fullmatch(metadata["metadata_frozen_selection_sha256"])
    ):
        raise ValueError("invalid sample selection SHA")
    if metadata["selection_frozen_before_entity_reconstruction"] is not True:
        raise ValueError("selection was not metadata-frozen")
    if metadata["games_allowed_for_entity_sampling"] != 68 or (
        metadata["games_excluded_from_entity_sampling"] != 32
    ) or metadata["all_games_in_source_metadata"] != 100:
        raise ValueError("incorrect public100/baseline68/heldout32 boundary")
    for key, value in metadata.items():
        if key in (
            "metadata_frozen_selection_sha256",
            "selection_frozen_before_entity_reconstruction",
        ):
            continue
        if type(value) is not int or value < 0:
            raise ValueError("unexpected non-count metadata")
    sample = payload["sample"]
    if not isinstance(sample, dict) or not set(sample).issubset(SAMPLE_FIELDS):
        raise ValueError("unexpected sample keys")
    for key, value in sample.items():
        if key == "conditional_mineral_mass_balance_not_host_verified":
            if not isinstance(value, dict) or set(value) != {
                "model", "per_mineral",
                "surface_up_ground_equal_surface_increase_buckets",
                "net_total_minus_default_mutation_abs_residual_buckets",
            } or value["model"] != (
                "INFERRED_DEFAULT_MINING_PLUS_PUBLISHED_TRANSURANIUM_NOT_HOST_CAUSAL"
            ):
                raise ValueError("unexpected mineral model annotation")
            for subkey, section in value.items():
                if subkey != "model":
                    _aggregate_only(section, section=subkey)
        else:
            _aggregate_only(value, section=key)
    limits = payload["evidence_limits"]
    if not isinstance(limits, dict) or not limits or any(
        type(v) is not bool for v in limits.values()
    ):
        raise ValueError("missing/invalid evidence boundaries")
    for important in (
        "raw_trn_is_submitted_turn_orders",
        "NuHost_ship_build_cost_verified",
        "T_minus_1_to_T_stock_change_identifies_action",
        "NuHost_economic_formula_verified",
    ):
        if limits.get(important) is not False:
            raise ValueError("causal verification flags must be false")
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    payload = validate(args.input)
    print("existing_M2_aggregate_report: validated")
    print("source_generation_sha256:", payload["generation"]["verified_sha256"])
    print(
        "frozen_selection_sha256:",
        payload["metadata"]["metadata_frozen_selection_sha256"],
    )
    print("baseline_allowed_games: 68")
    print("heldout_entity_sampling: false")
    print("note: existing report is being published, NOT rerun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
