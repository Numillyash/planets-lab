from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost

import combat_host_post_capture_special_movement_audit as module
from combat_host_post_capture_special_movement_audit import (
    _capture_ship_rows,
    _simulate_special_subject,
    _special_movement_kind,
)


def _specs() -> NuStaticSpecs:
    return NuStaticSpecs(
        hulls={
            16: HullSpec(
                id=16,
                name="Tower",
                tech_level=1,
                mass=100,
                cargo_capacity=100,
                fuel_tank=300,
                crew=10,
                engine_count=2,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            ),
            17: HullSpec(
                id=17,
                name="Ship",
                tech_level=1,
                mass=50,
                cargo_capacity=100,
                fuel_tank=300,
                crew=10,
                engine_count=2,
                beam_count=0,
                torpedo_launcher_count=0,
                fighter_bay_count=0,
                can_cloak=False,
                cost=ResourceCost(),
            ),
        },
        engines={
            9: EngineSpec(
                id=9,
                name="Transwarp",
                tech_level=9,
                cost=ResourceCost(),
                warp_fuel_factors=(0,) + (10_000,) * 9,
            )
        },
    )


def _raw(
    ship_id: int,
    owner_id: int,
    *,
    hull_id: int = 17,
    x: int = 100,
    target_x: int = 100,
    warp: int = 0,
    mission: int = 0,
    mission_target: int = 0,
    fuel: int = 100,
) -> dict[str, object]:
    return {
        "id": ship_id,
        "ownerid": owner_id,
        "hullid": hull_id,
        "x": x,
        "y": 100,
        "engineid": 9,
        "targetx": target_x,
        "targety": 100,
        "warp": warp,
        "mission": mission,
        "mission1target": mission_target,
        "enemy": 0,
        "friendlycode": "abc",
        "neutronium": fuel,
        "duranium": 0,
        "tritanium": 0,
        "molybdenum": 0,
        "supplies": 0,
        "clans": 0,
        "megacredits": 0,
        "beams": 0,
        "torps": 0,
        "bays": 0,
        "ammo": 0,
        "damage": 0,
        "crew": 10,
    }


def test_special_movement_kind() -> None:
    assert _special_movement_kind({"mission": 6}) == "tow"
    assert _special_movement_kind({"mission": 7}) == "intercept"
    assert _special_movement_kind({"mission": 3}) is None


def test_capture_ship_rows_excludes_planet_continuations() -> None:
    rows = _capture_ship_rows(
        {
            "examples": [
                {"status": "capture_continuation", "current_opponent_is_planet": False},
                {"status": "capture_continuation", "current_opponent_is_planet": True},
                {"status": "other", "current_opponent_is_planet": False},
            ]
        }
    )

    assert len(rows) == 1


def test_tow_subject_pipeline_reaches_factual_site(monkeypatch) -> None:
    monkeypatch.setattr(module, "_foreign_mine_route_risk", lambda **kwargs: None)

    tower = _raw(
        10,
        1,
        hull_id=16,
        x=100,
        target_x=110,
        warp=9,
        mission=6,
        mission_target=20,
        fuel=100,
    )
    target = _raw(20, 2, x=100, target_x=100, warp=0, fuel=0)
    owner_rows = {10: (1, tower), 20: (2, target)}

    result = _simulate_special_subject(
        game_id=1,
        battle_turn=5,
        site=(110, 100),
        subject_id=10,
        subject_owner_id=1,
        subject_raw=tower,
        owner_rows=owner_rows,
        specs=_specs(),
        planets=(),
        warp_wells_enabled=False,
        eligible_warp_well_planet_ids=frozenset(),
        races={1: 1, 2: 2},
        mine_context=None,
    )

    assert result["status"] == "exact"
    assert result["movement_kind"] == "tow"
    assert result["predicted_position"] == [110, 100]


def test_intercept_subject_pipeline_reaches_moved_target(monkeypatch) -> None:
    monkeypatch.setattr(module, "_foreign_mine_route_risk", lambda **kwargs: None)

    interceptor = _raw(
        10,
        1,
        x=100,
        target_x=100,
        warp=9,
        mission=7,
        mission_target=20,
        fuel=100,
    )
    target = _raw(
        20,
        2,
        x=110,
        target_x=120,
        warp=9,
        mission=0,
        fuel=100,
    )
    owner_rows = {10: (1, interceptor), 20: (2, target)}

    result = _simulate_special_subject(
        game_id=1,
        battle_turn=5,
        site=(120, 100),
        subject_id=10,
        subject_owner_id=1,
        subject_raw=interceptor,
        owner_rows=owner_rows,
        specs=_specs(),
        planets=(),
        warp_wells_enabled=False,
        eligible_warp_well_planet_ids=frozenset(),
        races={1: 1, 2: 2},
        mine_context=None,
    )

    assert result["status"] == "exact"
    assert result["movement_kind"] == "intercept"
    assert result["predicted_position"] == [120, 100]
