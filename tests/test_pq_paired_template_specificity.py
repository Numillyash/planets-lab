"""Paired, within-window template specificity is descriptive, not Host build parity."""
from __future__ import annotations

import json
import zipfile
from copy import deepcopy

import pytest

from planets_lab.corpus.pq_paired_template_specificity import (
    SCHEMA, paired_template_specificity,
)
from planets_lab.corpus.pq_control_multigame_observation import survey_frozen_public_ppq
from test_pq_window_field_sufficiency import make_fixture


def candidate(*, new_status="OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH", n=1):
    return {
        "host_causal_verified": False,
        "hull_engine_match_proves_construction": False,
        "newly_visible_owned_current_ship_count": n,
        "before_current_base_vs_new_ship": new_status,
        "secret": "PRIVATE_NEVER_PRINT",
    }


def baseline(*, matched=0, missed=2, untyped=0, stable=None,
             status="REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS", n=1):
    if stable is None:
        stable = matched + missed + untyped
    return {
        "host_causal_verified": False,
        "persistent_ships_are_independent_negative_samples": False,
        "status": status,
        "newly_visible_owned_ship_identity_count": n,
        "stable_owned_ship_id_intersection_count": stable,
        "typed_stable_ship_base_template_comparisons": matched + missed,
        "matches_before_base_hull_and_engine": matched,
        "does_not_match_before_base_hull_and_engine": missed,
        "stable_ships_with_untyped_hull_or_engine": untyped,
        "private": "SECRET_SOURCE_ID",
    }


@pytest.mark.parametrize("match,miss,expected", [
    (0, 3, "NEW_SHIP_MATCHES_BASE_NONE_OF_PERSISTENT_SHIPS_MATCH"),
    (1, 3, "NEW_SHIP_MATCHES_BASE_SOME_PERSISTENT_SHIPS_MATCH"),
    (3, 0, "NEW_SHIP_MATCHES_BASE_SOME_PERSISTENT_SHIPS_MATCH"),
])
def test_full_new_ship_match_paired_with_same_window_persistent_reference(match, miss, expected):
    result = paired_template_specificity(candidate(), baseline(matched=match, missed=miss))
    assert result["schema"] == SCHEMA
    assert result["paired_observational_category"] == expected
    assert result["same_window_persistent_ship_comparison_count"] == match + miss
    assert result["same_window_persistent_ship_template_match_count"] == match
    assert result["same_window_persistent_ship_template_mismatch_count"] == miss
    assert result["new_ship_matches_full_prior_base_template"]
    assert result["one_newly_visible_ship_template_compared"]
    assert all(result[k] is False for k in (
        "same_window_control_is_independent",
        "across_window_independence_established",
        "pairing_is_independent_statistical_validation",
        "observed_appearance_proves_construction",
        "base_configuration_is_host_accepted_order",
        "host_causal_verified",
        "raw_entity_ids_or_values_emitted",
    ))
    encoded = json.dumps(result)
    assert "PRIVATE_NEVER_PRINT" not in encoded
    assert "SECRET_SOURCE_ID" not in encoded


@pytest.mark.parametrize("ref,expected", [
    (baseline(matched=0, missed=0, stable=0, status="ABSTAIN_NO_PERSISTENT_OWNED_SHIP_REFERENCE"),
     "ABSTAIN_PERSISTENT_REFERENCE_UNQUALIFIED"),
    (baseline(matched=0, missed=0, stable=0, status="ABSTAIN_NO_UNIQUE_CURRENT_BASE"),
     "ABSTAIN_PERSISTENT_REFERENCE_UNQUALIFIED"),
    (baseline(matched=0, missed=0, stable=1, status="ABSTAIN_NO_TYPED_PERSISTENT_SHIP_SPECS", untyped=1),
     "ABSTAIN_PERSISTENT_REFERENCE_UNQUALIFIED"),
])
def test_explicit_reference_abstentions_are_not_fabricated_zero_matches(ref, expected):
    r = paired_template_specificity(candidate(), ref)
    assert r["paired_observational_category"] == expected
    assert not r["host_causal_verified"]


def test_new_ship_without_unique_base_abstains_even_if_persistent_compared():
    r = paired_template_specificity(
        candidate(new_status="ABSTAIN_NO_UNIQUE_CURRENT_BASE"), baseline(),
    )
    assert r["paired_observational_category"] == "ABSTAIN_NEW_SHIP_BASE_COMPARISON_UNQUALIFIED"
    assert r["one_newly_visible_ship_template_compared"] is False


def test_nonmatching_new_ship_is_not_reclassified_to_a_match():
    r = paired_template_specificity(
        candidate(new_status="OBSERVED_HULL_AND_ENGINE_MISMATCH"),
        baseline(matched=0, missed=1),
    )
    assert r["paired_observational_category"] == (
        "NEW_SHIP_DOES_NOT_FULLY_MATCH_NO_PERSISTENT_SHIPS_MATCH"
    )
    assert not r["new_ship_matches_full_prior_base_template"]


def test_nonappearance_window_never_becomes_a_new_ship_positive():
    r = paired_template_specificity(
        candidate(new_status="NO_NEW_OWN_CURRENT_IDENTITY", n=0), baseline(n=0),
    )
    assert r["paired_observational_category"] == "ABSTAIN_NOT_EXACTLY_ONE_APPEARING_SHIP"
    assert not r["one_newly_visible_ship_template_compared"]


@pytest.mark.parametrize("change", [
    "inconsistent_appearance_count", "causal_promotion", "negative_count",
    "unbalanced_comparisons", "unavailable_enum", "invalid_bool_count",
    "inconsistent_untyped", "unsupported_reference_enum",
])
def test_malformed_source_summary_fails_closed(change):
    new, ref = candidate(), baseline()
    if change == "inconsistent_appearance_count":
        ref["newly_visible_owned_ship_identity_count"] = 2
    elif change == "causal_promotion":
        new["host_causal_verified"] = True
    elif change == "negative_count":
        ref["matches_before_base_hull_and_engine"] = -1
    elif change == "unbalanced_comparisons":
        ref["typed_stable_ship_base_template_comparisons"] = 3
    elif change == "unavailable_enum":
        new["before_current_base_vs_new_ship"] = "HOST_VERIFIED_BUILD"
    elif change == "invalid_bool_count":
        ref["typed_stable_ship_base_template_comparisons"] = True
    elif change == "inconsistent_untyped":
        ref["stable_ships_with_untyped_hull_or_engine"] = 1
    elif change == "unsupported_reference_enum":
        ref["status"] = "HOST_ORDERS_ACCEPTED"
    with pytest.raises(ValueError):
        paired_template_specificity(new, ref)


def test_frozen_public_reader_and_six_game_survey_include_paired_noncausal_category(tmp_path):
    index, cohort, archives = make_fixture(tmp_path)
    source = archives / "game-510234.zip"
    with zipfile.ZipFile(source) as z:
        blobs = {info.filename: z.read(info) for info in z.infolist()}
    for turn in (7, 8):
        name = f"player2-turn{turn}.trn"
        row = json.loads(blobs[name])
        row["starbases"][0]["buildhullid"] = 7
        row["starbases"][0]["buildengineid"] = 2
        row["ships"][0]["hullid"] = 8  # persistent ship DOES NOT match base
        row["ships"][0]["engineid"] = 2
        if turn == 8:
            row["ships"].append({
                "id": 42, "ownerid": 2, "infoturn": 8,
                "hullid": 7, "engineid": 2,
                "secret": "DO_NOT_PUBLISH_PRIVATE_OBJECT",
            })
        blobs[name] = json.dumps(row).encode()
    with zipfile.ZipFile(source, "w") as z:
        for name, blob in blobs.items():
            z.writestr(name, blob)

    report = survey_frozen_public_ppq(
        feature_index=index, frozen_cohort=cohort, archive_dir=archives,
        player_slot=2, first_archive_turn=7,
        max_pairs_per_game=3, max_accepted_per_game=1,
    )
    categories = report["exploratory_paired_template_specificity_categories"]
    assert categories == {"NEW_SHIP_MATCHES_BASE_NONE_OF_PERSISTENT_SHIPS_MATCH": 1}
    assert report["paired_categories_are_iid_independent_or_host_causal"] is False
    window = report["by_game"][0]["exploratory_ship_appearance_windows"][0]
    paired = window["paired_new_and_existing_ship_template_specificity"]
    assert paired["same_window_persistent_ship_comparison_count"] == 1
    assert paired["same_window_persistent_ship_template_mismatch_count"] == 1
    assert paired["same_window_persistent_ship_template_match_count"] == 0
    assert paired["host_causal_verified"] is False
    encoded = json.dumps(report)
    assert "DO_NOT_PUBLISH_PRIVATE_OBJECT" not in encoded
    assert '"id": 42' not in encoded
    assert '"hullid": 7' not in encoded
    assert not report["ship_appearance_is_construction_verified"]
