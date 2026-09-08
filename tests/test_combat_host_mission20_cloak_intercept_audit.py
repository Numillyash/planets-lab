from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_mission20_cloak_intercept_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_mission20_cloak_intercept_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_target_signature_classifies_matching_enemy_on_other_owner_target() -> None:
    assert audit._target_signature(
        ship_owner=3,
        enemy=4,
        target_id=50,
        target_owner=4,
    ) == ("positive", "other_owner", "enemy_matches_target_owner")


def test_target_signature_keeps_zero_target_nonsemantic() -> None:
    assert audit._target_signature(
        ship_owner=3,
        enemy=4,
        target_id=0,
        target_owner=None,
    ) == ("zero_or_missing", "not_applicable", "not_applicable")


def test_target_signature_fails_closed_when_target_owner_unknown() -> None:
    assert audit._target_signature(
        ship_owner=3,
        enemy=4,
        target_id=50,
        target_owner=None,
    ) == ("positive", "unresolved", "target_owner_unknown")


def test_scope_aggregates_signature_dimensions() -> None:
    rows = [
        {
            "game_id": 1,
            "owner_race_id": 3,
            "hull_id": 29,
            "target_presence": "positive",
            "target_relation": "other_owner",
            "enemy_relation": "enemy_matches_target_owner",
            "iscloaked": True,
        },
        {
            "game_id": 1,
            "owner_race_id": 3,
            "hull_id": 29,
            "target_presence": "zero_or_missing",
            "target_relation": "not_applicable",
            "enemy_relation": "not_applicable",
            "iscloaked": False,
        },
    ]
    scope = audit._scope(rows)
    assert scope["records"] == 2
    assert scope["games"] == {"1": 2}
    assert scope["owner_races"] == {"3": 2}
    assert scope["owner_hulls"] == {"29": 2}
    assert scope["target_presence"] == {"positive": 1, "zero_or_missing": 1}
    assert scope["target_relation"] == {"not_applicable": 1, "other_owner": 1}
    assert scope["enemy_relation"] == {"enemy_matches_target_owner": 1, "not_applicable": 1}


def test_player_races_reports_conflicting_assignments() -> None:
    class Snapshot:
        def __init__(self, players: list[dict[str, int]]) -> None:
            self.mechanics_payload = {"players": players}

    resolved, conflicts = audit._player_races(
        [
            Snapshot([{"id": 3, "raceid": 3}, {"id": 4, "raceid": 4}]),
            Snapshot([{"id": 3, "raceid": 3}, {"id": 4, "raceid": 5}]),
        ]
    )
    assert resolved == {3: 3}
    assert conflicts == {4: (4, 5)}
