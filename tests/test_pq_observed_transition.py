"""Strict public PPQ owner-current identity transition signatures."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from planets_lab.corpus.pq_observed_transition import (
    SCHEMA, observed_owned_transition_signature,
)
from test_pq_window_field_sufficiency import make_fixture, report


def one(turn, *, ship_ids=(1, 2), base_id=20):
    return {
        "planets": [
            {"id": 20, "ownerid": 2, "infoturn": turn,
             "name": "SECRET PLANET", "megacredits": 1234},
            {"id": 30, "ownerid": 3, "infoturn": turn},
        ],
        "starbases": [
            {"planetid": base_id, "infoturn": turn,
             "buildhullid": 44, "private": "SECRET QUEUE"},
        ],
        "ships": [
            {"id": sid, "ownerid": 2, "infoturn": turn,
             "friendlycode": "SECRET CODE"} for sid in ship_ids
        ] + [{"id": 99, "ownerid": 3, "infoturn": turn}],
    }


def check(before, after):
    return observed_owned_transition_signature(
        before, after, perspective=2, before_turn=7, after_turn=8,
    )


def test_identity_intersection_is_a_view_not_build_proof():
    before = one(7, ship_ids=(1, 2))
    after = one(8, ship_ids=(2, 3))
    x = check(before, after)
    assert x["schema"] == SCHEMA
    assert x["status"] == "OBSERVED_OWNER_CURRENT_IDENTITY_INTERSECTION_ONLY"
    ships = x["entity_signatures"]["ships"]
    assert ships["before"]["fresh_owned_typed_rows"] == 2
    assert ships["after"]["fresh_owned_typed_rows"] == 2
    assert ships["observed_in_both"] == 1
    assert ships["newly_visible_owned_fresh_ids"] == 1
    assert ships["no_longer_visible_owned_fresh_ids"] == 1
    bases = x["entity_signatures"]["starbases"]
    assert bases["observed_in_both"] == 1
    assert bases["newly_visible_owned_fresh_ids"] == 0
    assert x["entity_signatures"]["planets"]["observed_in_both"] == 1
    assert all(
        x[key] is False for key in (
            "owner_current_views_are_globally_complete",
            "appearance_is_ship_construction_verified",
            "disappearance_is_ship_loss_verified",
            "queue_and_warehouse_after_before_verified",
            "owner_pp_verified", "accepted_host_orders_verified",
            "nuhost_phase_order_verified", "host_causal_verified",
            "private_entity_fields_emitted",
        )
    )
    payload = json.dumps(x)
    for forbidden in ("SECRET", "friendlycode", "megacredits", '"44"', '"99"'):
        assert forbidden not in payload


def test_new_ship_contact_without_own_current_info_cannot_be_a_build():
    before = one(7)
    after = one(8, ship_ids=(1, 2, 3))
    after["ships"][2]["infoturn"] = 7
    x = check(before, after)
    ships = x["entity_signatures"]["ships"]
    assert ships["after"]["fresh_owned_typed_rows"] == 2
    assert ships["newly_visible_owned_fresh_ids"] == 0
    assert ships["after"]["unqualified_rows"] == 2


@pytest.mark.parametrize("bad", ["duplicate_ship", "duplicate_planet", "duplicate_base", "missing_ships",
                                 "missing_starbases", "bool_ship_id", "absent_freshness"])
def test_ambiguous_owner_current_source_never_proves_host_events(bad):
    before, after = one(7), one(8)
    if bad == "duplicate_ship":
        after["ships"].append(deepcopy(after["ships"][0]))
    elif bad == "duplicate_planet":
        after["planets"].append(deepcopy(after["planets"][0]))
    elif bad == "duplicate_base":
        after["starbases"].append(deepcopy(after["starbases"][0]))
    elif bad == "missing_ships":
        after.pop("ships")
    elif bad == "missing_starbases":
        after.pop("starbases")
    elif bad == "bool_ship_id":
        after["ships"][0]["id"] = True
    elif bad == "absent_freshness":
        after["starbases"][0].pop("infoturn")
    result = check(before, after)
    assert not result["host_causal_verified"]
    assert not result["appearance_is_ship_construction_verified"]
    assert not result["owner_current_views_are_globally_complete"]
    if bad in ("duplicate_ship", "duplicate_planet", "duplicate_base",
               "missing_ships", "missing_starbases"):
        assert result["status"] == "ABSTAIN_AMBIGUOUS_OR_MISSING_SOURCE_ARRAYS"
    elif bad == "absent_freshness":
        assert result["entity_signatures"]["starbases"]["after"]["fresh_owned_typed_rows"] == 0
    else:
        assert result["entity_signatures"]["ships"]["after"]["unqualified_rows"] >= 1


@pytest.mark.parametrize("before_turn,after_turn", [(7, 7), (7, 10), (True, 8), (-1, 0)])
def test_untrusted_turn_boundary_rejected(before_turn, after_turn):
    with pytest.raises(ValueError):
        observed_owned_transition_signature(
            one(7), one(8), perspective=2,
            before_turn=before_turn, after_turn=after_turn,
        )


def test_existing_two_member_archival_pipeline_includes_strict_observation_signature(tmp_path):
    paths = make_fixture(tmp_path)
    value = report(paths)
    signature = value["observed_owner_transition"]
    assert signature["schema"] == SCHEMA
    assert signature["status"] == "OBSERVED_OWNER_CURRENT_IDENTITY_INTERSECTION_ONLY"
    assert signature["entity_signatures"]["starbases"]["observed_in_both"] == 1
    assert signature["entity_signatures"]["ships"]["observed_in_both"] == 1
    assert signature["entity_signatures"]["ships"]["after"]["fresh_owned_typed_rows"] == 1
    assert signature["appearance_is_ship_construction_verified"] is False
    assert "private@example.com" not in json.dumps(signature)
    assert "SUPER_SECRET_DO_NOT_LEAK" not in json.dumps(signature)
