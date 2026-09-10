from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_cloak_population_audit import (  # noqa: E402
    _cloak_transition,
    _equipment_signature,
    _stable_identity,
)


def _ship(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "ownerid": 5,
        "hullid": 46,
        "engineid": 9,
        "beamid": 2,
        "beams": 4,
        "torpedoid": 6,
        "bays": 0,
        "turn": 11,
        "torps": 4,
        "neutronium": 40,
        "damage": 0,
        "mission": 9,
        "iscloaked": True,
    }
    raw.update(overrides)
    return raw


def test_equipment_signature_ignores_mutable_cargo_ammo_and_damage() -> None:
    before = _ship(torps=4, neutronium=45, damage=0)
    after = _ship(torps=1, neutronium=10, damage=20)
    assert _equipment_signature(before) == _equipment_signature(after)


def test_stable_identity_accepts_same_owner_equipment_and_build_turn() -> None:
    before = _ship(neutronium=45)
    after = _ship(neutronium=40, mission=1, iscloaked=False)
    assert (
        _stable_identity(
            before_owner=5,
            before_raw=before,
            after_owner=5,
            after_raw=after,
        )
        is True
    )


def test_stable_identity_rejects_owner_hull_equipment_or_build_turn_change() -> None:
    before = _ship()
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=3, after_raw=_ship(ownerid=3)) is False
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=5, after_raw=_ship(hullid=47)) is False
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=5, after_raw=_ship(beamid=6)) is False
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=5, after_raw=_ship(turn=12)) is False


def test_stable_identity_fails_closed_when_identity_field_is_missing() -> None:
    before = _ship()
    after = _ship()
    del after["engineid"]
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=5, after_raw=after) is None
    assert _stable_identity(before_owner=5, before_raw=before, after_owner=None, after_raw=None) is None


def test_cloak_transition_preserves_true_false_and_unknown() -> None:
    assert _cloak_transition(True, True) == "true_to_true"
    assert _cloak_transition(True, False) == "true_to_false"
    assert _cloak_transition(False, True) == "false_to_true"
    assert _cloak_transition(False, False) == "false_to_false"
    assert _cloak_transition(True, None) == "true_to_unknown"
