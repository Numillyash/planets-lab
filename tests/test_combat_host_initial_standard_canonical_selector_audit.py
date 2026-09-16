from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from planets_lab.rules.combat.selection import ShipCombatSideInput, decide_ship_combat_pair

from combat_host_factual_queue_selection_audit import _decision_projection  # noqa: E402
from combat_host_initial_standard_canonical_selector_audit import (  # noqa: E402
    _matches_legacy,
    canonical_selection_from_projected_rows,
)


def _ship(ship_id: int, owner_id: int, **overrides: object) -> ShipCombatSideInput:
    values: dict[str, object] = {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "mission": 0,
        "primary_enemy": 0,
        "friendly_code": "abc",
        "has_fuel": True,
        "diplomacy_allows_attack": True,
        "harmonic_weapon_modulation_enabled": False,
        "galactic_power_enabled": False,
        "standard_targetable_by_opponent": True,
    }
    values.update(overrides)
    return ShipCombatSideInput(**values)


def _row(
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
    *,
    profile: str = "strict",
) -> dict[str, object]:
    decision = decide_ship_combat_pair(left=left, right=right, same_location=True)
    return {
        "left": {
            "ship_id": left.ship_id,
            "owner_id": left.owner_id,
            "mission": left.mission,
            "enemy": left.primary_enemy,
            "friendlycode": left.friendly_code,
        },
        "right": {
            "ship_id": right.ship_id,
            "owner_id": right.owner_id,
            "mission": right.mission,
            "enemy": right.primary_enemy,
            "friendlycode": right.friendly_code,
        },
        profile: _decision_projection(decision),
    }


def test_projected_row_adapter_uses_production_active_then_target_order() -> None:
    active = _ship(20, 1, mission=3)
    rows = [
        _row(active, _ship(80, 2)),
        _row(active, _ship(40, 3)),
    ]

    selection, error = canonical_selection_from_projected_rows(rows, profile="strict")

    assert error is None
    assert selection is not None
    assert selection.engagement_available is True
    assert selection.active_ship_id == 20
    assert selection.target_ship_id == 40
    assert _matches_legacy(
        selection,
        {"pair": [20, 40], "active_ship_id": 20, "target_ship_id": 40},
    ) is True


def test_projected_row_adapter_preserves_known_blocked_pair() -> None:
    active = _ship(20, 1, mission=3)
    blocked_target = _ship(40, 2, standard_targetable_by_opponent=False)
    eligible_target = _ship(80, 3)
    rows = [
        _row(active, blocked_target),
        _row(active, eligible_target),
    ]

    selection, error = canonical_selection_from_projected_rows(rows, profile="strict")

    assert error is None
    assert selection is not None
    assert selection.engagement_available is True
    assert selection.eligible_pair_count == 1
    assert selection.target_ship_id == 80


def test_projected_row_adapter_reports_malformed_projection() -> None:
    selection, error = canonical_selection_from_projected_rows(
        [{"left": {}, "right": {}, "strict": {}}],
        profile="strict",
    )

    assert selection is None
    assert error is not None
    assert error.startswith("adapter_error:")
