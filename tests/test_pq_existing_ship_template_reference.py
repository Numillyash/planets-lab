"""Existing-ship observational reference prevents overinterpreting 17/17 ship matches."""
from __future__ import annotations

import json
import zipfile
from copy import deepcopy

import pytest

from planets_lab.corpus.pq_existing_ship_template_reference import (
    SCHEMA, existing_ship_template_reference,
)
from planets_lab.corpus.pq_control_multigame_observation import survey_frozen_public_ppq
from test_pq_window_field_sufficiency import make_fixture


def pair(*, new=True):
    before = {
        "player": {"id": 2, "secret": "PRIVATE_PLAYER"},
        "planets": [{"id": 20, "ownerid": 2, "infoturn": 7}],
        "starbases": [{"planetid": 20, "infoturn": 7,
                       "buildhullid": 7, "buildengineid": 2,
                       "secret": "PRIVATE_ACCEPTED_ORDER"}],
        "ships": [
            {"id": 10, "ownerid": 2, "infoturn": 7,
             "hullid": 7, "engineid": 2, "code": "SECRET_SHIP"},
            {"id": 11, "ownerid": 2, "infoturn": 7,
             "hullid": 8, "engineid": 2},
        ],
    }
    after = deepcopy(before)
    after["planets"][0]["infoturn"] = 8
    after["starbases"][0]["infoturn"] = 8
    for ship in after["ships"]:
        ship["infoturn"] = 8
    if new:
        after["ships"].append({
            "id": 12, "ownerid": 2, "infoturn": 8,
            "hullid": 7, "engineid": 2, "secret": "SECRET_NEW",
        })
    return before, after


def test_persistent_reference_matches_and_mismatches_without_build_claim():
    b,a = pair()
    o = existing_ship_template_reference(
        b,a,perspective=2,embedded_before=7,embedded_after=8,
    )
    assert o["schema"] == SCHEMA
    assert o["stratum"] == "WINDOW_WITH_NEWLY_VISIBLE_OWN_SHIP"
    assert o["stable_owned_ship_id_intersection_count"] == 2
    assert o["typed_stable_ship_base_template_comparisons"] == 2
    assert o["matches_before_base_hull_and_engine"] == 1
    assert o["does_not_match_before_base_hull_and_engine"] == 1
    assert o["newly_visible_owned_ship_identity_count"] == 1
    assert o["status"] == "REFERENCE_TYPED_PERSISTENT_OWNED_SHIPS"
    assert not o["persistent_ships_are_independent_negative_samples"]
    assert not o["host_causal_verified"]
    assert not o["new_ship_is_verified_construction"]
    assert not o["private_ids_or_values_emitted"]
    data = json.dumps(o)
    for bad in ("PRIVATE", "SECRET", "hullid", "engineid", '"12"'):
        assert bad not in data


def test_zero_appearance_windows_provide_descriptive_reference_too():
    b,a = pair(new=False)
    r = existing_ship_template_reference(
        b,a,perspective=2,embedded_before=7,embedded_after=8,
    )
    assert r["stratum"] == "WINDOW_WITHOUT_NEWLY_VISIBLE_OWN_SHIP"
    assert r["matches_before_base_hull_and_engine"] == 1
    assert r["typed_stable_ship_base_template_comparisons"] == 2
    assert r["newly_visible_owned_ship_identity_count"] == 0


@pytest.mark.parametrize("change,expected", [
    ("missing", "ABSTAIN_SOURCE_ARRAY_OR_SHIP_ID_AMBIGUOUS"),
    ("duplicate_ship", "ABSTAIN_SOURCE_ARRAY_OR_SHIP_ID_AMBIGUOUS"),
    ("duplicate_base", "ABSTAIN_NO_UNIQUE_CURRENT_BASE"),
    ("stale_base", "ABSTAIN_NO_UNIQUE_CURRENT_BASE"),
    ("no_reference", "ABSTAIN_NO_PERSISTENT_OWNED_SHIP_REFERENCE"),
    ("base_engine_none", "ABSTAIN_BASE_TEMPLATE_UNTYPED"),
    ("prior_ship_untyped", "ABSTAIN_NO_TYPED_PERSISTENT_SHIP_SPECS"),
])
def test_incomplete_source_produces_explicit_refusal(change, expected):
    b,a = pair()
    if change == "missing":
        b.pop("ships")
    elif change == "duplicate_ship":
        a["ships"].append(deepcopy(a["ships"][0]))
    elif change == "duplicate_base":
        b["starbases"].append(deepcopy(b["starbases"][0]))
    elif change == "stale_base":
        b["starbases"][0]["infoturn"] = 6
    elif change == "no_reference":
        for ship in a["ships"][:2]:
            ship["infoturn"] = 7
    elif change == "base_engine_none":
        b["starbases"][0]["buildengineid"] = None
    elif change == "prior_ship_untyped":
        for ship in b["ships"]:
            ship.pop("engineid")
    r = existing_ship_template_reference(
        b,a,perspective=2,embedded_before=7,embedded_after=8,
    )
    assert r["status"] == expected
    assert not r["host_causal_verified"]


def test_synthetic_frozen_multigame_aggregate_stratifies_nonindependent_reference(tmp_path):
    idx, cohort, archives = make_fixture(tmp_path)
    path=archives/"game-510234.zip"
    with zipfile.ZipFile(path) as zin:
        rows={x.filename:zin.read(x) for x in zin.infolist()}
    for turn in (7,8):
        name=f"player2-turn{turn}.trn"
        payload=json.loads(rows[name])
        payload["starbases"][0]["buildengineid"]=2
        payload["ships"][0]["engineid"]=2
        if turn==8:
            payload["ships"].append({
                "id": 44, "ownerid": 2, "infoturn": 8,
                "hullid": 7, "engineid": 2,
                "secret": "DO_NOT_EXPORT_SOURCE_VALUES",
            })
        rows[name]=json.dumps(payload).encode()
    with zipfile.ZipFile(path,"w") as zout:
        for name,body in rows.items(): zout.writestr(name,body)
    result=survey_frozen_public_ppq(
        feature_index=idx, frozen_cohort=cohort, archive_dir=archives,
        player_slot=2, first_archive_turn=7,
        max_pairs_per_game=2, max_accepted_per_game=1,
    )
    assert result["owner_current_source_qualified_pairs"]==1
    assert result["exploratory_before_base_template_status_counts"] == {
        "OBSERVED_BEFORE_BASE_HULL_ENGINE_MATCH": 1,
    }
    ref=result["existing_ship_template_reference_by_stratum"][
        "WINDOW_WITH_NEWLY_VISIBLE_OWN_SHIP"
    ]
    assert ref["windows"] == 1
    assert ref["reference_comparisons"] == 1
    assert ref["matching_preexisting_ship_templates"] == 1
    assert ref["nonmatching_preexisting_ship_templates"] == 0
    assert not result["existing_ship_reference_is_independent_negative_control"]
    assert "DO_NOT_EXPORT_SOURCE_VALUES" not in json.dumps(result)
    assert not result["ship_appearance_is_construction_verified"]
