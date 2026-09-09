from __future__ import annotations

import sys
from pathlib import Path

from planets_lab.data import EngineSpec, HullSpec, NuStaticSpecs, ResourceCost

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_normal_movement_position_audit import (  # noqa: E402
    _effective_requested_warp,
    _inbound_transfer_targets,
    _nonzero_transfer_amount,
    _normal_position_prediction,
)


def _specs(*, fuel_factor: int = 10_000) -> NuStaticSpecs:
    hull = HullSpec(
        id=16,
        name="Test Hull",
        tech_level=3,
        mass=60,
        cargo_capacity=200,
        fuel_tank=250,
        crew=6,
        engine_count=1,
        beam_count=0,
        torpedo_launcher_count=0,
        fighter_bay_count=0,
        can_cloak=False,
        cost=ResourceCost(),
    )
    engine = EngineSpec(
        id=9,
        name="Test Engine",
        tech_level=9,
        cost=ResourceCost(),
        warp_fuel_factors=(0,) + (fuel_factor,) * 9,
    )
    return NuStaticSpecs(hulls={16: hull}, engines={9: engine})


def _raw(**changes: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "id": 1,
        "ownerid": 1,
        "hullid": 16,
        "x": 100,
        "y": 100,
        "engineid": 9,
        "beamid": 0,
        "torpedoid": 0,
        "beams": 0,
        "torps": 0,
        "bays": 0,
        "ammo": 0,
        "targetx": 110,
        "targety": 100,
        "warp": 9,
        "mission": 1,
        "mission1target": 0,
        "mission2target": 0,
        "enemy": 0,
        "friendlycode": "abc",
        "neutronium": 100,
        "duranium": 0,
        "tritanium": 0,
        "molybdenum": 0,
        "supplies": 0,
        "clans": 0,
        "megacredits": 0,
        "damage": 0,
        "crew": 6,
        "mass": 60,
    }
    raw.update(changes)
    return raw


def _predict(
    *,
    raw: dict[str, object] | None = None,
    specs: NuStaticSpecs | None = None,
    planets: tuple[tuple[int, int, int], ...] = (),
    warp_wells_enabled: bool | None = False,
    eligible_warp_well_planet_ids: frozenset[int] | None = frozenset(),
    inbound_transfer_targets: frozenset[int] = frozenset(),
    tow_targets: frozenset[int] = frozenset(),
    chunnel_source_sites: frozenset[tuple[int, int]] = frozenset(),
) -> tuple[tuple[int, int] | None, str]:
    return _normal_position_prediction(
        game_id=1,
        ship_id=1,
        owner_id=1,
        raw=raw or _raw(),
        race_id=1,
        specs=specs or _specs(),
        planets=planets,
        warp_wells_enabled=warp_wells_enabled,
        eligible_warp_well_planet_ids=eligible_warp_well_planet_ids,
        inbound_transfer_targets=inbound_transfer_targets,
        tow_targets=tow_targets,
        chunnel_source_sites=chunnel_source_sites,
        sphere=False,
    )


def test_nonzero_transfer_amount_only_uses_payload_amounts() -> None:
    assert _nonzero_transfer_amount({"transfertargetid": 9, "transferneutronium": 0}) is False
    assert _nonzero_transfer_amount({"transferneutronium": 4}) is True
    assert _nonzero_transfer_amount({"transfersupplies": -2}) is True


def test_inbound_transfer_targets_are_collected_from_nonzero_orders() -> None:
    rows = {
        1: (1, {"transfertargetid": 9, "transferneutronium": 5}),
        2: (1, {"transfertargetid": 8, "transferneutronium": 0}),
        3: (2, {"transfertargetid": 7, "transfersupplies": 2}),
    }
    assert _inbound_transfer_targets(rows) == frozenset({7, 9})


def test_effective_warp_keeps_low_damage_without_race_resolution() -> None:
    assert _effective_requested_warp({"warp": 9, "damage": 0}, race_id=None) == (9, None)


def test_effective_warp_uses_strict_raw_damage_cap_only_with_low_supplies() -> None:
    assert _effective_requested_warp(
        {"warp": 9, "damage": 25, "supplies": 0}, race_id=1
    ) == (8, None)
    assert _effective_requested_warp(
        {"warp": 9, "damage": 25, "supplies": 5}, race_id=1
    ) == (None, "damage_repair_can_change_warp")


def test_normal_prediction_reaches_full_waypoint_without_t_state() -> None:
    predicted, reason = _predict()
    assert predicted == (110, 100)
    assert reason == "normal_move"


def test_normal_prediction_uses_host_partial_endpoint_when_fuel_is_sufficient() -> None:
    predicted, reason = _predict(raw=_raw(targetx=300, neutronium=200))
    assert predicted == (181, 100)
    assert reason == "normal_move"


def test_normal_prediction_fails_closed_on_explicit_transfer() -> None:
    predicted, reason = _predict(raw=_raw(transferneutronium=5, transfertargetid=2))
    assert predicted is None
    assert reason == "outbound_transfer"


def test_normal_prediction_does_not_guess_fuel_proration() -> None:
    predicted, reason = _predict(
        raw=_raw(neutronium=0),
        specs=_specs(fuel_factor=1_000_000),
    )
    assert predicted is None
    assert reason == "normal_plan_insufficient_fuel"


def test_moving_intercept_never_falls_through_to_normal_movement() -> None:
    predicted, reason = _predict(raw=_raw(mission=7, mission1target=9))
    assert predicted is None
    assert reason == "intercept_movement"


def test_moving_tow_target_never_falls_through_to_normal_movement() -> None:
    predicted, reason = _predict(tow_targets=frozenset({1}))
    assert predicted is None
    assert reason == "tow_target"


def test_moving_hyp_never_falls_through_to_normal_movement() -> None:
    predicted, reason = _predict(raw=_raw(friendlycode="HYP"))
    assert predicted is None
    assert reason == "hyperjump_movement"


def test_moving_chunnel_source_stack_never_falls_through_to_normal_movement() -> None:
    predicted, reason = _predict(chunnel_source_sites=frozenset({(100, 100)}))
    assert predicted is None
    assert reason == "potential_chunnel_source_stack"


def test_unknown_warp_well_setting_with_nearby_factual_planet_fails_closed() -> None:
    predicted, reason = _predict(
        planets=((99, 110, 100),),
        warp_wells_enabled=None,
        eligible_warp_well_planet_ids=None,
    )
    assert predicted is None
    assert reason == "warp_well_setting_unknown"
