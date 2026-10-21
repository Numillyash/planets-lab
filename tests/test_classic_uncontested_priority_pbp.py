"""Classic Priority Build Points: exact normal hull cost, bounded one owner/base."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.classic_uncontested_priority_pbp import (
    STATUS, ClassicPriorityContext, PriorityShipOrder,
    documented_classic_priority_cost, simulate_uncontested_classic_pbp_priority,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from test_classic_standard_pointer_economy_turn import context as classic_game


def prepare(*, existing=8, pbp=21):
    state, specs, _, regular = classic_game(existing=existing)
    priority_context = ClassicPriorityContext(
        ship_limit=10,
        player_pbps=((1, pbp), (2, 0)),
        queued_base_orders={
            10: PriorityShipOrder(
                blueprint=regular[10].blueprint,
                warehouse=StandardComponentWarehouse(),
                allowed_hull_ids=frozenset({7}),
            ),
            20: PriorityShipOrder(
                blueprint=regular[20].blueprint,
                warehouse=StandardComponentWarehouse(),
                allowed_hull_ids=frozenset({7}),
            ),
            30: None,
        },
        full_fleet_and_base_roster_asserted=True,
        complete_player_pbp_balances_asserted=True,
        no_pb_codes_clones_or_other_priority_orders_asserted=True,
        exact_single_precombat_priority_subphase_asserted=True,
    )
    return state, specs, priority_context


def run(state, specs, queue, **kwargs):
    opts = dict(
        standard_rules_asserted=True,
        complete_warehouse_and_hull_rights_asserted=True,
    )
    opts.update(kwargs)
    return simulate_uncontested_classic_pbp_priority(state, specs, queue, **opts)


@pytest.mark.parametrize("mass,expected", [
    (1, 1), (49, 1), (50, 1), (51, 2), (60, 2),
    (100, 2), (101, 3), (999, 20), (1000, 20), (1001, 20),
])
def test_documented_cost_ceiling_per_50kt_and_20_point_cap(mass, expected):
    assert documented_classic_priority_cost(mass) == expected


@pytest.mark.parametrize("bad", [-1, 0, None, True, 25.5, "100"])
def test_bad_hull_mass_abstains_on_cost_quote(bad):
    assert documented_classic_priority_cost(bad) is None


def test_single_player_priority_build_consumes_one_pbp_and_lowest_free_ship_id():
    state, specs, queue = prepare()
    initial = deepcopy((state, specs, queue))
    outcome = run(state, specs, queue)
    replay = run(state, specs, queue)
    assert outcome == replay
    assert outcome.status == STATUS and outcome.supported
    assert outcome.selected_base_planet_id == 10
    assert outcome.built_ship_id == 9
    assert outcome.hull_mass == 50
    assert outcome.pbp_cost == 1
    assert outcome.player_pbps_after == ((1, 20), (2, 0))
    assert outcome.phase_state.turn == state.turn
    assert outcome.phase_state.ships[9].owner_id == 1
    assert set(outcome.phase_state.ships) == set(state.ships) | {9}
    assert outcome.purchased_materials.megacredits == 260
    assert outcome.purchased_materials.duranium == 9
    assert not outcome.independently_witnessed_pbp_balance
    assert not outcome.independently_witnessed_queue_selection
    assert not outcome.independently_witnessed_ship_id
    assert not outcome.nuhost_execution_verified
    assert not outcome.independent_host_parity_verified
    assert (state, specs, queue) == initial


def test_huge_hull_priority_price_still_capped_at_20_pbp():
    state, specs, queue = prepare(pbp=21)
    specs.hulls[7] = replace(specs.hulls[7], mass=1121)
    result = run(state, specs, queue)
    assert result.supported
    assert result.pbp_cost == 20
    assert result.player_pbps_after == ((1, 1), (2, 0))


def test_fully_stocked_priority_build_does_not_charge_surface_materials():
    state, specs, queue = prepare()
    stocked = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    q = dict(queue.queued_base_orders)
    q[10] = replace(q[10], warehouse=stocked)
    queue = replace(queue, queued_base_orders=q)
    state.planets[10].cargo.megacredits = 0
    state.planets[10].cargo.duranium = 0
    state.planets[10].cargo.tritanium = 0
    state.planets[10].cargo.molybdenum = 0
    result = run(state, specs, queue)
    assert result.supported
    assert result.purchased_materials.megacredits == 0
    assert result.purchased_materials.duranium == 0
    assert result.warehouse_after == StandardComponentWarehouse(
        hulls=((7, 0),), engines=((9, 0),),
        beams=((3, 0),), launchers=((2, 0),),
    )


@pytest.mark.parametrize("case", [
    "below_threshold", "second_high_pbp", "duplicate_pbp",
    "missing_player", "bool_pbp", "negative_pbp", "no_base_queue",
    "duplicate_priority_base", "wrong_owner", "missing_base",
    "bad_context", "missing_roster_assert", "missing_points_assert",
    "missing_no_pb_assert", "missing_phase_assert", "no_standard_rules",
    "missing_warehouse_assert", "hard_limit_full",
    "unknown_mass", "invalid_hull_id", "no_money", "ship_mission",
    "unknown_stock", "unexpected_metadata", "bad_ship_limit",
])
def test_unsupported_priority_contest_or_source_abstains_whole_phase(case):
    state, specs, q = prepare()
    opt = {}
    if case == "below_threshold": q = replace(q, player_pbps=((1, 20), (2, 0)))
    elif case == "second_high_pbp":
        q = replace(q, player_pbps=((1, 21), (2, 21)))
    elif case == "duplicate_pbp":
        q = replace(q, player_pbps=((1, 21), (1, 22), (2, 0)))
    elif case == "missing_player": q = replace(q, player_pbps=((1, 21),))
    elif case == "bool_pbp": q = replace(q, player_pbps=((1, True), (2, 0)))
    elif case == "negative_pbp": q = replace(q, player_pbps=((1, -1), (2, 0)))
    elif case == "no_base_queue":
        q = replace(q, queued_base_orders={10: q.queued_base_orders[10]})
    elif case == "duplicate_priority_base":
        req = dict(q.queued_base_orders)
        req[30] = req[10]
        q = replace(q, queued_base_orders=req)
    elif case == "wrong_owner": state.starbases[10].owner_id = 2
    elif case == "missing_base": state.starbases.pop(30)
    elif case == "bad_context": q = {"wrong": True}
    elif case == "missing_roster_assert":
        q = replace(q, full_fleet_and_base_roster_asserted=False)
    elif case == "missing_points_assert":
        q = replace(q, complete_player_pbp_balances_asserted=False)
    elif case == "missing_no_pb_assert":
        q = replace(q, no_pb_codes_clones_or_other_priority_orders_asserted=False)
    elif case == "missing_phase_assert":
        q = replace(q, exact_single_precombat_priority_subphase_asserted=False)
    elif case == "no_standard_rules": opt["standard_rules_asserted"] = False
    elif case == "missing_warehouse_assert":
        opt["complete_warehouse_and_hull_rights_asserted"] = False
    elif case == "hard_limit_full":
        from planets_lab.core import Ship
        state.ships[9] = Ship(id=9, owner_id=1, hull_id=7, x=100, y=100)
        state.ships[10] = Ship(id=10, owner_id=1, hull_id=7, x=100, y=100)
    elif case == "unknown_mass": specs.hulls[7] = replace(specs.hulls[7], mass=0)
    elif case == "invalid_hull_id":
        req = dict(q.queued_base_orders)
        req[10] = replace(req[10], blueprint=replace(req[10].blueprint, hull_id=999))
        q = replace(q, queued_base_orders=req)
    elif case == "no_money": state.planets[10].cargo.megacredits = 0
    elif case == "ship_mission": state.ships[1].mission = "tow"
    elif case == "unknown_stock":
        req = dict(q.queued_base_orders)
        req[10] = replace(req[10], warehouse=StandardComponentWarehouse(
            hulls=((999, 1),),
        ))
        q = replace(q, queued_base_orders=req)
    elif case == "unexpected_metadata": state.metadata["special"] = True
    elif case == "bad_ship_limit": q = replace(q, ship_limit=1000)
    original = deepcopy((state, specs, q))
    result = run(state, specs, q, **opt)
    assert result.status == "ABSTAIN_CLASSIC_PRIORITY_BUILD"
    assert not result.supported
    assert result.phase_state is None
    assert result.built_ship_id is None
    assert result.warehouse_after is None
    assert result.player_pbps_after == ()
    assert not result.nuhost_execution_verified
    assert (state, specs, q) == original
