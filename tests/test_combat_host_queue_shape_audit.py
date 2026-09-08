from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_queue_shape_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_queue_shape_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def _ship(object_id: int, owner_id: int) -> dict[str, object]:
    return {
        "object_id": object_id,
        "hull_id": 10,
        "owner_id": owner_id,
        "kind": "ship",
    }


def _planet(object_id: int, owner_id: int) -> dict[str, object]:
    return {
        "object_id": object_id,
        "hull_id": 0,
        "owner_id": owner_id,
        "kind": "planet",
    }


def _vcr(
    vcr_id: int,
    shape: str,
    left: dict[str, object],
    right: dict[str, object],
) -> dict[str, object]:
    return {
        "vcr_id": vcr_id,
        "shape": shape,
        "sides": {"left": left, "right": right},
    }


def test_ship_combats_before_planet_has_no_phase_violation() -> None:
    queue = [
        _vcr(10, "ship_vs_ship", _ship(1, 1), _ship(2, 2)),
        _vcr(11, "ship_vs_ship", _ship(1, 1), _ship(3, 3)),
        _vcr(12, "ship_vs_planet", _ship(1, 1), _planet(50, 2)),
    ]

    result = audit._site_summary(queue)

    assert result["profile"] == "SSP"
    assert result["phase_order_violation"] is False
    assert result["ship_count"] == 3
    assert result["planet_count"] == 1
    assert result["max_ship_appearances"] == 3


def test_ship_combat_after_planet_is_phase_violation() -> None:
    queue = [
        _vcr(10, "ship_vs_planet", _ship(1, 1), _planet(50, 2)),
        _vcr(11, "ship_vs_ship", _ship(1, 1), _ship(2, 2)),
    ]

    result = audit._site_summary(queue)

    assert result["profile"] == "PS"
    assert result["phase_order_violation"] is True


def test_same_ship_pair_can_be_counted_repeatedly_without_changing_identity() -> None:
    queue = [
        _vcr(1, "ship_vs_ship", _ship(10, 1), _ship(20, 2)),
        _vcr(2, "ship_vs_ship", _ship(20, 3), _ship(10, 1)),
        _vcr(3, "ship_vs_ship", _ship(10, 1), _ship(20, 3)),
    ]

    result = audit._site_summary(queue)

    assert result["repeated_ship_pairs"] == 1
    assert result["max_pair_fights"] == 3
    assert result["pairs_over_two_fights"] == 1


def test_scope_keeps_queue_shape_counts() -> None:
    sites = [
        {
            "summary": audit._site_summary(
                [_vcr(1, "ship_vs_ship", _ship(1, 1), _ship(2, 2))]
            )
        },
        {
            "summary": audit._site_summary(
                [
                    _vcr(2, "ship_vs_ship", _ship(3, 1), _ship(4, 2)),
                    _vcr(3, "ship_vs_planet", _ship(3, 1), _planet(50, 2)),
                ]
            )
        },
    ]

    scope = audit._scope(sites)

    assert scope["sites"] == 2
    assert scope["multi_vcr_sites"] == 1
    assert scope["ship_only_sites"] == 1
    assert scope["planet_phase_sites"] == 1
    assert scope["phase_order_violations"] == 0
    assert scope["queue_lengths"] == {"1": 1, "2": 1}
    assert scope["battle_shapes"] == {"ship_vs_ship": 2, "ship_vs_planet": 1}
