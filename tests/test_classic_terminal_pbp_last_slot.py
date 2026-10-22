"""Classic unique-highest-PBP contention for the final hard ship slot."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.classic_terminal_pbp_last_slot import (
    STATUS, POLICY, PLACEMENTS, ClassicContestedBase,
    ClassicTerminalContext, simulate_classic_terminal_priority_slot,
)
from planets_lab.sim.classic_uncontested_priority_pbp import PriorityShipOrder
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from test_classic_standard_pointer_economy_turn import context as ordinary_game


def data():
    state, specs, _, designs = ordinary_game(existing=9)
    ctx = ClassicTerminalContext(
        ship_limit=10,
        player_pbps=((1, 25), (2, 22)),
        bases=(
            ClassicContestedBase(
                10, PriorityShipOrder(
                    blueprint=designs[10].blueprint,
                    warehouse=StandardComponentWarehouse(),
                    allowed_hull_ids=frozenset({7}),
                ),
            ),
            ClassicContestedBase(
                20, PriorityShipOrder(
                    blueprint=designs[20].blueprint,
                    warehouse=StandardComponentWarehouse(),
                    allowed_hull_ids=frozenset({7}),
                ),
            ),
            ClassicContestedBase(30, None),
        ),
        last_standard_build_planet_id=10,
        full_fleet_base_owner_pbp_scope_asserted=True,
        no_codes_clones_or_extra_build_windows_asserted=True,
        unique_highest_pbp_hypothesis_asserted=True,
    )
    return state, specs, ctx


def run(game, specs, ctx, **changes):
    opts = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_warehouse_and_hull_rights_asserted=True,
        no_other_ship_base_or_combat_actions_asserted=True,
    )
    opts.update(changes)
    return simulate_classic_terminal_priority_slot(game, specs, ctx, **opts)


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_unique_higher_pbp_wins_last_classic_id_without_changing_pointer(placement):
    game, specs, ctx = data()
    original = deepcopy((game, specs, ctx))
    out = run(game, specs, ctx, placement=placement)
    assert out == run(game, specs, ctx, placement=placement)
    assert out.supported and out.status == STATUS
    assert out.state.turn == game.turn + 1
    assert out.winning_base_id == 10 and out.winning_ship_id == 10
    assert out.pbp_cost == 1
    assert out.pbps_after == ((1, 24), (2, 22))
    assert out.last_standard_pointer_after == 10
    assert len(out.state.ships) == 10
    assert out.state.ships[10].owner_id == 1
    assert out.selected_build_balance.purchased.megacredits == 260
    assert out.selected_build_balance.purchased.duranium == 9
    assert out.nonwinner_warehouses == ((20, StandardComponentWarehouse()),)
    assert all(p.resource_balance_exact for p in out.planet_balances)
    assert not out.priority_rank_independently_verified
    assert not out.pbp_balances_independently_verified
    assert not out.ship_id_independently_verified
    assert not out.nuhost_execution_verified
    assert not out.nuhost_phase_placement_verified
    assert not out.independent_host_parity_verified
    assert (game, specs, ctx) == original


def test_other_player_can_win_if_unique_highest_score_reverses():
    game, specs, ctx = data()
    ctx = replace(ctx, player_pbps=((1, 22), (2, 25)))
    result = run(game, specs, ctx)
    assert result.supported
    assert result.winning_base_id == 20
    assert result.winning_ship_id == 10
    assert result.state.ships[10].owner_id == 2
    assert result.pbps_after == ((1, 22), (2, 24))
    assert result.last_standard_pointer_after == 10


def test_higher_mass_consumes_capped_pbp_but_not_losers_points():
    game, specs, ctx = data()
    specs.hulls[7] = replace(specs.hulls[7], mass=1111)
    out = run(game, specs, ctx)
    assert out.supported
    assert out.pbp_cost == 20
    assert out.pbps_after == ((1, 5), (2, 22))


def test_after_economy_tax_can_fund_last_slot_hypothesis_only():
    game, specs, ctx = data()
    game.planets[10].cargo.megacredits = 259
    early = run(game, specs, ctx)
    late = run(game, specs, ctx, placement=PLACEMENTS[1])
    assert not early.supported
    assert late.supported
    assert late.winning_ship_id == 10


@pytest.mark.parametrize("case", (
    "tie", "one_eligible", "winner_no_queued_base",
    "two_bases_same_winner", "missing_base", "duplicate_base",
    "priority_pb_code", "clone", "wrong_ownership",
    "invalid_policy", "policy_not_asserted", "missing_scope",
    "missing_no_effect_assertion", "owner_missing", "duplicate_owner",
    "negative_pbp", "bool_pbp", "cap_full", "two_free_slots",
    "ship_id_bool", "no_money", "phantom_warehouse",
    "missing_hull", "mission", "metadata", "bad_placement",
    "missing_rules", "missing_component_assert", "missing_action_assert",
    "boolean_seed", "invalid_pointer",
))
def test_unknown_contest_and_scope_fails_without_partial_output(case):
    game, specs, ctx = data()
    opts = {}
    rows = list(ctx.bases)
    if case == "tie": ctx = replace(ctx, player_pbps=((1, 25), (2, 25)))
    elif case == "one_eligible": ctx = replace(ctx, player_pbps=((1, 25), (2, 20)))
    elif case == "winner_no_queued_base": rows[0] = replace(rows[0], queued=None)
    elif case == "two_bases_same_winner": rows[2] = replace(rows[2], queued=rows[0].queued)
    elif case == "missing_base": rows = rows[:2]
    elif case == "duplicate_base": rows[2] = rows[0]
    elif case == "priority_pb_code": rows[0] = replace(rows[0], pb_code=1)
    elif case == "clone": rows[1] = replace(rows[1], cloning=True)
    elif case == "wrong_ownership": game.starbases[20].owner_id = 1
    elif case == "invalid_policy": ctx = replace(ctx, ranking_policy="REAL_NUHOST_PROVEN")
    elif case == "policy_not_asserted": ctx = replace(ctx, unique_highest_pbp_hypothesis_asserted=False)
    elif case == "missing_scope": ctx = replace(ctx, full_fleet_base_owner_pbp_scope_asserted=False)
    elif case == "missing_no_effect_assertion":
        ctx = replace(ctx, no_codes_clones_or_extra_build_windows_asserted=False)
    elif case == "owner_missing": ctx = replace(ctx, player_pbps=((1, 25),))
    elif case == "duplicate_owner": ctx = replace(ctx, player_pbps=((1, 25), (1, 22)))
    elif case == "negative_pbp": ctx = replace(ctx, player_pbps=((1, -1), (2, 22)))
    elif case == "bool_pbp": ctx = replace(ctx, player_pbps=((1, True), (2, 22)))
    elif case == "cap_full":
        from planets_lab.core import Ship
        game.ships[10] = Ship(id=10, owner_id=1, hull_id=7, x=100, y=100)
    elif case == "two_free_slots": ctx = replace(ctx, ship_limit=11)
    elif case == "ship_id_bool": ctx = replace(ctx, ship_limit=True)
    elif case == "no_money": game.planets[10].cargo.megacredits = 0
    elif case == "phantom_warehouse":
        rows[0] = replace(rows[0], queued=replace(
            rows[0].queued, warehouse=StandardComponentWarehouse(hulls=((999, 1),)),
        ))
    elif case == "missing_hull": specs.hulls.pop(7)
    elif case == "mission": game.ships[1].mission = "tow"
    elif case == "metadata": game.metadata["special"] = True
    elif case == "bad_placement": opts["placement"] = "verified_real_queue"
    elif case == "missing_rules": opts["standard_rules_asserted"] = False
    elif case == "missing_component_assert":
        opts["complete_warehouse_and_hull_rights_asserted"] = False
    elif case == "missing_action_assert":
        opts["no_other_ship_base_or_combat_actions_asserted"] = False
    elif case == "boolean_seed": opts["seed"] = True
    elif case == "invalid_pointer":
        ctx = replace(ctx, last_standard_build_planet_id=None)
    if rows != list(ctx.bases):
        ctx = replace(ctx, bases=tuple(rows))
    saved = deepcopy((game, specs, ctx))
    out = run(game, specs, ctx, **opts)
    assert not out.supported
    assert out.status == "ABSTAIN_CLASSIC_TERMINAL_SLOT"
    assert out.state is None and out.selected_build_balance is None
    assert out.pbps_after == () and out.planet_balances == ()
    assert (game, specs, ctx) == saved


@pytest.mark.parametrize("tamper", (
    "alter_winning_crew", "extra_ship", "mc_gain", "ground_gain", "remove_mine_events",
))
def test_final_economy_forgery_abstains_entire_terminal_build(monkeypatch, tamper):
    import planets_lab.sim.classic_terminal_pbp_last_slot as mod
    original = mod.HostEngine.step

    def corrupt(self, state, orders, *, seed=0):
        after, events = original(self, state, orders, seed=seed)
        after = deepcopy(after)
        if tamper == "alter_winning_crew":
            after.ships[10].crew += 1
        elif tamper == "extra_ship":
            from planets_lab.core import Ship
            after.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        elif tamper == "mc_gain":
            after.planets[20].cargo.megacredits += 1
        elif tamper == "ground_gain":
            after.planets[20].ground_duranium.amount += 1
        elif tamper == "remove_mine_events":
            events = tuple(ev for ev in events if ev.phase != "mineral_mining")
        return after, events

    monkeypatch.setattr(mod.HostEngine, "step", corrupt)
    game, specs, ctx = data()
    initial = deepcopy(game)
    out = run(game, specs, ctx)
    assert not out.supported
    assert out.state is None and out.pbps_after == ()
    assert game == initial


def test_legacy_owner_signed_schema_is_not_extended():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert tuple(x.name for x in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
