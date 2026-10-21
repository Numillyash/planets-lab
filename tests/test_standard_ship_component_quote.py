"""Exact NEW component purchase quote, no ship construction or Host receipt."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.core import Starbase
from planets_lab.data.nu_specs import (
    BeamSpec, EngineSpec, HullSpec, NuStaticSpecs, ResourceCost, TorpedoSpec,
)
from planets_lab.sim.standard_ship_component_quote import (
    QUOTE_STATUS, StandardShipBlueprint, quote_standard_new_component_ship,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def catalog():
    return NuStaticSpecs(
        hulls={7: HullSpec(
            id=7, name="fictional normal frigate", tech_level=4, mass=50,
            cargo_capacity=100, fuel_tank=200, crew=20,
            engine_count=2, beam_count=3, torpedo_launcher_count=2,
            fighter_bay_count=0, can_cloak=False,
            cost=ResourceCost(100, 5, 7, 3),
        )},
        engines={9: EngineSpec(
            id=9, name="fictional engine", tech_level=6,
            cost=ResourceCost(60, 1, 2, 1),
            warp_fuel_factors=tuple(range(10)),
        )},
        beams={3: BeamSpec(
            id=3, name="fictional beam", tech_level=3, mass=2,
            damage=5, crew_kill=2,
            cost=ResourceCost(10, 0, 1, 0),
        )},
        torpedoes={2: TorpedoSpec(
            id=2, name="fictional launcher", tech_level=5, mass=2,
            damage=10, crew_kill=10, combat_range=100,
            launcher_cost=20, torpedo_cost=5,
            cost=ResourceCost(20, 2, 0, 1),
        )},
    )


def pre():
    planet = fixture().planets[10]
    planet.cargo.megacredits = 500
    planet.cargo.duranium = 100
    planet.cargo.tritanium = 100
    planet.cargo.molybdenum = 100
    base = Starbase(planet_id=10, owner_id=1,
                    tech_hull=5, tech_engine=6, tech_beam=3,
                    tech_torpedo=5)
    design = StandardShipBlueprint(
        hull_id=7, engine_id=9,
        beam_id=3, beam_count=2,
        torpedo_id=2, torpedo_launcher_count=1,
    )
    return planet, base, catalog(), design


def calculate(planet, base, static, design, **overrides):
    args = dict(
        allowed_hull_ids=frozenset({7}),
        standard_rules_asserted=True,
        no_warehouse_parts_used_asserted=True,
        hull_eligibility_asserted=True,
    )
    args.update(overrides)
    return quote_standard_new_component_ship(
        planet, base, static, design, **args,
    )


def test_documented_standard_parts_quote_multiplies_engine_and_weapon_costs():
    p, b, c, d = pre()
    copy = deepcopy((p, b, c, d))
    quote = calculate(p, b, c, d)
    repeat = calculate(p, b, c, d)
    assert quote == repeat
    assert quote.status == QUOTE_STATUS and quote.supported
    assert quote.cost == ResourceCost(
        megacredits=260, duranium=9, tritanium=13, molybdenum=6,
    )
    assert quote.engine_count == 2 and quote.hull_count == 1
    assert quote.beam_count == 2 and quote.torpedo_launcher_count == 1
    assert quote.affordable_from_surface
    assert dict(quote.shortfalls) == {
        "megacredits": 0, "duranium": 0,
        "tritanium": 0, "molybdenum": 0,
    }
    assert not quote.warehouse_inventory_verified
    assert not quote.race_build_rights_independently_verified
    assert not quote.actual_ship_build_queue_verified
    assert not quote.ship_limit_and_priority_verified
    assert not quote.ship_id_allocated
    assert not quote.nuhost_order_execution_verified
    assert (p, b, c, d) == copy


def test_unarmed_hull_quote_still_purchases_all_required_engines():
    p, b, c, _ = pre()
    quote = calculate(p, b, c, StandardShipBlueprint(7, 9))
    assert quote.supported
    assert quote.engine_count == 2
    assert quote.cost == ResourceCost(220, 7, 11, 5)
    assert quote.beam_count == 0 and quote.torpedo_launcher_count == 0


def test_insufficient_surface_materials_reports_deficit_not_fake_build():
    p, b, c, d = pre()
    p.cargo.megacredits = 200
    p.cargo.duranium = 4
    p.cargo.tritanium = 10
    p.cargo.molybdenum = 0
    frozen = deepcopy(p)
    result = calculate(p, b, c, d)
    assert result.supported
    assert not result.affordable_from_surface
    assert dict(result.shortfalls) == {
        "megacredits": 60,
        "duranium": 5,
        "tritanium": 3,
        "molybdenum": 6,
    }
    assert p == frozen
    assert result.ship_id_allocated is False


@pytest.mark.parametrize("scenario", (
    "missing_rules", "missing_warehouse_assertion", "missing_eligibility",
    "missing_license_set", "unlicensed_hull", "bad_license_bool",
    "foreign_base", "wrong_planet_id", "missing_owner",
    "unknown_hull", "unknown_engine", "special_hull",
    "tech_hull", "tech_engine", "tech_beam", "tech_torpedo",
    "unknown_beam", "unknown_launcher",
    "excess_beams", "excess_tubes", "negative_beams",
    "bool_beam_count", "beam_missing_id", "unused_beam_id",
    "tube_missing_id", "unused_tube_id",
    "bad_base_tech", "negative_planet_stock",
    "negative_unit_price", "boolean_unit_price", "zero_engines",
))
def test_invalid_design_or_unverified_cost_abstains(scenario):
    p, b, c, d = pre()
    opts = {}
    if scenario == "missing_rules": opts["standard_rules_asserted"] = False
    elif scenario == "missing_warehouse_assertion":
        opts["no_warehouse_parts_used_asserted"] = False
    elif scenario == "missing_eligibility":
        opts["hull_eligibility_asserted"] = False
    elif scenario == "missing_license_set":
        opts["allowed_hull_ids"] = None
    elif scenario == "unlicensed_hull":
        opts["allowed_hull_ids"] = frozenset({8})
    elif scenario == "bad_license_bool":
        opts["allowed_hull_ids"] = frozenset({True, 7})
    elif scenario == "foreign_base": b.owner_id = 2
    elif scenario == "wrong_planet_id": b.planet_id = 11
    elif scenario == "missing_owner": p.owner_id = None
    elif scenario == "unknown_hull": d = replace(d, hull_id=999)
    elif scenario == "unknown_engine": d = replace(d, engine_id=999)
    elif scenario == "special_hull":
        c.hulls[7] = replace(c.hulls[7], special="hyperspecial")
    elif scenario == "tech_hull": b.tech_hull = 3
    elif scenario == "tech_engine": b.tech_engine = 5
    elif scenario == "tech_beam": b.tech_beam = 2
    elif scenario == "tech_torpedo": b.tech_torpedo = 4
    elif scenario == "unknown_beam": d = replace(d, beam_id=999)
    elif scenario == "unknown_launcher": d = replace(d, torpedo_id=999)
    elif scenario == "excess_beams": d = replace(d, beam_count=4)
    elif scenario == "excess_tubes": d = replace(d, torpedo_launcher_count=3)
    elif scenario == "negative_beams": d = replace(d, beam_count=-1)
    elif scenario == "bool_beam_count": d = replace(d, beam_count=True)
    elif scenario == "beam_missing_id": d = replace(d, beam_id=None)
    elif scenario == "unused_beam_id": d = replace(d, beam_count=0)
    elif scenario == "tube_missing_id": d = replace(d, torpedo_id=None)
    elif scenario == "unused_tube_id": d = replace(d, torpedo_launcher_count=0)
    elif scenario == "bad_base_tech": b.tech_hull = True
    elif scenario == "negative_planet_stock": p.cargo.tritanium = -1
    elif scenario == "negative_unit_price":
        c.engines[9] = replace(c.engines[9],
                               cost=ResourceCost(-1, 0, 0, 0))
    elif scenario == "boolean_unit_price":
        c.engines[9] = replace(c.engines[9],
                               cost=ResourceCost(True, 0, 0, 0))
    elif scenario == "zero_engines":
        c.hulls[7] = replace(c.hulls[7], engine_count=0)
    frozen = deepcopy((p, b, c, d))
    quote = calculate(p, b, c, d, **opts)
    assert quote.status == "ABSTAIN_STANDARD_SHIP_COMPONENT_QUOTE"
    assert not quote.supported and quote.cost is None
    assert quote.shortfalls == ()
    assert not quote.ship_id_allocated
    assert (p, b, c, d) == frozen


def test_no_ship_is_created_or_resources_consumed_and_legacy_schemas_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    p, b, c, d = pre()
    saved = deepcopy((p, b, c, d))
    assert calculate(p, b, c, d).supported
    assert (p, b, c, d) == saved
    assert tuple(x.name for x in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
