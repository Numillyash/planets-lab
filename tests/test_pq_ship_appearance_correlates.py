"""Noncausal starbase template/PP-direction observations from synthetic snapshots."""
from __future__ import annotations

import json
import zipfile
from copy import deepcopy

import pytest

from planets_lab.corpus.pq_ship_appearance_correlates import (
    SCHEMA, appearance_correlates,
)
from planets_lab.corpus.pq_control_multigame_observation import survey_frozen_public_ppq
from test_pq_window_field_sufficiency import make_fixture


def fixture():
    before = {
        "player": {"id": 2, "prioritypoints": 4, "secret": "SENSITIVE_PP_VALUE"},
        "ships": [{"id": 1, "ownerid": 2, "infoturn": 7}],
        "planets": [{"id": 20, "ownerid": 2, "infoturn": 7}],
        "starbases": [{
            "planetid": 20, "infoturn": 7,
            "buildhullid": 8, "buildengineid": 2,
            "raworders": "SECRET_ORDER",
        }],
    }
    after = {
        "player": {"id": 2, "prioritypoints": 2, "secret": "SENSITIVE_PP_VALUE"},
        "ships": [
            {"id": 1, "ownerid": 2, "infoturn": 8},
            {"id": 7, "ownerid": 2, "infoturn": 8,
             "hullid": 8, "engineid": 2, "secret": "SECRET_SHIP_CODE"},
        ],
        "planets": [{"id": 20, "ownerid": 2, "infoturn": 8}],
        "starbases": [{"planetid": 20, "infoturn": 8}],
    }
    return before, after


def check(before, after):
    return appearance_correlates(
        before, after, perspective=2, embedded_before=7, embedded_after=8,
    )


def test_one_base_match_and_decreased_pp_are_observational_not_build_proof():
    b,a = fixture()
    x = check(b,a)
    assert x["schema"] == SCHEMA
    assert x["newly_visible_owned_current_ship_count"] == 1
    assert x["before_current_base_vs_new_ship"] == "OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH"
    assert x["observed_prioritypoints_trend"] == "PP_DECREASED"
    assert x["same_source_window_posthoc_exploratory"]
    for flag in (
        "before_base_build_fields_are_accepted_orders",
        "hull_engine_match_proves_construction",
        "pp_delta_proves_build_spend",
        "all_own_ship_identities_independently_complete",
        "warehouse_and_build_resources_independently_complete",
        "host_accepted_orders_verified",
        "host_causal_verified", "raw_ids_values_or_orders_emitted",
    ):
        assert x[flag] is False
    encoded = json.dumps(x)
    for secret in ("SENSITIVE", "SECRET", "raworders", "id\": 7", "engineid"):
        assert secret not in encoded


@pytest.mark.parametrize("change,expected", (
    ("hull_only", "OBSERVED_HULL_ONLY_ENGINE_MISMATCH"),
    ("engine_only", "OBSERVED_ENGINE_ONLY_HULL_MISMATCH"),
    ("neither", "OBSERVED_HULL_AND_ENGINE_MISMATCH"),
    ("unknown_base_engine", "ABSTAIN_BUILD_TEMPLATE_FIELD_NOT_TYPED_POSITIVE"),
    ("no_current_base", "ABSTAIN_NO_UNIQUE_CURRENT_BASE"),
    ("extra_other_visible_base", "ABSTAIN_NO_UNIQUE_CURRENT_BASE"),
    ("two_new_ships", "ABSTAIN_MULTIPLE_APPEARANCES"),
    ("duplicate_ship", "ABSTAIN_UNQUALIFIED_ARCHIVE_SOURCE"),
    ("missing_ship_array", "ABSTAIN_UNQUALIFIED_ARCHIVE_SOURCE"),
))
def test_observational_mismatches_and_missing_sources_fail_closed(change,expected):
    b,a = fixture()
    if change == "hull_only":
        a["ships"][1]["engineid"] = 3
    elif change == "engine_only":
        a["ships"][1]["hullid"] = 9
    elif change == "neither":
        a["ships"][1]["hullid"] = 9
        a["ships"][1]["engineid"] = 3
    elif change == "unknown_base_engine":
        b["starbases"][0]["buildengineid"] = None
    elif change == "no_current_base":
        b["starbases"][0]["infoturn"] = 6
    elif change == "extra_other_visible_base":
        b["starbases"].append({"planetid": 30, "infoturn": 7})
    elif change == "two_new_ships":
        a["ships"].append({"id": 9, "ownerid": 2, "infoturn": 8, "hullid": 8})
    elif change == "duplicate_ship":
        a["ships"].append(deepcopy(a["ships"][1]))
    elif change == "missing_ship_array":
        b.pop("ships")
    assert check(b,a)["before_current_base_vs_new_ship"] == expected


@pytest.mark.parametrize("change,expected", (
    ("same", "PP_UNCHANGED"),
    ("increase", "PP_INCREASED"),
    ("missing", "UNKNOWN_PRIORITYPOINTS_SOURCE"),
    ("bool", "UNKNOWN_PRIORITYPOINTS_SOURCE"),
    ("mismatch_player", "ABSTAIN_PLAYER_IDENTITY"),
))
def test_prioritypoint_direction_never_emits_raw_values(change,expected):
    b,a = fixture()
    if change == "same":
        a["player"]["prioritypoints"] = 4
    elif change == "increase":
        a["player"]["prioritypoints"] = 9
    elif change == "missing":
        a["player"].pop("prioritypoints")
    elif change == "bool":
        a["player"]["prioritypoints"] = True
    else:
        a["player"]["id"] = 3
    assert check(b,a)["observed_prioritypoints_trend"] == expected


def test_no_new_owned_ship_does_not_report_a_build_template():
    b,a=fixture()
    a["ships"].pop()
    r=check(b,a)
    assert r["before_current_base_vs_new_ship"]=="NO_NEW_OWN_CURRENT_IDENTITY"
    assert r["newly_visible_owned_current_ship_count"] == 0


@pytest.mark.parametrize("bad", [
    {"perspective": True, "embedded_before": 7, "embedded_after": 8},
    {"perspective": 0, "embedded_before": 7, "embedded_after": 8},
    {"perspective": 2, "embedded_before": 7, "embedded_after": 10},
])
def test_invalid_embedded_turns_or_player_rejected(bad):
    b,a=fixture()
    with pytest.raises(ValueError):
        appearance_correlates(b,a,**bad)


def test_real_pipeline_counts_only_categorical_observational_candidate(tmp_path):
    idx, cohort, root = make_fixture(tmp_path)
    archive = root / "game-510234.zip"
    with zipfile.ZipFile(archive) as raw:
        members={entry.filename:raw.read(entry) for entry in raw.infolist()}
    for turn in (7,8):
        name=f"player2-turn{turn}.trn"
        d=json.loads(members[name])
        d["player"]["prioritypoints"] = 4 if turn==7 else 2
        d["starbases"][0]["buildhullid"] = 8
        d["starbases"][0]["buildengineid"] = 2
        if turn==8:
            d["ships"].append({
                "id": 7, "ownerid": 2, "infoturn": 8,
                "hullid": 8, "engineid": 2, "secret": "NEVER_PUBLIC",
            })
        members[name]=json.dumps(d).encode()
    with zipfile.ZipFile(archive,"w") as out:
        for name, data in members.items(): out.writestr(name,data)
    report=survey_frozen_public_ppq(
        feature_index=idx, frozen_cohort=cohort, archive_dir=root,
        player_slot=2, first_archive_turn=7,
        max_pairs_per_game=4, max_accepted_per_game=2,
    )
    assert report["exploratory_ship_appearance_window_count"] == 1
    assert report["exploratory_before_base_template_status_counts"] == {
        "OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH": 1,
    }
    assert report["exploratory_prioritypoints_direction_counts"] == {
        "PP_DECREASED": 1,
    }
    case=report["by_game"][0]["exploratory_ship_appearance_windows"][0]
    assert case["observed_before_base_template_and_pp"]["host_causal_verified"] is False
    assert case["observed_before_base_template_and_pp"]["hull_engine_match_proves_construction"] is False
    serialized=json.dumps(report)
    assert "NEVER_PUBLIC" not in serialized
    assert '"id": 7' not in serialized
    assert not report["ship_appearance_is_construction_verified"]
