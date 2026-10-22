"""Early unthrottled PQ/PPQ idle PP credits + ordinary ship building."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.early_pq_ppq_idle_pp_turn import (
    STATUS, PLACEMENTS, EarlyOrdinaryBase, EarlyPPContext,
    simulate_unthrottled_pq_ppq_idle_pp_turn,
)
from planets_lab.sim.late_pq_ppq_priority_admission import MODES
from planets_lab.sim.standard_ship_warehouse_assembly import (
    SelectedBuildSlot, StandardComponentWarehouse,
)
from planets_lab.sim.standard_unthrottled_multibase_queue import CompleteBaseBuild

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from test_classic_standard_pointer_economy_turn import context as classic_context


def fixture(*, mode="PRODUCTION_PQ", both_queued=True):
    game, specs, _, requests = classic_context(existing=8)
    def build(pid, sid):
        return CompleteBaseBuild(
            blueprint=requests[pid].blueprint,
            warehouse=StandardComponentWarehouse(),
            slot=SelectedBuildSlot(
                starbase_planet_id=pid, proposed_ship_id=sid,
                global_ship_limit=500,
                complete_global_ship_roster_asserted=True,
                queue_selection_asserted=True,
            ),
            allowed_hull_ids=frozenset({7}),
        )
    bases = (
        EarlyOrdinaryBase(10, build(10, 9)),
        EarlyOrdinaryBase(20, build(20, 10)) if both_queued
        else EarlyOrdinaryBase(20, None, StandardComponentWarehouse()),
        EarlyOrdinaryBase(30, None, StandardComponentWarehouse()),
    )
    context = EarlyPPContext(
        queue_mode=mode, soft_ship_limit=500,
        player_pp=((1, 5), (2, 7)),
        all_bases=bases,
        complete_fleet_owner_base_and_inventory_asserted=True,
        all_ordinary_starbases_selected_asserted=True,
        default_two_pp_per_idle_selected_base_asserted=True,
        no_priority_clone_regular_contention_or_other_actions_asserted=True,
    )
    return game, specs, context


def run(game, specs, context, **overrides):
    opts = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_component_rights_and_inventory_asserted=True,
        no_external_pp_income_or_other_host_actions_asserted=True,
    )
    opts.update(overrides)
    return simulate_unthrottled_pq_ppq_idle_pp_turn(game, specs, context, **opts)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_full_early_all_base_selected_build_and_idle_pp_credit(mode, placement):
    game, specs, ctx = fixture(mode=mode)
    frozen = deepcopy((game, specs, ctx))
    result = run(game, specs, ctx, placement=placement)
    assert result == run(game, specs, ctx, placement=placement)
    assert result.supported and result.status == STATUS
    assert result.state.turn == game.turn + 1
    assert set(result.state.ships) == set(game.ships) | {9, 10}
    assert result.state.ships[9].owner_id == 1
    assert result.state.ships[10].owner_id == 2
    assert result.idle_pp_credits == ((30, 1, 2),)
    assert result.player_pp_after == ((1, 7), (2, 7))
    assert len(result.ship_receipts) == 2
    assert all(x.purchased.megacredits == 260 for x in result.ship_receipts)
    assert len(result.planet_balances) == 3
    assert all(row.resource_balance_exact for row in result.planet_balances)
    assert result.base_warehouses_after[2] == (30, StandardComponentWarehouse())
    assert not result.real_starbase_selection_verified
    assert not result.real_ship_id_assignment_verified
    assert not result.independently_accepted_pp_earnings_verified
    assert not result.nuhost_execution_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified
    assert (game, specs, ctx) == frozen


def test_two_idle_bases_credit_both_owners_without_any_pp_ship_fee():
    game, specs, ctx = fixture(both_queued=False)
    # One normal build at base10, two idle bases owned by different players.
    result = run(game, specs, ctx)
    assert result.supported
    assert result.player_pp_after == ((1, 7), (2, 9))
    assert result.idle_pp_credits == ((20, 2, 2), (30, 1, 2))
    assert len(result.ship_receipts) == 1
    assert result.ship_receipts[0].ship_id == 9


def test_full_stored_parts_avoid_surface_debits_but_idle_pp_awarded():
    game, specs, ctx = fixture()
    full = StandardComponentWarehouse(
        hulls=((7,1),), engines=((9,2),),
        beams=((3,2),), launchers=((2,1),),
    )
    bases = list(ctx.all_bases)
    bases[0] = replace(bases[0], queued=replace(bases[0].queued, warehouse=full))
    ctx = replace(ctx, all_bases=tuple(bases))
    for resource in ("megacredits","duranium","tritanium","molybdenum"):
        setattr(game.planets[10].cargo, resource, 0)
    out = run(game, specs, ctx)
    assert out.supported
    assert all(
        getattr(out.ship_receipts[0].purchased, field) == 0
        for field in ("megacredits","duranium","tritanium","molybdenum")
    )
    assert out.player_pp_after == ((1,7),(2,7))
    assert dict(out.base_warehouses_after)[10].hulls == ((7,0),)


def test_before_after_economy_tax_funding_still_changes_ship_admission():
    game, specs, ctx = fixture()
    game.planets[10].cargo.megacredits = 259
    before = run(game, specs, ctx, placement=PLACEMENTS[0])
    after = run(game, specs, ctx, placement=PLACEMENTS[1])
    assert not before.supported and before.state is None
    assert after.supported
    assert after.planet_balances[0].taxes_collected > 0
    assert after.idle_pp_credits == ((30,1,2),)


def test_permuted_assigned_ids_remain_caller_asserted_not_real_host_order():
    game, specs, ctx = fixture()
    rows = list(ctx.all_bases)
    rows[0] = replace(rows[0], queued=replace(
        rows[0].queued, slot=replace(rows[0].queued.slot, proposed_ship_id=10),
    ))
    rows[1] = replace(rows[1], queued=replace(
        rows[1].queued, slot=replace(rows[1].queued.slot, proposed_ship_id=9),
    ))
    ctx = replace(ctx, all_bases=tuple(rows))
    out = run(game, specs, ctx)
    assert out.supported
    assert out.state.ships[9].owner_id == 2
    assert out.state.ships[10].owner_id == 1
    assert not out.real_ship_id_assignment_verified


@pytest.mark.parametrize("case", (
    "missing_base", "duplicate_base", "missing_idle_stock",
    "unknown_idle_part", "negative_idle_stock",
    "bool_pp", "missing_owner_pp", "duplicate_owner_pp",
    "wrong_base_owner", "bad_queue_mode", "soft_limit_boundary",
    "not_all_selected", "not_default_credits", "no_full_roster",
    "no_safe_host_claim", "bad_standard_claim", "missing_rights",
    "bad_seed", "unsupported_placement", "ship_in_motion",
    "duplicate_ship_id", "id_not_lowest_free", "missing_slot_assert",
    "price_unaffordable", "phantom_selected_parts", "custom_metadata",
    "no_queued", "no_idle", "no_known_catalog_hull",
))
def test_invalid_early_pp_assumptions_fail_closed(case):
    game, specs, ctx = fixture()
    opts = {}
    rows = list(ctx.all_bases)
    if case == "missing_base": rows.pop()
    elif case == "duplicate_base": rows[2] = rows[0]
    elif case == "missing_idle_stock": rows[2] = replace(rows[2], idle_warehouse=None)
    elif case == "unknown_idle_part":
        rows[2] = replace(rows[2], idle_warehouse=StandardComponentWarehouse(hulls=((999,1),)))
    elif case == "negative_idle_stock":
        rows[2] = replace(rows[2], idle_warehouse=StandardComponentWarehouse(hulls=((7,-1),)))
    elif case == "bool_pp": ctx = replace(ctx, player_pp=((1,True),(2,7)))
    elif case == "missing_owner_pp": ctx = replace(ctx, player_pp=((1,5),))
    elif case == "duplicate_owner_pp": ctx = replace(ctx, player_pp=((1,5),(1,6)))
    elif case == "wrong_base_owner": game.starbases[20].owner_id = 1
    elif case == "bad_queue_mode": ctx = replace(ctx, queue_mode="CLASSIC_PBP")
    elif case == "soft_limit_boundary": ctx = replace(ctx, soft_ship_limit=10)
    elif case == "not_all_selected": ctx = replace(ctx, all_ordinary_starbases_selected_asserted=False)
    elif case == "not_default_credits":
        ctx = replace(ctx, default_two_pp_per_idle_selected_base_asserted=False)
    elif case == "no_full_roster":
        ctx = replace(ctx, complete_fleet_owner_base_and_inventory_asserted=False)
    elif case == "no_safe_host_claim":
        opts["no_external_pp_income_or_other_host_actions_asserted"] = False
    elif case == "bad_standard_claim": opts["standard_rules_asserted"] = False
    elif case == "missing_rights": opts["complete_component_rights_and_inventory_asserted"] = False
    elif case == "bad_seed": opts["seed"] = True
    elif case == "unsupported_placement": opts["placement"] = "causal_nuhost_order"
    elif case == "ship_in_motion": game.ships[1].warp = 8
    elif case == "duplicate_ship_id":
        rows[1] = replace(rows[1], queued=replace(
            rows[1].queued, slot=replace(rows[1].queued.slot, proposed_ship_id=9),
        ))
    elif case == "id_not_lowest_free":
        rows[1] = replace(rows[1], queued=replace(
            rows[1].queued, slot=replace(rows[1].queued.slot, proposed_ship_id=11),
        ))
    elif case == "missing_slot_assert":
        rows[0] = replace(rows[0], queued=replace(
            rows[0].queued, slot=replace(
                rows[0].queued.slot, queue_selection_asserted=False,
            ),
        ))
    elif case == "price_unaffordable": game.planets[20].cargo.megacredits = 0
    elif case == "phantom_selected_parts":
        rows[0] = replace(rows[0], queued=replace(
            rows[0].queued, warehouse=StandardComponentWarehouse(hulls=((999,1),)),
        ))
    elif case == "custom_metadata": game.metadata["custom_mode"] = True
    elif case == "no_queued":
        rows[0] = EarlyOrdinaryBase(10,None,StandardComponentWarehouse())
        rows[1] = EarlyOrdinaryBase(20,None,StandardComponentWarehouse())
    elif case == "no_idle":
        rows[2] = replace(rows[2], queued=rows[0].queued, idle_warehouse=None)
    elif case == "no_known_catalog_hull": specs.hulls.pop(7)
    if tuple(rows) != ctx.all_bases: ctx = replace(ctx, all_bases=tuple(rows))
    frozen = deepcopy((game, specs, ctx))
    out = run(game, specs, ctx, **opts)
    assert not out.supported
    assert out.state is None and out.ship_receipts == ()
    assert out.player_pp_after == () and out.idle_pp_credits == ()
    assert out.planet_balances == () and out.economic_events == ()
    assert (game, specs, ctx) == frozen


@pytest.mark.parametrize("tamper", (
    "extra_mc", "ground_fake", "lost_mining_event",
    "new_ship_crew", "unknown_extra_ship",
))
def test_forged_early_turn_economy_abstains_without_pp_award(monkeypatch,tamper):
    import planets_lab.sim.early_pq_ppq_idle_pp_turn as mod
    original = mod.HostEngine.step

    def forged(self, game, orders, *, seed=0):
        out, events = original(self, game, orders, seed=seed)
        out = deepcopy(out)
        if tamper == "extra_mc": out.planets[30].cargo.megacredits += 1
        elif tamper == "ground_fake": out.planets[20].ground_duranium.amount += 1
        elif tamper == "lost_mining_event":
            events = tuple(x for x in events if x.phase != "mineral_mining")
        elif tamper == "new_ship_crew": out.ships[9].crew += 1
        elif tamper == "unknown_extra_ship":
            from planets_lab.core import Ship
            out.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        return out, events

    monkeypatch.setattr(mod.HostEngine, "step", forged)
    game, specs, ctx = fixture()
    original_game = deepcopy(game)
    out = run(game, specs, ctx)
    assert not out.supported and out.state is None
    assert out.player_pp_after == () and out.ship_receipts == ()
    assert game == original_game
