"""Model-only warehouse, chosen queue slot, new ship with exact materials."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.standard_ship_warehouse_assembly import (
    MODEL_STATUS, QUEUE_HYPOTHESIS, SelectedBuildSlot,
    StandardComponentWarehouse, assemble_selected_standard_ship,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture
from test_standard_ship_component_quote import pre


def context():
    state = fixture()
    state.ships.clear()
    planet, base, specs, blueprint = pre()
    state.planets[10] = planet
    state.starbases[10] = base
    state.validate()
    return state, specs, blueprint


def selected(**opts):
    args = dict(
        starbase_planet_id=10, proposed_ship_id=17,
        global_ship_limit=500,
        queue_hypothesis=QUEUE_HYPOTHESIS,
        complete_global_ship_roster_asserted=True,
        queue_selection_asserted=True,
    )
    args.update(opts)
    return SelectedBuildSlot(**args)


def calculate(state, specs, design, warehouse=None, slot=None, **changes):
    args = dict(
        allowed_hull_ids=frozenset({7}),
        standard_rules_asserted=True,
        complete_warehouse_asserted=True,
        hull_eligibility_asserted=True,
        standard_hull_crew_asserted=True,
    )
    args.update(changes)
    return assemble_selected_standard_ship(
        state, specs, design,
        warehouse if warehouse is not None else StandardComponentWarehouse(),
        slot if slot is not None else selected(),
        **args,
    )


def test_all_new_components_creates_one_conditional_ship_with_exact_cost():
    state, specs, design = context()
    frozen = deepcopy((state, specs, design))
    first = calculate(state, specs, design)
    replay = calculate(state, specs, design)
    assert first == replay
    assert first.supported and first.status == MODEL_STATUS
    assert first.purchased_cost.megacredits == 260
    assert (first.purchased_cost.duranium,
            first.purchased_cost.tritanium,
            first.purchased_cost.molybdenum) == (9, 13, 6)
    assert len(first.component_ledger) == 4
    assert [(x.kind, x.drawn_from_warehouse, x.newly_purchased)
            for x in first.component_ledger] == [
        ("hulls", 0, 1), ("engines", 0, 2),
        ("beams", 0, 2), ("launchers", 0, 1),
    ]
    assert first.phase_state.turn == state.turn  # phase stage, not Host turn
    assert first.phase_state.ships[17] == first.assembled_ship
    ship = first.assembled_ship
    assert ship.id == 17 and ship.owner_id == 1 and ship.hull_id == 7
    assert ship.engine_id == 9 and ship.beam_id == 3 and ship.beam_count == 2
    assert ship.torpedo_id == 2 and ship.torpedo_launcher_count == 1
    assert ship.fighter_bay_count == 0 and ship.crew == 20
    assert ship.cargo.neutronium == 0 and ship.cargo.supplies == 0
    assert ship.x == state.planets[10].x and ship.y == state.planets[10].y
    for key in ("megacredits", "duranium", "tritanium", "molybdenum"):
        assert (getattr(state.planets[10].cargo, key)
                - getattr(first.phase_state.planets[10].cargo, key)
                == getattr(first.purchased_cost, key))
    assert not first.independently_authenticated_warehouse
    assert not first.independently_authenticated_queue_slot
    assert not first.independently_authenticated_ship_id
    assert not first.nuhost_ship_assembly_verified
    assert not first.independent_host_parity_verified
    assert (state, specs, design) == frozen


def test_exact_partial_component_stock_debits_only_missing_items():
    state, specs, design = context()
    inventory = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 1),),
        beams=((3, 1),), launchers=((2, 0),),
    )
    original = deepcopy((state, inventory))
    out = calculate(state, specs, design, warehouse=inventory)
    assert out.supported
    assert out.purchased_cost.megacredits == 90
    assert (out.purchased_cost.duranium,
            out.purchased_cost.tritanium,
            out.purchased_cost.molybdenum) == (3, 3, 2)
    assert [(x.drawn_from_warehouse, x.newly_purchased)
            for x in out.component_ledger] == [(1, 0), (1, 1), (1, 1), (0, 1)]
    assert out.warehouse_after == StandardComponentWarehouse(
        hulls=((7, 0),), engines=((9, 0),),
        beams=((3, 0),), launchers=((2, 0),),
    )
    assert out.phase_state.ships[17] == out.assembled_ship
    assert (state, inventory) == original


def test_fully_stocked_build_consumes_warehouse_without_planetary_charge():
    state, specs, design = context()
    stock = StandardComponentWarehouse(
        hulls=((7, 3),), engines=((9, 4),),
        beams=((3, 4),), launchers=((2, 2),),
    )
    out = calculate(state, specs, design, warehouse=stock)
    assert out.supported
    assert out.purchased_cost.megacredits == 0
    assert out.purchased_cost.duranium == 0
    assert out.phase_state.planets[10].cargo == state.planets[10].cargo
    assert out.warehouse_after == StandardComponentWarehouse(
        hulls=((7, 2),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )


def test_inadequate_surface_minerals_abstain_but_existing_stock_can_rescue():
    state, specs, design = context()
    state.planets[10].cargo.molybdenum = 0
    assert not calculate(state, specs, design).supported
    stock = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    out = calculate(state, specs, design, warehouse=stock)
    assert out.supported
    assert out.purchased_cost.molybdenum == 0


@pytest.mark.parametrize("case", [
    "no_rules", "no_stock_witness", "no_race_witness", "no_crew_witness",
    "no_slot_witness", "no_roster_witness", "bad_queue", "bad_limit",
    "above_ship_limit", "ship_collision", "id_zero", "id_1000", "bool_ship_id",
    "foreign_base", "absent_base", "missing_hull_license", "bad_hull",
    "bad_stock_type", "duplicate_stock", "negative_stock", "bool_stock",
    "unknown_stock_id", "phantom_catalog_stock", "stock_tuple_missing", "missing_credits",
    "unknown_game_variant", "ship_roster_inconsistent", "tech_too_low",
])
def test_unsupported_queue_stock_design_or_resource_fails_closed(case):
    state, specs, design = context()
    warehouse = StandardComponentWarehouse()
    sel = selected()
    opts = {}
    if case == "no_rules": opts["standard_rules_asserted"] = False
    elif case == "no_stock_witness": opts["complete_warehouse_asserted"] = False
    elif case == "no_race_witness": opts["hull_eligibility_asserted"] = False
    elif case == "no_crew_witness": opts["standard_hull_crew_asserted"] = False
    elif case == "no_slot_witness": sel = replace(sel, queue_selection_asserted=False)
    elif case == "no_roster_witness":
        sel = replace(sel, complete_global_ship_roster_asserted=False)
    elif case == "bad_queue":
        sel = replace(sel, queue_hypothesis="postlimit_pbp_suggested")
    elif case == "bad_limit": sel = replace(sel, global_ship_limit=1000)
    elif case == "above_ship_limit": sel = replace(sel, global_ship_limit=1)
    elif case == "ship_collision":
        ship = deepcopy(fixture().ships[1])
        ship.id = 17
        state.ships[17] = ship
    elif case == "id_zero": sel = replace(sel, proposed_ship_id=0)
    elif case == "id_1000": sel = replace(sel, proposed_ship_id=1000)
    elif case == "bool_ship_id": sel = replace(sel, proposed_ship_id=True)
    elif case == "foreign_base": state.starbases[10].owner_id = 2
    elif case == "absent_base": state.starbases.clear()
    elif case == "missing_hull_license": opts["allowed_hull_ids"] = frozenset({8})
    elif case == "bad_hull": design = replace(design, hull_id=999)
    elif case == "bad_stock_type": warehouse = StandardComponentWarehouse(hulls=[(7, 1)])
    elif case == "duplicate_stock":
        warehouse = StandardComponentWarehouse(hulls=((7, 1), (7, 2)))
    elif case == "negative_stock": warehouse = StandardComponentWarehouse(hulls=((7, -1),))
    elif case == "bool_stock": warehouse = StandardComponentWarehouse(engines=((9, True),))
    elif case == "unknown_stock_id": warehouse = StandardComponentWarehouse(hulls=((0, 2),))
    elif case == "phantom_catalog_stock":
        warehouse = StandardComponentWarehouse(engines=((999, 2),))
    elif case == "stock_tuple_missing": warehouse = StandardComponentWarehouse(hulls=((7,),))
    elif case == "missing_credits": state.planets[10].cargo.megacredits = 0
    elif case == "unknown_game_variant": state.metadata["campaign_special"] = True
    elif case == "ship_roster_inconsistent":
        state.ships[4] = deepcopy(fixture().ships[1])
    elif case == "tech_too_low": state.starbases[10].tech_engine = 1
    if case == "above_ship_limit":
        # Global cap one, but at least one existing ship must occupy it.
        ship = deepcopy(fixture().ships[1])
        ship.id = 99
        state.ships[99] = ship
    snapshot = deepcopy((state, specs, design, warehouse, sel))
    outcome = calculate(state, specs, design, warehouse, sel, **opts)
    assert outcome.status == "ABSTAIN_STANDARD_SHIP_ASSEMBLY"
    assert not outcome.supported
    assert outcome.phase_state is None
    assert outcome.assembled_ship is None
    assert outcome.warehouse_after is None
    assert outcome.purchased_cost is None
    assert outcome.component_ledger == ()
    assert not outcome.nuhost_ship_assembly_verified
    assert (state, specs, design, warehouse, sel) == snapshot


def test_phase_state_is_not_a_complete_host_turn_or_independent_queue_witness():
    state, specs, design = context()
    out = calculate(state, specs, design)
    assert out.supported
    assert out.phase_state.turn == state.turn
    assert out.phase_state_turn_advanced is False
    assert not out.independently_authenticated_queue_slot
    assert not out.independently_authenticated_ship_id
    assert not out.nuhost_ship_assembly_verified
    # Existing owner HMAC schema must not silently acquire unsigned build orders.
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert tuple(f.name for f in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset((
        "player_id", "ship_orders", "starbase_tech_orders",
    ))
