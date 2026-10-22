"""One exact late PQ/PPQ pb1 priority ship beyond the soft cap."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_ppq_priority_admission import MODES
from planets_lab.sim.late_pq_ppq_priority_ship_economy import (
    STATUS, PLACEMENTS, simulate_late_pq_ppq_priority_economic_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from test_late_pq_ppq_priority_admission import fixture


def run(game, specs, ctx, **kwargs):
    options = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_component_warehouse_and_hull_rights_asserted=True,
        no_other_ship_base_pp_or_combat_effects_asserted=True,
    )
    options.update(kwargs)
    return simulate_late_pq_ppq_priority_economic_turn(
        game, specs, ctx, **options,
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_late_ship_builds_beyond_soft_limit_with_distinct_pp_and_bom(mode, placement):
    state, specs, ctx = fixture(mode)
    original = deepcopy((state, specs, ctx))
    result = run(state, specs, ctx, placement=placement)
    assert result == run(state, specs, ctx, placement=placement)
    assert result.status == STATUS and result.supported
    assert result.state.turn == state.turn + 1
    assert len(state.ships) == ctx.soft_ship_limit == 8
    assert len(result.state.ships) == 9
    assert result.new_ship_id == 9 and result.winning_base_id == 10
    assert result.state.ships[9].owner_id == 1
    assert result.priority_mode == mode
    assert result.pp_cost == 2 and result.player_pp_after == ((1,1), (2,0))
    assert result.component_receipt.purchased.megacredits == 260
    assert result.component_receipt.purchased.duranium == 9
    assert result.component_receipt.purchased.tritanium == 13
    assert result.component_receipt.purchased.molybdenum == 6
    assert all(x.resource_balance_exact for x in result.planet_balances)
    assert len(result.planet_balances) == 3
    assert result.state.starbases == state.starbases
    assert not result.priority_order_independently_verified
    assert not result.server_accepted_order_verified
    assert not result.programmatic_ship_id_independently_verified
    assert not result.nuhost_execution_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified
    assert (state, specs, ctx) == original


def test_full_warehouse_pays_no_surface_mc_or_mineral_but_pp_costs_two():
    state, specs, ctx = fixture()
    warehouse = StandardComponentWarehouse(
        hulls=((7,1),), engines=((9,2),),
        beams=((3,2),), launchers=((2,1),),
    )
    orders = list(ctx.all_bases)
    orders[0] = replace(orders[0], order=replace(orders[0].order, warehouse=warehouse))
    ctx = replace(ctx, all_bases=tuple(orders))
    for resource in ("megacredits", "duranium", "tritanium", "molybdenum"):
        setattr(state.planets[10].cargo, resource, 0)
    out = run(state, specs, ctx)
    assert out.supported
    assert out.pp_cost == 2 and out.player_pp_after == ((1,1), (2,0))
    assert all(
        getattr(out.component_receipt.purchased, x) == 0
        for x in ("megacredits", "duranium", "tritanium", "molybdenum")
    )
    assert out.component_receipt.warehouse_after == StandardComponentWarehouse(
        hulls=((7,0),), engines=((9,0),),
        beams=((3,0),), launchers=((2,0),),
    )


def test_one_mc_short_is_funded_only_after_taxes_in_explicit_hypothesis():
    game, specs, ctx = fixture()
    game.planets[10].cargo.megacredits = 259
    frozen = deepcopy(game)
    early = run(game, specs, ctx, placement=PLACEMENTS[0])
    late = run(game, specs, ctx, placement=PLACEMENTS[1])
    assert not early.supported
    assert early.state is None and early.player_pp_after == ()
    assert late.supported
    assert late.planet_balances[0].taxes_collected > 0
    assert late.player_pp_after == ((1,1), (2,0))
    assert game == frozen


def test_priority_ships_quoted_with_1000kt_default_21_pp_limit():
    game, specs, ctx = fixture("PLANETARY_PPQ")
    specs.hulls[7] = replace(specs.hulls[7], mass=1100)
    ctx = replace(ctx, player_pp=((1,21), (2,0)))
    outcome = run(game, specs, ctx)
    assert outcome.supported
    assert outcome.pp_cost == 21
    assert outcome.player_pp_after == ((1,0), (2,0))


@pytest.mark.parametrize("bad", (
    "no_priority_pp", "no_full_warehouse", "no_standard_rule",
    "no_other_action_claim", "missing_one_base", "ordinary_second",
    "priority_competitor", "pb2", "custom_price", "below_soft",
    "not_enough_mc", "not_enough_duranium", "moving_ship",
    "unknown_component", "unknown_hull", "extra_metadata",
    "invalid_placement", "bool_seed",
))
def test_invalid_late_priority_economy_abstains_whole_turn(bad):
    game, specs, ctx = fixture()
    kw = {}
    bases = list(ctx.all_bases)
    if bad == "no_priority_pp": ctx = replace(ctx, player_pp=((1,1), (2,0)))
    elif bad == "no_full_warehouse":
        kw["complete_component_warehouse_and_hull_rights_asserted"] = False
    elif bad == "no_standard_rule": kw["standard_rules_asserted"] = False
    elif bad == "no_other_action_claim":
        kw["no_other_ship_base_pp_or_combat_effects_asserted"] = False
    elif bad == "missing_one_base": bases.pop()
    elif bad == "ordinary_second": bases[1] = replace(bases[1], order=bases[0].order)
    elif bad == "priority_competitor":
        bases[1] = replace(bases[1], order=bases[0].order, priority_code="pb1")
    elif bad == "pb2": bases[0] = replace(bases[0], priority_code="pb2")
    elif bad == "custom_price": ctx = replace(ctx, default_priority_cost_rule_asserted=False)
    elif bad == "below_soft": ctx = replace(ctx, soft_ship_limit=10)
    elif bad == "not_enough_mc": game.planets[10].cargo.megacredits = 0
    elif bad == "not_enough_duranium": game.planets[10].cargo.duranium = 0
    elif bad == "moving_ship": game.ships[1].warp = 9
    elif bad == "unknown_component":
        bases[0] = replace(bases[0], order=replace(
            bases[0].order, warehouse=StandardComponentWarehouse(hulls=((999,1),)),
        ))
    elif bad == "unknown_hull": specs.hulls.pop(7)
    elif bad == "extra_metadata": game.metadata["custom"] = True
    elif bad == "invalid_placement": kw["placement"] = "claimed_nuhost_causal"
    elif bad == "bool_seed": kw["seed"] = True
    if tuple(bases) != ctx.all_bases:
        ctx = replace(ctx, all_bases=tuple(bases))
    frozen = deepcopy((game, specs, ctx))
    out = run(game, specs, ctx, **kw)
    assert not out.supported
    assert out.status == "ABSTAIN_LATE_PQ_PPQ_PRIORITY_ECONOMIC_TURN"
    assert out.state is None
    assert out.component_receipt is None and out.player_pp_after == ()
    assert out.planet_balances == () and out.economy_events == ()
    assert (game, specs, ctx) == frozen


@pytest.mark.parametrize("corruption", (
    "bonus_mc", "undocumented_ground", "missing_mine_receipt",
    "new_ship_crew", "phantom_ship",
))
def test_forged_result_or_economic_event_cannot_create_partial_priority_ship(monkeypatch, corruption):
    import planets_lab.sim.late_pq_ppq_priority_ship_economy as mod
    original = mod.HostEngine.step

    def bad_step(self, game, orders, *, seed=0):
        after, events = original(self, game, orders, seed=seed)
        after = deepcopy(after)
        if corruption == "bonus_mc":
            after.planets[20].cargo.megacredits += 1
        elif corruption == "undocumented_ground":
            after.planets[20].ground_duranium.amount += 1
        elif corruption == "missing_mine_receipt":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        elif corruption == "new_ship_crew":
            after.ships[9].crew += 1
        elif corruption == "phantom_ship":
            from planets_lab.core import Ship
            after.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        return after, events

    monkeypatch.setattr(mod.HostEngine, "step", bad_step)
    game, specs, ctx = fixture()
    original_game = deepcopy(game)
    out = run(game, specs, ctx)
    assert not out.supported
    assert out.state is None and out.player_pp_after == ()
    assert game == original_game


def test_canonical_signed_owner_orders_and_14_phases_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    assert len(PlanetaryHostPipeline().phases) == 14
    assert tuple(field.name for field in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset((
        "player_id", "ship_orders", "starbase_tech_orders",
    ))
