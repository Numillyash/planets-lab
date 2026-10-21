"""Fully fictional, strictly scoped two-base early queue and economic ledger."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.core import Starbase, Ship
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import (
    PLACEMENTS, QUEUE_MODES, STATUS, CompleteBaseBuild,
    simulate_unthrottled_multibase_build_turn,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture
from test_standard_ship_component_quote import pre


def context():
    game = fixture()
    game.ships.clear()
    planet, base, specs, blueprint = pre()
    game.planets[10] = deepcopy(planet)
    game.starbases[10] = deepcopy(base)
    second = deepcopy(planet)
    second.id = 20
    second.owner_id = 2
    second.x, second.y = 300, 300
    second.cargo.megacredits = 500
    game.planets[20] = second
    game.starbases[20] = Starbase(
        planet_id=20, owner_id=2,
        tech_hull=5, tech_engine=6, tech_beam=3, tech_torpedo=5,
    )
    game.validate()
    return game, specs, blueprint


def queue_for(design, *, limit=500, first_stock=None, second_stock=None):
    def selection(pid, ship_id):
        return SelectedBuildSlot(
            starbase_planet_id=pid, proposed_ship_id=ship_id,
            global_ship_limit=limit,
            complete_global_ship_roster_asserted=True,
            queue_selection_asserted=True,
        )
    return {
        10: CompleteBaseBuild(
            blueprint=design,
            warehouse=first_stock if first_stock is not None
            else StandardComponentWarehouse(),
            slot=selection(10, 17),
            allowed_hull_ids=frozenset({7}),
        ),
        20: CompleteBaseBuild(
            blueprint=design,
            warehouse=second_stock if second_stock is not None
            else StandardComponentWarehouse(),
            slot=selection(20, 18),
            allowed_hull_ids=frozenset({7}),
        ),
    }


def simulate(game, specs, queue, **kwargs):
    args = dict(
        queue_mode="CLASSIC_PBP",
        global_ship_limit=500,
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_base_roster_and_warehouses_asserted=True,
        all_bases_have_ordinary_builds_asserted=True,
        no_priority_cloning_or_other_base_actions_asserted=True,
        no_ship_actions_or_combat_asserted=True,
    )
    args.update(kwargs)
    return simulate_unthrottled_multibase_build_turn(
        game, specs, queue, **args,
    )


@pytest.mark.parametrize("mode", QUEUE_MODES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_two_owner_two_base_uncontested_early_builds_are_exact(mode, placement):
    game, specs, design = context()
    intents = queue_for(design)
    frozen = deepcopy((game, specs, intents))
    a = simulate(game, specs, intents, queue_mode=mode, placement=placement)
    b = simulate(game, specs, intents, queue_mode=mode, placement=placement)
    assert a == b
    assert a.supported and a.status == STATUS
    assert a.queue_mode == mode
    assert a.state.turn == game.turn + 1
    assert set(a.state.ships) == {17, 18}
    assert a.state.ships[17].owner_id == 1
    assert a.state.ships[18].owner_id == 2
    assert (a.state.ships[17].x, a.state.ships[17].y) == (100, 100)
    assert (a.state.ships[18].x, a.state.ships[18].y) == (300, 300)
    assert a.state.starbases == game.starbases
    assert len(a.receipts) == 2
    assert [x.ship_id for x in a.receipts] == [17, 18]
    assert [x.starbase_planet_id for x in a.receipts] == [10, 20]
    assert len(a.planet_balances) == 2
    assert all(x.resource_balance_exact for x in a.planet_balances)
    assert all(x.material_debit_exact and x.warehouse_debit_exact
               and x.assembled_ship_exact for x in a.receipts)
    assert {x.purchased.megacredits for x in a.receipts} == {260}
    assert {x.purchased.duranium for x in a.receipts} == {9}
    assert all(x.purchased.tritanium == 13 for x in a.receipts)
    assert all(x.purchased.molybdenum == 6 for x in a.receipts)
    assert not a.independently_verified_queue_order
    assert not a.independently_verified_priority_points
    assert not a.independently_verified_ship_id_allocation
    assert not a.independently_verified_component_warehouses
    assert not a.nuhost_execution_verified
    assert not a.nuhost_phase_placement_verified
    assert not a.independent_host_parity_verified
    assert (game, specs, intents) == frozen


def test_mixed_all_new_and_stocked_bases_have_separate_exact_bills():
    game, specs, design = context()
    first = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    second = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 1),),
    )
    queue = queue_for(design, first_stock=first, second_stock=second)
    out = simulate(game, specs, queue, placement=PLACEMENTS[1])
    assert out.supported
    assert out.receipts[0].purchased.megacredits == 0
    assert out.receipts[1].purchased.megacredits == 90
    assert out.receipts[0].warehouse_after == StandardComponentWarehouse(
        hulls=((7, 0),), engines=((9, 0),),
        beams=((3, 0),), launchers=((2, 0),),
    )
    assert out.receipts[1].warehouse_after.hulls == ((7, 0),)


def test_newly_mined_materials_support_after_economy_but_not_before():
    game, specs, design = context()
    game.planets[10].cargo.duranium = 0
    game.planets[10].mines = 14  # Federation 70% -> 10 KT
    requests = queue_for(design)
    initial = deepcopy(game)
    early = simulate(game, specs, requests, placement=PLACEMENTS[0])
    late = simulate(game, specs, requests, placement=PLACEMENTS[1])
    assert not early.supported
    assert early.state is None and early.receipts == ()
    assert late.supported
    assert late.planet_balances[0].mined_minerals[1] >= 9
    assert len(late.receipts) == 2
    assert game == initial


def test_cash_tax_funds_both_bases_only_after_economy():
    game, specs, design = context()
    game.planets[10].cargo.megacredits = 259
    game.planets[20].cargo.megacredits = 259
    requests = queue_for(design)
    before = simulate(game, specs, requests, placement=PLACEMENTS[0])
    after = simulate(game, specs, requests, placement=PLACEMENTS[1])
    assert not before.supported and before.state is None
    assert after.supported
    assert len(after.receipts) == 2
    assert all(x.taxes_collected > 0 for x in after.planet_balances)


@pytest.mark.parametrize("case", (
    "one_base_omitted", "phantom_base", "missing_slot", "duplicate_ship_id",
    "ship_id_collision", "ship_cap_exhausted", "middle_90pct_boundary",
    "classic_id_beyond_hard_limit", "special_slot_type", "unapproved_queue",
    "pls", "missing_standard_assert", "missing_warehouse_assert",
    "missing_all_queued_assert", "missing_no_priority_assert",
    "missing_combat_assert", "empty_queue", "unknown_stock",
    "bad_hull_license", "foreign_base", "unaffordable_late_base",
    "unsupported_existing_ship", "unsupported_metadata",
    "invalid_seed", "unrecognized_placement",
))
def test_full_queue_denials_fail_closed_without_partial_ships(case):
    game, specs, blueprint = context()
    q = queue_for(blueprint)
    opts = {}
    if case == "one_base_omitted": q.pop(20)
    elif case == "phantom_base": q[30] = q.pop(20)
    elif case == "missing_slot":
        q[20] = replace(q[20], slot=replace(q[20].slot, queue_selection_asserted=False))
    elif case == "duplicate_ship_id":
        q[20] = replace(q[20], slot=replace(q[20].slot, proposed_ship_id=17))
    elif case == "ship_id_collision":
        game.ships[17] = Ship(id=17, owner_id=1, hull_id=7, x=100, y=100)
    elif case == "ship_cap_exhausted":
        opts["global_ship_limit"] = 10
        # After 8 earlier ships, only two slots: near-limit modes are excluded.
        for i in range(1, 9):
            game.ships[i] = Ship(id=i, owner_id=1, hull_id=7, x=100, y=100)
        for pid in q:
            q[pid] = replace(q[pid], slot=replace(q[pid].slot, global_ship_limit=10))
    elif case == "middle_90pct_boundary":
        opts["global_ship_limit"] = 10
        for i in range(1, 8):
            game.ships[i] = Ship(id=i, owner_id=1, hull_id=7, x=100, y=100)
        for pid in q:
            q[pid] = replace(q[pid], slot=replace(q[pid].slot, global_ship_limit=10))
    elif case == "classic_id_beyond_hard_limit":
        opts["global_ship_limit"] = 30
        q[20] = replace(q[20], slot=replace(q[20].slot, proposed_ship_id=31, global_ship_limit=30))
        q[10] = replace(q[10], slot=replace(q[10].slot, global_ship_limit=30))
    elif case == "special_slot_type":
        q[20] = replace(q[20], slot=replace(q[20].slot, queue_hypothesis="PRIORITY_BUILD"))
    elif case == "unapproved_queue":
        opts["queue_mode"] = "UNSPECIFIED"
    elif case == "pls": opts["queue_mode"] = "PLS"
    elif case == "missing_standard_assert": opts["standard_rules_asserted"] = False
    elif case == "missing_warehouse_assert":
        opts["complete_base_roster_and_warehouses_asserted"] = False
    elif case == "missing_all_queued_assert":
        opts["all_bases_have_ordinary_builds_asserted"] = False
    elif case == "missing_no_priority_assert":
        opts["no_priority_cloning_or_other_base_actions_asserted"] = False
    elif case == "missing_combat_assert":
        opts["no_ship_actions_or_combat_asserted"] = False
    elif case == "empty_queue": q = {}
    elif case == "unknown_stock":
        q[20] = replace(q[20], warehouse=StandardComponentWarehouse(engines=((99, 3),)))
    elif case == "bad_hull_license":
        q[20] = replace(q[20], allowed_hull_ids=frozenset({1}))
    elif case == "foreign_base":
        game.starbases[20].owner_id = 1
    elif case == "unaffordable_late_base":
        game.planets[20].cargo.megacredits = 0
        game.planets[20].tax_rate = 0
    elif case == "unsupported_existing_ship":
        game.ships[1] = Ship(id=1, owner_id=1, hull_id=7, x=100, y=100, mission="tow")
    elif case == "unsupported_metadata": game.metadata["priority_points"] = 5
    elif case == "invalid_seed": opts["seed"] = True
    elif case == "unrecognized_placement": opts["placement"] = "real_host_order"
    frozen = deepcopy((game, specs, q))
    out = simulate(game, specs, q, **opts)
    assert not out.supported and out.status == "ABSTAIN_UNTHROTTLED_MULTI_BASE_BUILD"
    assert out.state is None and out.receipts == ()
    assert out.planet_balances == () and out.economy_events == ()
    assert not out.nuhost_execution_verified
    assert (game, specs, q) == frozen


@pytest.mark.parametrize("tamper", (
    "wrong_first_warehouse", "wrong_second_cost", "new_ship_fields",
    "extra_ship", "planet_mc", "ground_mineral", "missing_mine_event",
))
def test_corrupted_economy_or_per_base_receipts_abstain(monkeypatch, tamper):
    import planets_lab.sim.standard_unthrottled_multibase_queue as mod
    original_build = mod.assemble_selected_standard_ship
    original_step = mod.HostEngine.step
    calls = 0

    def corrupted_build(*args, **kwargs):
        nonlocal calls
        calls += 1
        outcome = original_build(*args, **kwargs)
        if not outcome.supported:
            return outcome
        if tamper == "wrong_first_warehouse" and calls == 1:
            return replace(outcome, warehouse_after=StandardComponentWarehouse(
                hulls=((7, 2),),
            ))
        if tamper == "wrong_second_cost" and calls == 2:
            return replace(outcome, purchased_cost=replace(
                outcome.purchased_cost, duranium=outcome.purchased_cost.duranium + 1,
            ))
        if tamper == "new_ship_fields" and calls == 2:
            bad = deepcopy(outcome.phase_state)
            bad.ships[18].crew += 1
            return replace(outcome, phase_state=bad, assembled_ship=bad.ships[18])
        return outcome

    def corrupted_economy(self, state, orders, *, seed=0):
        modeled, events = original_step(self, state, orders, seed=seed)
        modeled = deepcopy(modeled)
        if tamper == "extra_ship":
            modeled.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        elif tamper == "planet_mc":
            modeled.planets[20].cargo.megacredits += 1
        elif tamper == "ground_mineral":
            modeled.planets[20].ground_duranium.amount += 1
        elif tamper == "missing_mine_event":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        return modeled, events

    monkeypatch.setattr(mod, "assemble_selected_standard_ship", corrupted_build)
    monkeypatch.setattr(mod.HostEngine, "step", corrupted_economy)
    game, specs, design = context()
    initial = deepcopy(game)
    out = simulate(game, specs, queue_for(design))
    assert not out.supported
    assert out.state is None and out.receipts == ()
    assert out.planet_balances == () and out.economy_events == ()
    assert game == initial


def test_legacy_owner_signed_capture_and_canonical_host_stay_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    assert len(PlanetaryHostPipeline().phases) == 14
    assert tuple(f.name for f in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset((
        "player_id", "ship_orders", "starbase_tech_orders",
    ))
