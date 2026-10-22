"""Conditional Classic priority PBP + ordinary pointer queue + full economy."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.classic_joint_priority_standard_turn import (
    STATUS, PLACEMENTS, ClassicJointContext,
    simulate_classic_joint_priority_standard_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from test_classic_standard_pointer_economy_turn import context as basic_context
from test_classic_uncontested_priority_pbp import prepare as priority_fixture


def fixture(*, existing=8, pbp=21):
    state, specs, standard, ordinary = basic_context(existing=existing)
    _, _, priority = priority_fixture(existing=existing, pbp=pbp)
    standard = replace(standard, player_pbps=priority.player_pbps)
    return state, specs, ClassicJointContext(priority, standard, ordinary)


def execute(state, specs, context, **overrides):
    opts = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_queue_and_component_scope_asserted=True,
        no_other_ship_or_base_actions_asserted=True,
    )
    opts.update(overrides)
    return simulate_classic_joint_priority_standard_turn(state, specs, context, **opts)


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_one_priority_then_one_standard_reconciles_all_resources(placement):
    game, specs, context = fixture()
    frozen = deepcopy((game, specs, context))
    result = execute(game, specs, context, placement=placement)
    repeat = execute(game, specs, context, placement=placement)
    assert result == repeat
    assert result.supported and result.status == STATUS
    assert result.state.turn == game.turn + 1
    assert result.priority_base_id == 10 and result.priority_ship_id == 9
    assert result.priority_pbp_cost == 1
    assert result.pbps_after == ((1, 20), (2, 0))
    assert result.selected_standard_bases == (20,)
    assert result.selected_standard_ship_ids == (10,)
    assert result.last_standard_pointer_after == 20
    assert result.state.ships[9].owner_id == 1
    assert result.state.ships[10].owner_id == 2
    assert result.state.ships[9].x == 100
    assert result.state.ships[10].x == 300
    assert len(result.build_balances) == 2
    assert len(result.planet_balances) == 3
    assert all(x.resource_balance_exact for x in result.planet_balances)
    assert [r.starbase_planet_id for r in result.build_balances] == [10, 20]
    assert [r.ship_id for r in result.build_balances] == [9, 10]
    assert all(r.material_debit_exact and r.warehouse_debit_exact for r in result.build_balances)
    assert all(r.purchased.megacredits == 260 for r in result.build_balances)
    assert not result.queue_and_pbp_independently_witnessed
    assert not result.ship_ids_independently_witnessed
    assert not result.nuhost_execution_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified
    assert (game, specs, context) == frozen


def test_only_one_remaining_slot_priority_wins_and_pointer_does_not_advance():
    game, specs, context = fixture(existing=9)
    outcome = execute(game, specs, context)
    assert outcome.supported
    assert outcome.priority_ship_id == 10
    assert outcome.selected_standard_bases == ()
    assert outcome.selected_standard_ship_ids == ()
    assert len(outcome.build_balances) == 1
    assert outcome.last_standard_pointer_after == context.standard.last_standard_build_planet_id
    assert set(outcome.state.ships) == set(game.ships) | {10}
    assert dict(outcome.warehouse_after)[20] == context.ordinary_queued[20].warehouse


def test_mixed_stocks_reduce_priority_cost_without_forgiving_standard_debit():
    game, specs, context = fixture()
    stocked = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    priority_orders = dict(context.priority.queued_base_orders)
    priority_orders[10] = replace(priority_orders[10], warehouse=stocked)
    ordinary = dict(context.ordinary_queued)
    ordinary[10] = replace(ordinary[10], warehouse=stocked)
    context = replace(context, priority=replace(
        context.priority, queued_base_orders=priority_orders,
    ), ordinary_queued=ordinary)
    out = execute(game, specs, context)
    assert out.supported
    assert out.build_balances[0].purchased.megacredits == 0
    assert out.build_balances[1].purchased.megacredits == 260
    assert dict(out.warehouse_after)[10].hulls == ((7, 0),)
    assert dict(out.warehouse_after)[20] == out.build_balances[1].warehouse_after


def test_after_economy_tax_can_finance_priority_and_standard_full_turn():
    game, specs, ctx = fixture()
    game.planets[10].cargo.megacredits = 259
    game.planets[20].cargo.megacredits = 259
    start = deepcopy(game)
    before = execute(game, specs, ctx, placement=PLACEMENTS[0])
    after = execute(game, specs, ctx, placement=PLACEMENTS[1])
    assert not before.supported and before.state is None
    assert after.supported
    assert all(x.taxes_collected > 0 for x in after.planet_balances[:2])
    assert game == start


@pytest.mark.parametrize("problem", (
    "priority_22", "second_eligible_owner", "priority_second_candidate",
    "priority_new_base", "missing_standard_base", "priority_wrong_warehouse",
    "priority_wrong_blueprint", "missing_ordinary_order",
    "priority_missing_owner", "standard_pbp_mismatch",
    "standard_ship_count_mismatch", "standard_owner_mismatch",
    "priority_storm", "priority_fcode", "clone",
    "missing_priority_assertion", "missing_standard_scope",
    "no_rules", "no_stock_scope", "other_actions",
    "bad_phase", "bool_seed", "priority_no_money", "standard_no_money",
    "priority_phantom_component", "unknown_priority_hull",
    "priority_competing_regular", "hard_limit_full",
))
def test_ambiguous_or_invalid_context_abstains_atomically(problem):
    game, specs, ctx = fixture()
    kwargs = {}
    if problem == "priority_22":
        ctx = replace(ctx, priority=replace(
            ctx.priority, player_pbps=((1, 22), (2, 0)),
        ), standard=replace(ctx.standard, player_pbps=((1, 22), (2, 0))))
    elif problem == "second_eligible_owner":
        ctx = replace(ctx, priority=replace(
            ctx.priority, player_pbps=((1, 21), (2, 21)),
        ), standard=replace(ctx.standard, player_pbps=((1, 21), (2, 21))))
    elif problem == "priority_second_candidate":
        req = dict(ctx.priority.queued_base_orders)
        req[30] = req[10]
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=req))
    elif problem == "priority_new_base":
        req = dict(ctx.priority.queued_base_orders)
        req[99] = req[10]
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=req))
    elif problem == "missing_standard_base":
        ctx = replace(ctx, standard=replace(ctx.standard, bases=ctx.standard.bases[:2]))
    elif problem == "priority_wrong_warehouse":
        req = dict(ctx.priority.queued_base_orders)
        req[10] = replace(req[10], warehouse=StandardComponentWarehouse(hulls=((7, 1),)))
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=req))
    elif problem == "priority_wrong_blueprint":
        req = dict(ctx.priority.queued_base_orders)
        req[10] = replace(req[10], blueprint=replace(req[10].blueprint, beam_count=1))
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=req))
    elif problem == "missing_ordinary_order":
        q = dict(ctx.ordinary_queued)
        q.pop(20)
        ctx = replace(ctx, ordinary_queued=q)
    elif problem == "priority_missing_owner":
        ctx = replace(ctx, priority=replace(ctx.priority, player_pbps=((1, 21),)))
    elif problem == "standard_pbp_mismatch":
        ctx = replace(ctx, standard=replace(ctx.standard, player_pbps=((1, 20), (2, 0))))
    elif problem == "standard_ship_count_mismatch":
        ctx = replace(ctx, standard=replace(ctx.standard, current_ship_count=9))
    elif problem == "standard_owner_mismatch":
        rows = list(ctx.standard.bases)
        rows[0] = replace(rows[0], owner_id=2)
        ctx = replace(ctx, standard=replace(ctx.standard, bases=tuple(rows)))
    elif problem == "priority_storm":
        game.metadata["ion_storms_turned_on"] = True
    elif problem == "priority_fcode":
        rows = list(ctx.standard.bases)
        rows[0] = replace(rows[0], priority_build_code=1)
        ctx = replace(ctx, standard=replace(ctx.standard, bases=tuple(rows)))
    elif problem == "clone":
        rows = list(ctx.standard.bases)
        rows[0] = replace(rows[0], clone_ordered=True)
        ctx = replace(ctx, standard=replace(ctx.standard, bases=tuple(rows)))
    elif problem == "missing_priority_assertion":
        ctx = replace(ctx, priority=replace(
            ctx.priority, exact_single_precombat_priority_subphase_asserted=False,
        ))
    elif problem == "missing_standard_scope":
        ctx = replace(ctx, standard=replace(ctx.standard, complete_starbase_roster_asserted=False))
    elif problem == "no_rules": kwargs["standard_rules_asserted"] = False
    elif problem == "no_stock_scope": kwargs["complete_queue_and_component_scope_asserted"] = False
    elif problem == "other_actions": kwargs["no_other_ship_or_base_actions_asserted"] = False
    elif problem == "bad_phase": kwargs["placement"] = "NUHOST_VERIFIED"
    elif problem == "bool_seed": kwargs["seed"] = True
    elif problem == "priority_no_money": game.planets[10].cargo.megacredits = 0
    elif problem == "standard_no_money": game.planets[20].cargo.megacredits = 0
    elif problem == "priority_phantom_component":
        q = dict(ctx.priority.queued_base_orders)
        q[10] = replace(q[10], warehouse=StandardComponentWarehouse(hulls=((999, 1),)))
        ordinary = dict(ctx.ordinary_queued)
        ordinary[10] = replace(ordinary[10], warehouse=q[10].warehouse)
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=q), ordinary_queued=ordinary)
    elif problem == "unknown_priority_hull":
        del specs.hulls[7]
    elif problem == "priority_competing_regular":
        q = dict(ctx.priority.queued_base_orders)
        q[30] = q[10]
        ordinary = dict(ctx.ordinary_queued)
        ordinary[30] = ordinary[10]
        rows = tuple(replace(r, ordinary_ship_queued=True) if r.planet_id == 30 else r for r in ctx.standard.bases)
        ctx = replace(ctx, priority=replace(ctx.priority, queued_base_orders=q), standard=replace(ctx.standard, bases=rows), ordinary_queued=ordinary)
    elif problem == "hard_limit_full":
        # Priority cannot begin at the hard limit, even with 21 PBP.
        from planets_lab.core import Ship
        game.ships[9] = Ship(id=9, owner_id=1, hull_id=7, x=100, y=100)
        game.ships[10] = Ship(id=10, owner_id=1, hull_id=7, x=100, y=100)
        ctx = replace(ctx, standard=replace(ctx.standard, current_ship_count=10))
    frozen = deepcopy((game, specs, ctx))
    result = execute(game, specs, ctx, **kwargs)
    assert result.status == "ABSTAIN_CLASSIC_JOINT_TURN"
    assert not result.supported
    assert result.state is None and result.build_balances == ()
    assert result.planet_balances == () and result.economic_events == ()
    assert result.pbps_after == () and result.warehouse_after == ()
    assert (game, specs, ctx) == frozen


@pytest.mark.parametrize("fault", (
    "extra_economy_ship", "changed_priority_crew",
    "money_forged", "ground_forged", "mine_receipt_removed",
))
def test_forged_state_or_events_cannot_partially_pass(monkeypatch, fault):
    import planets_lab.sim.classic_joint_priority_standard_turn as mod
    real_step = mod.HostEngine.step

    def mutate(self, before, orders, *, seed=0):
        after, events = real_step(self, before, orders, seed=seed)
        after = deepcopy(after)
        if fault == "extra_economy_ship":
            from planets_lab.core import Ship
            after.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        elif fault == "changed_priority_crew":
            after.ships[9].crew += 1
        elif fault == "money_forged":
            after.planets[20].cargo.megacredits += 1
        elif fault == "ground_forged":
            after.planets[20].ground_duranium.amount += 1
        elif fault == "mine_receipt_removed":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        return after, events

    monkeypatch.setattr(mod.HostEngine, "step", mutate)
    game, specs, ctx = fixture()
    frozen = deepcopy(game)
    out = execute(game, specs, ctx)
    assert not out.supported and out.state is None
    assert out.build_balances == () and out.pbps_after == ()
    assert game == frozen


def test_user_signed_owner_orders_and_original_economy_remain_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    assert len(PlanetaryHostPipeline().phases) == 14
    assert tuple(f.name for f in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
