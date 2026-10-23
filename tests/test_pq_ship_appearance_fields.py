"""Strict archived field presence audit of *observed* own-ship additions.

All outputs are counts and a fixed list of key names; never source values.
"""
from __future__ import annotations

import json
import zipfile

import pytest

from planets_lab.corpus.pq_ship_appearance_fields import (
    SCHEMA, FIELDS, source_fields_for_ship_appearance,
)
from planets_lab.corpus.pq_window_field_sufficiency import scan_single_pq_window
from planets_lab.corpus.pq_control_multigame_observation import survey_frozen_public_ppq
from test_pq_window_field_sufficiency import make_fixture


def _synthetic_pair():
    b = {
        "player": {"id": 2, "prioritypoints": 7, "savekey": "SECRET_KEY"},
        "planets": [
            {"id": 20, "ownerid": 2, "infoturn": 7,
             "megacredits": 100, "duranium": 3, "name": "SECRET_NAME"},
        ],
        "starbases": [
            {"planetid": 20, "infoturn": 7,
             "buildhullid": 3, "buildengineid": None,
             "hulltechlevel": 8, "secret_order": "SECRET_ORDER"},
        ],
        "ships": [
            {"id": 1, "ownerid": 2, "infoturn": 7, "hullid": 4},
        ],
    }
    a = {
        "player": {"id": 2, "prioritypoints": 8, "savekey": "OTHER_SECRET"},
        "planets": [
            {"id": 20, "ownerid": 2, "infoturn": 8,
             "megacredits": 250, "duranium": None},
        ],
        "starbases": [
            {"planetid": 20, "infoturn": 8, "buildhullid": 5,
             "buildengineid": 2, "hulltechlevel": 8},
        ],
        "ships": [
            {"id": 1, "ownerid": 2, "infoturn": 8, "hullid": 4},
            {"id": 42, "ownerid": 2, "infoturn": 8,
             "hullid": 5, "engineid": 2,
             "friendlycode": "SHOULD_NEVER_LEAK"},
        ],
    }
    return b, a


def evaluate(b, a):
    return source_fields_for_ship_appearance(
        b, a, perspective=2, embedded_before=7, embedded_after=8,
    )


def test_presence_is_not_orders_values_or_build_parity():
    before, after = _synthetic_pair()
    output = evaluate(before, after)
    assert output["schema"] == SCHEMA
    assert output["status"] == "OBSERVED_NEW_OWNED_SHIP_SOURCE_FIELDS"
    assert output["newly_visible_owned_current_ship_ids_count"] == 1
    groups = output["source_field_presence_only"]
    assert groups["before_owned_current_bases"]["selected_source_rows"] == 1
    assert groups["after_owned_current_bases"]["selected_source_rows"] == 1
    assert groups["newly_visible_owned_current_ships"]["selected_source_rows"] == 1
    assert groups["newly_visible_owned_current_ships"]["source_key_status"]["hullid"]["typed_nonnegative_integer_rows"] == 1
    assert groups["before_owned_current_bases"]["source_key_status"]["buildhullid"]["key_present_rows"] == 1
    assert groups["before_owned_current_bases"]["source_key_status"]["buildengineid"]["null_rows"] == 1
    assert groups["after_owned_current_planets"]["source_key_status"]["duranium"]["null_rows"] == 1
    assert groups["before_perspective_player"]["source_key_status"]["prioritypoints"]["typed_nonnegative_integer_rows"] == 1
    for guard in (
        "all_own_ships_independently_complete", "queued_build_command_authenticated",
        "starbase_components_complete", "owner_priority_points_independently_complete",
        "host_orders_accepted_verified", "source_fields_match_causal_build_event",
        "nuhost_build_execution_verified", "private_values_or_ids_emitted",
    ):
        assert output[guard] is False
    text = json.dumps(output)
    for value in ("SECRET", "SHOULD_NEVER_LEAK", "250", "42", "friendlycode", "savekey", "SECRET_NAME"):
        assert value not in text
    assert all(set(group["source_key_status"]) == set(FIELDS[label]) for label,group in (
        ("starbase",groups["after_owned_current_bases"]),
        ("ship",groups["newly_visible_owned_current_ships"]),
        ("planet",groups["before_owned_current_planets"]),
        ("player",groups["after_perspective_player"]),
    ))


def test_stale_new_ship_is_not_current_added_ship():
    b,a = _synthetic_pair()
    a["ships"][1]["infoturn"] = 7
    out=evaluate(b,a)
    assert out["status"] == "NO_NEWLY_VISIBLE_OWNED_SHIP_IN_THIS_WINDOW"
    assert out["newly_visible_owned_current_ship_ids_count"] == 0
    assert out["source_field_presence_only"]["newly_visible_owned_current_ships"]["selected_source_rows"] == 0


def test_missing_fields_do_not_turn_into_negative_factual_warehouse_claims():
    b,a = _synthetic_pair()
    b["starbases"][0].pop("infoturn")
    out = evaluate(b,a)
    assert out["source_field_presence_only"]["before_owned_current_bases"]["selected_source_rows"] == 0
    assert out["starbase_components_complete"] is False
    assert out["owner_priority_points_independently_complete"] is False


def test_missing_array_preserves_abstain_even_if_new_ship_visible():
    b,a = _synthetic_pair()
    b.pop("planets")
    out=evaluate(b,a)
    assert out["status"]=="ABSTAIN_SOURCE_SHAPE_OR_IDENTITY"
    assert "BEFORE_PLANETS_ARRAY_MISSING" in out["missing_or_ambiguous_source"]
    assert out["source_fields_match_causal_build_event"] is False


@pytest.mark.parametrize("args", [
    {"perspective": True, "embedded_before": 7, "embedded_after": 8},
    {"perspective": 51, "embedded_before": 7, "embedded_after": 8},
    {"perspective": 2, "embedded_before": 7, "embedded_after": 10},
    {"perspective": 2, "embedded_before": -1, "embedded_after": 0},
])
def test_source_field_audit_fails_closed_on_identity_boundary(args):
    b,a=_synthetic_pair()
    with pytest.raises(ValueError):
        source_fields_for_ship_appearance(b,a,**args)


def test_two_member_reader_and_multigame_candidate_discovery(tmp_path):
    index, cohort, root = make_fixture(tmp_path)
    file = root / "game-510234.zip"
    with zipfile.ZipFile(file) as z:
        rows = {i.filename:z.read(i) for i in z.infolist()}
    a=json.loads(rows["player2-turn8.trn"])
    a["ships"].append({
        "id": 42, "ownerid": 2, "infoturn": 8,
        "hullid": 5, "friendlycode": "PRIVATE_ORDERS_NEVER_EMIT",
    })
    rows["player2-turn8.trn"]=json.dumps(a).encode()
    with zipfile.ZipFile(file,"w") as z:
        for name,blob in rows.items(): z.writestr(name,blob)
    win=scan_single_pq_window(
        feature_index=index, frozen_cohort=cohort, archive_dir=root,
        game_id=510234, player_id=2, t_before=7,
    )
    assert win["ship_appearance_source_field_audit"]["newly_visible_owned_current_ship_ids_count"]==1
    result=survey_frozen_public_ppq(
        feature_index=index, frozen_cohort=cohort, archive_dir=root,
        player_slot=2, first_archive_turn=7,
        max_pairs_per_game=4, max_accepted_per_game=2,
    )
    assert result["exploratory_ship_appearance_window_count"]==1
    case=result["by_game"][0]["exploratory_ship_appearance_windows"][0]
    assert (case["archive_before_turn"],case["archive_after_turn"])==(7,8)
    assert (case["embedded_before_turn"],case["embedded_after_turn"])==(7,8)
    assert case["newly_visible_owned_fresh_ship_count"]==1
    assert case["selection_type"]=="EXPLORATORY_POSTHOC_OBSERVED_IDENTITY"
    assert case["verified_ship_build"] is False
    assert result["posthoc_window_selection_not_independent_validation"]
    encoded=json.dumps(result)
    assert "PRIVATE_ORDERS_NEVER_EMIT" not in encoded
    assert '"42"' not in encoded
    assert not result["host_causal_verified"]
