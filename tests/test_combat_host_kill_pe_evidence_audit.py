from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_kill_pe_evidence_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_kill_pe_evidence_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ship_aligned": True,
        "planet_aligned": True,
        "ship_owner": 1,
        "planet_owner": 2,
        "planet_fc": "abc",
        "enemy": 0,
        "mission": 3,
    }
    row.update(overrides)
    return row


def test_zero_enemy_nonhostile_planet_is_kill_candidate_slice() -> None:
    assert audit._classify_causal_row(_row()) == "zero_enemy_nonhostile_planet"


def test_att_and_nuk_are_excluded_as_planet_initiated_candidates() -> None:
    assert audit._classify_causal_row(_row(planet_fc="att")) == "planet_attack_fc"
    assert audit._classify_causal_row(_row(planet_fc="nuk")) == "planet_attack_fc"


def test_enemy_matching_planet_owner_is_separate_pe_evidence_slice() -> None:
    assert (
        audit._classify_causal_row(_row(enemy=2))
        == "enemy_matches_planet_owner_nonhostile_planet"
    )
    assert audit._classify_causal_row(_row(enemy=7)) == "enemy_other_nonhostile_planet"


def test_scope_reports_mission_ids_per_causal_slice() -> None:
    rows = [
        _row(mission=3),
        _row(mission=3),
        _row(mission=7, enemy=2),
        _row(mission=4, enemy=9),
    ]
    scope = audit._scope(rows, example_limit=10)
    assert scope["zero_enemy_nonhostile_mission_ids"] == {"3": 2}
    assert scope["enemy_matches_planet_owner_mission_ids"] == {"7": 1}
    assert scope["enemy_other_nonhostile_mission_ids"] == {"4": 1}
