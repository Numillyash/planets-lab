from __future__ import annotations

import sys
from pathlib import Path

from planets_lab.corpus.reconstruction import PerspectiveRecord

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_super_spy_cloak_context_audit import (  # noqa: E402
    _documented_super_spy_effective_cloak_candidate,
    _planet_ion_pulse_context,
)


def _candidate(**overrides):
    values = {
        "race_id": 3,
        "mission": 9,
        "hull_can_cloak": True,
        "advanced_cloak": False,
        "damage": 0,
        "fuel_before": 37,
        "reference_cost": 5,
        "reference_move_resolved": True,
        "reference_remaining_fuel": 37,
        "prior_iscloaked": True,
        "ion_start_inside": False,
        "planet_ion_pulse_possible": False,
        "loki_start_exposed": False,
        "active_glory_colocated": False,
    }
    values.update(overrides)
    return _documented_super_spy_effective_cloak_candidate(**values)


def _planet_record(*, owner_id: int, defense: int | None) -> PerspectiveRecord:
    raw = {"id": 1, "ownerid": owner_id, "x": 100, "y": 200}
    if defense is not None:
        raw["defense"] = defense
    return PerspectiveRecord(
        player_id=owner_id,
        archive_turn=93,
        embedded_turn=93,
        infoturn=93,
        raw=raw,
    )


def test_documented_super_spy_positive_candidate() -> None:
    state, reason = _candidate()
    assert state is True
    assert reason == "documented_super_spy_ordinary_cloak_supported"


def test_damage_blocks_documented_super_spy_cloak() -> None:
    state, reason = _candidate(damage=1)
    assert state is False
    assert reason == "damage_blocks_cloak"


def test_low_fuel_is_not_promoted_as_effective_cloak() -> None:
    state, reason = _candidate(fuel_before=5)
    assert state is False
    assert reason == "fuel_not_safely_above_reference_cost"


def test_visible_decloak_context_fails_closed() -> None:
    state, reason = _candidate(loki_start_exposed=True)
    assert state is None
    assert reason == "loki_context_present"


def test_planet_ion_pulse_possibility_fails_closed() -> None:
    state, reason = _candidate(planet_ion_pulse_possible=True)
    assert state is None
    assert reason == "planet_ion_pulse_possible"


def test_unresolved_planet_ion_pulse_context_fails_closed() -> None:
    state, reason = _candidate(planet_ion_pulse_possible=None)
    assert state is None
    assert reason == "planet_ion_pulse_context_unresolved"


def test_non_super_spy_prior_cloak_control_is_out_of_scope() -> None:
    state, reason = _candidate(mission=2)
    assert state is None
    assert reason == "outside_super_spy_scope"


def test_advanced_cloak_is_deliberately_unresolved() -> None:
    state, reason = _candidate(advanced_cloak=True)
    assert state is None
    assert reason == "advanced_cloak_unresolved"


def test_foreign_planet_with_30_defense_is_conservative_pulse_risk() -> None:
    record = _planet_record(owner_id=6, defense=30)
    result = _planet_ion_pulse_context(
        planet_groups={(93, 1): (record,)},
        turn=93,
        ship_owner_id=3,
        position=(100, 200),
    )
    assert result["possible"] is True
    assert result["status"] == "possible"


def test_same_owner_planet_is_not_super_spy_pulse_risk() -> None:
    record = _planet_record(owner_id=3, defense=100)
    result = _planet_ion_pulse_context(
        planet_groups={(93, 1): (record,)},
        turn=93,
        ship_owner_id=3,
        position=(100, 200),
    )
    assert result["possible"] is False
    assert result["status"] == "clear"


def test_foreign_planet_unknown_defense_fails_closed() -> None:
    record = _planet_record(owner_id=6, defense=None)
    result = _planet_ion_pulse_context(
        planet_groups={(93, 1): (record,)},
        turn=93,
        ship_owner_id=3,
        position=(100, 200),
    )
    assert result["possible"] is None
    assert result["status"] == "unresolved"
