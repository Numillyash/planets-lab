"""Source-shape audit for planet-linked visible historical starbases."""
from __future__ import annotations

from copy import deepcopy
import json
import zipfile

import pytest

from planets_lab.corpus.pq_starbase_observability import (
    STARBASE_SOURCE_KEYS, starbase_owner_provenance,
)
from test_pq_window_field_sufficiency import make_fixture, report


def snapshot():
    return {
        "planets": [
            {"id": 20, "ownerid": 2, "infoturn": 7, "name": "HIDDEN PLANET"},
            {"id": 30, "ownerid": 3, "infoturn": 7},
        ],
        "starbases": [
            {"planetid": 20, "infoturn": 7, "buildhullid": 8,
             "privatefield": "SECRET SHOULD NOT APPEAR"},
            {"planetid": 30, "infoturn": 7, "ownerid": 3},
        ],
    }


def check(data):
    return starbase_owner_provenance(data, perspective=2, embedded_turn=7)


def test_strict_owner_provenance_via_current_owned_planet_without_base_owner():
    data = snapshot()
    result = check(data)
    assert result["status"] == "BOUNDED_PLANET_LINK_ONLY_NOT_HOST_VERIFIED"
    assert result["owned_planet_linked_base_rows"] == 1
    assert result["fresh_owned_planet_linked_bases"] == 1
    assert result["unresolved_or_ambiguous_base_rows"] == 0
    assert result["owner_conflicts_with_planet"] == 0
    assert result["source_key_presence_counts"]["buildhullid"] == 1
    assert result["source_key_presence_counts"]["infoturn"] == 2
    assert not result["warehouse_and_queue_complete"]
    assert not result["independent_host_owner_freshness_verified"]
    text = json.dumps(result)
    assert "HIDDEN PLANET" not in text and "SECRET SHOULD NOT APPEAR" not in text
    assert "20" not in json.dumps(result["source_key_presence_counts"])


@pytest.mark.parametrize("change,field,expected", [
    ("missing_base_freshness", "linked_owned_planet_bases_without_base_infoturn", 1),
    ("stale_base_freshness", "linked_owned_planet_bases_with_stale_base_infoturn", 1),
    ("explicit_base_owner_conflict", "owner_conflicts_with_planet", 1),
    ("unknown_planet_freshness", "unresolved_or_ambiguous_base_rows", 1),
    ("duplicate_planet_id", "unresolved_or_ambiguous_base_rows", 1),
    ("no_planet_owner", "unresolved_or_ambiguous_base_rows", 1),
    ("boolean_base_planetid", "unresolved_or_ambiguous_base_rows", 1),
])
def test_unknown_contradicted_or_stale_base_not_promoted(change, field, expected):
    data = snapshot()
    base = data["starbases"][0]
    planet = data["planets"][0]
    if change == "missing_base_freshness":
        base.pop("infoturn")
    elif change == "stale_base_freshness":
        base["infoturn"] = 6
    elif change == "explicit_base_owner_conflict":
        base["ownerid"] = 3
    elif change == "unknown_planet_freshness":
        planet.pop("infoturn")
    elif change == "duplicate_planet_id":
        data["planets"].append(deepcopy(planet))
    elif change == "no_planet_owner":
        planet.pop("ownerid")
    elif change == "boolean_base_planetid":
        base["planetid"] = True
    out = check(data)
    assert out[field] == expected
    assert out["fresh_owned_planet_linked_bases"] == 0
    assert out["warehouse_and_queue_complete"] is False


def test_missing_array_preserves_unknown_instead_of_fabricating_no_bases():
    for kind in ("planets", "starbases"):
        data = snapshot()
        data.pop(kind)
        out = check(data)
        assert out["status"] == "ABSTAIN_PLANET_OR_STARBASE_ARRAY_MISSING"
        assert out["unresolved_or_ambiguous_base_rows"] is None
        assert out["source_key_presence_counts"] == {}
        assert out["fresh_owned_planet_linked_bases"] == 0


def test_all_source_field_counts_only_fixed_allowlisted_key_names():
    data = snapshot()
    data["starbases"][0]["email"] = "hidden@secret.invalid"
    data["starbases"][0]["savekey"] = "another-SECRET"
    data["starbases"][0]["buildhullid"] = "a-secret-non-numeric-payload"
    result = check(data)
    assert set(result["source_key_presence_counts"]) == set(STARBASE_SOURCE_KEYS)
    assert result["source_key_presence_counts"]["buildhullid"] == 1
    assert "secret" not in json.dumps(result).lower()
    assert "email" not in json.dumps(result).lower()


def test_two_member_pq_archive_reports_planet_linked_base_safely(tmp_path):
    paths = make_fixture(tmp_path)
    output = report(paths)
    for which in ("before", "after"):
        datum = output["starbase_provenance"][which]
        assert datum["fresh_owned_planet_linked_bases"] == 1
        assert datum["owned_planet_linked_base_rows"] == 1
        assert datum["warehouse_and_queue_complete"] is False
        # Existing direct-base-owner count may be zero if only the
        # planet establishes owner provenance; no silent promotion.
    assert not output["causal_queue_replay_admitted"]


def test_realistic_base_without_infoturn_is_linked_but_not_current(tmp_path):
    paths = make_fixture(tmp_path)
    archive = paths[2] / "game-510234.zip"
    with zipfile.ZipFile(archive) as zin:
        members = {i.filename: zin.read(i) for i in zin.infolist()}
    for t in (7, 8):
        name = f"player2-turn{t}.trn"
        payload = json.loads(members[name])
        payload["starbases"][0].pop("infoturn")
        payload["starbases"][0].pop("ownerid")
        payload["starbases"][0]["private"] = "raw secret"
        members[name] = json.dumps(payload).encode()
    with zipfile.ZipFile(archive, "w") as zout:
        for name, blob in members.items():
            zout.writestr(name, blob)
    data = report(paths)
    assert all(
        data["starbase_provenance"][side][
            "linked_owned_planet_bases_without_base_infoturn"
        ] == 1
        for side in ("before", "after")
    )
    assert all(
        data["starbase_provenance"][side]["fresh_owned_planet_linked_bases"] == 0
        for side in ("before", "after")
    )
    assert "raw secret" not in json.dumps(data)


def test_duplicate_base_on_one_planet_is_ambiguous_not_two_proven_build_sites():
    data = snapshot()
    data["starbases"].append(deepcopy(data["starbases"][0]))
    result = check(data)
    assert result["fresh_owned_planet_linked_bases"] == 0
    assert result["unresolved_or_ambiguous_base_rows"] == 2
    assert result["owned_planet_linked_base_rows"] == 0
