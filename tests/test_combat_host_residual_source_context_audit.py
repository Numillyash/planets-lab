from __future__ import annotations

import importlib.util
from pathlib import Path

from planets_lab.corpus.reconstruction import PerspectiveRecord


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_residual_source_context_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_residual_source_context_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_project_ship_record_is_strictly_allowlisted() -> None:
    projected = audit._project_ship_record(
        {
            "id": 89,
            "ownerid": 5,
            "hullid": 46,
            "friendlycode": "2eC",
            "mission": 7,
            "ammo": 4,
            "name": "private ship name",
            "note": "private note",
            "messages": ["private"],
        }
    )

    assert projected["fields"]["id"] == 89
    assert projected["fields"]["friendlycode"] == "2eC"
    assert projected["fields"]["ammo"] == 4
    assert "name" not in projected["fields"]
    assert "note" not in projected["fields"]
    assert "messages" not in projected["fields"]


def test_snapshot_context_preserves_owner_freshness_and_provenance() -> None:
    owner = PerspectiveRecord(
        player_id=5,
        archive_turn=18,
        embedded_turn=18,
        infoturn=18,
        raw={
            "id": 89,
            "ownerid": 5,
            "hullid": 46,
            "mission": 7,
            "mission1target": 80,
            "enemy": 0,
            "friendlycode": "2eC",
        },
    )
    stale_other = PerspectiveRecord(
        player_id=6,
        archive_turn=18,
        embedded_turn=18,
        infoturn=17,
        raw={
            "id": 89,
            "ownerid": 5,
            "hullid": 46,
            "mission": 1,
        },
    )

    snapshot = audit._snapshot_context(
        (owner, stale_other),
        ship_id=89,
        relative_turn="T-1",
        requested_archive_turn=18,
    )

    assert snapshot["perspective_count"] == 2
    assert snapshot["current_perspective_count"] == 1
    assert snapshot["stale_perspective_count"] == 1
    assert snapshot["current_owner_visible_count"] == 1
    assert snapshot["owner_visible_records"][0]["perspective_player_id"] == 5
    assert snapshot["owner_visible_records"][0]["freshness"] == "current"
    assert snapshot["perspective_provenance"][1]["freshness"] == "stale"


def test_known_field_diff_compares_only_fields_present_on_both_turns() -> None:
    before = {
        "owner_visible_records": [
            {
                "freshness": "current",
                "fields": {"ownerid": 5, "damage": 0, "neutronium": 26},
            }
        ]
    }
    after = {
        "owner_visible_records": [
            {
                "freshness": "current",
                "fields": {"ownerid": 5, "damage": 12, "supplies": 7},
            }
        ]
    }

    diff = audit._known_field_diff(before, after)

    assert diff["status"] == "comparable"
    assert diff["compared_fields"] == ["damage", "ownerid"]
    assert diff["changed"] == {"damage": {"before": 0, "after": 12}}
    assert diff["same_fields"] == ["ownerid"]
    assert diff["before_only"] == ["neutronium"]
    assert diff["after_only"] == ["supplies"]


def test_ship_appearances_keep_vcr_order_location_side_and_provenance() -> None:
    rows = [
        {
            "vcr_id": 13,
            "digest": "a",
            "payload": {
                "id": 13,
                "turn": 19,
                "x": 2565,
                "y": 1729,
                "leftownerid": 6,
                "rightownerid": 5,
                "left": {"objectid": 80, "hullid": 56, "damage": 0},
                "right": {"objectid": 89, "hullid": 46, "damage": 0},
            },
            "provenance": [{"member_player_id": 5}],
        },
        {
            "vcr_id": 20,
            "digest": "b",
            "payload": {
                "id": 20,
                "turn": 19,
                "x": 2600,
                "y": 1800,
                "leftownerid": 5,
                "rightownerid": 4,
                "left": {"objectid": 89, "hullid": 46, "damage": 15},
                "right": {"objectid": 70, "hullid": 30, "damage": 0},
            },
            "provenance": [{"member_player_id": 4}],
        },
    ]

    appearances = audit._ship_appearances(rows, ship_id=89, target_vcr_id=13)

    assert [row["vcr_id"] for row in appearances] == [13, 20]
    assert appearances[0]["relative_to_target"] == "target_vcr"
    assert appearances[0]["side"] == "right"
    assert appearances[1]["relative_to_target"] == "after_target_vcr"
    assert appearances[1]["side"] == "left"
    assert (appearances[1]["x"], appearances[1]["y"]) == (2600, 1800)
    assert appearances[1]["ship_combatant"]["fields"]["damage"] == 15


def test_parse_case_requires_five_positive_integers() -> None:
    case = audit._parse_case("621896:28:67:62:38")
    assert case == audit.AuditCase(621896, 28, 67, 62, 38)
