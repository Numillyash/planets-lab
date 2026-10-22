"""Bounded 2-3 turn Classic PBP/pointer/warehouse conservation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.classic_bounded_multiturn_carry import (
    STATUS, ClassicBaseTurnIntent, ClassicExplicitTurn,
    ClassicQueueCarryState, simulate_bounded_classic_carry,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from test_classic_joint_priority_standard_turn import fixture


def prepared(*, existing=8, limit=12, pbp=21, rounds=2):
    game, static, context = fixture(existing=existing, pbp=pbp)
    priority = replace(context.priority, ship_limit=limit)
    standard = replace(context.standard, ship_limit=limit)
    context = replace(context, priority=priority, standard=standard)
    carry = ClassicQueueCarryState(
        ship_limit=limit,
        last_standard_build_planet_id=context.standard.last_standard_build_planet_id,
        player_pbps=context.priority.player_pbps,
        all_base_warehouses=(
            (10, StandardComponentWarehouse()),
            (20, StandardComponentWarehouse()),
            (30, StandardComponentWarehouse()),
        ),
    )
    def order(pid):
        build = context.ordinary_queued.get(pid)
        return ClassicBaseTurnIntent(
            planet_id=pid,
            blueprint=build.blueprint if build else None,
            allowed_hull_ids=build.allowed_hull_ids if build else frozenset(),
        )
    plan = ClassicExplicitTurn(
        bases=tuple(order(pid) for pid in (10, 20, 30)),
        placement="builds_before_planetary",
    )
    return game, static, carry, (plan,) * rounds


def run(game, specs, carry, plans, **options):
    opts = dict(
        standard_rules_asserted=True,
        complete_all_turn_orders_and_warehouses_asserted=True,
        no_external_pbp_awards_or_interturn_mutations_asserted=True,
        no_combat_movement_clone_or_nonstandard_orders_asserted=True,
    )
    opts.update(options)
    return simulate_bounded_classic_carry(game, specs, carry, plans, **opts)


def test_two_turns_priority_then_standard_only_with_shared_finite_ids():
    game, specs, carry, plans = prepared()
    frozen = deepcopy((game, specs, carry, plans))
    out = run(game, specs, carry, plans)
    again = run(game, specs, carry, plans)
    assert out == again
    assert out.status == STATUS and out.supported
    assert out.state.turn == game.turn + 2
    assert len(out.turns) == 2
    first, second = out.turns
    assert first.queue_subphase == "PRIORITY_THEN_STANDARD"
    assert first.priority_ship_id == 9
    assert first.standard_ship_ids == (10,)
    assert first.allocated_ship_ids == (9, 10)
    assert first.pbps_after == ((1, 20), (2, 0))
    assert first.last_standard_pointer_after == 20
    assert second.queue_subphase == "STANDARD_ONLY"
    assert second.priority_ship_id is None
    assert second.standard_ship_ids == (11, 12)
    assert second.allocated_ship_ids == (11, 12)
    assert second.pbps_after == first.pbps_after
    assert second.last_standard_pointer_after == 20
    assert set(out.state.ships) == set(game.ships) | {9, 10, 11, 12}
    assert out.state.ships[9].owner_id == 1
    assert out.state.ships[10].owner_id == 2
    assert out.state.ships[11].owner_id == 1
    assert out.state.ships[12].owner_id == 2
    assert out.carry_after.player_pbps == ((1, 20), (2, 0))
    assert out.carry_after.last_standard_build_planet_id == 20
    assert out.carry_after.ship_limit == 12
    assert dict(out.carry_after.all_base_warehouses)[30] == StandardComponentWarehouse()
    assert all(row.planet_balance_exact for row in out.turns)
    assert not out.nuhost_execution_verified
    assert not out.host_queue_order_verified
    assert not out.player_pbps_independently_witnessed
    assert not out.standard_pointer_independently_witnessed
    assert not out.warehouses_independently_witnessed
    assert not out.independent_host_parity_verified
    assert (game, specs, carry, plans) == frozen


def test_third_turn_after_hard_limit_builds_zero_without_pointer_changes():
    game, specs, carry, plans = prepared(rounds=3)
    out = run(game, specs, carry, plans)
    assert out.supported
    assert out.state.turn == game.turn + 3
    assert [r.allocated_ship_ids for r in out.turns] == [
        (9, 10), (11, 12), (),
    ]
    assert out.turns[-1].last_standard_pointer_after == 20
    assert out.turns[-1].pbps_after == ((1, 20), (2, 0))


def test_priority_takes_only_last_slot_then_next_turn_no_standard_build():
    game, specs, carry, plans = prepared(existing=11, rounds=2)
    # "existing" ships 1-11 with hard cap 12; one priority build only.
    out = run(game, specs, carry, plans)
    assert out.supported
    assert out.turns[0].allocated_ship_ids == (12,)
    assert out.turns[0].last_standard_pointer_after == 10
    assert out.turns[1].allocated_ship_ids == ()
    assert out.turns[1].last_standard_pointer_after == 10
    assert out.carry_after.player_pbps == ((1, 20), (2, 0))


def test_instock_parts_are_carried_and_not_magically_replenished_between_turns():
    game, specs, carry, plans = prepared()
    stocked = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    carry = replace(carry, all_base_warehouses=(
        (10, stocked), (20, StandardComponentWarehouse()),
        (30, StandardComponentWarehouse()),
    ))
    out = run(game, specs, carry, plans)
    assert out.supported
    # First priority assembly depletes all stocked parts, and its
    # next standard build cannot use that first ship's old materials.
    assert out.turns[0].base_warehouses_after[0] == (
        10, StandardComponentWarehouse(
            hulls=((7, 0),), engines=((9, 0),),
            beams=((3, 0),), launchers=((2, 0),),
        ),
    )
    assert out.turns[1].base_warehouses_after[0][1].hulls == ((7, 0),)
    assert carry.all_base_warehouses[0] == (10, stocked)


def test_after_economy_placement_can_fund_first_turn_from_tax():
    game, specs, carry, plans = prepared()
    game.planets[10].cargo.megacredits = 259
    game.planets[20].cargo.megacredits = 259
    # Isolate the first turn's tax timing. With 259 MC at BOTH bases
    # the income funds this turn's 260-MC BOM but does not necessarily
    # fund a second identical ship in the following turn; that would
    # require another complete independent affordability hypothesis.
    one_turn = plans[:1]
    newplans = tuple(replace(p, placement="builds_after_planetary") for p in one_turn)
    before = run(game, specs, carry, one_turn)
    after = run(game, specs, carry, newplans)
    assert not before.supported
    assert after.supported
    assert all(row.planet_balance_exact for row in after.turns)


@pytest.mark.parametrize("case", (
    "last_turn_invalid_hull", "missing_one_plan", "many_turns",
    "new_pbp_eligible_remains", "different_base_owner",
    "missing_warehouse", "duplicate_warehouse",
    "phantom_component", "negative_stock", "missing_pbp_owner",
    "priority_contention", "missing_full_orders", "missing_no_external",
    "missing_no_other_actions", "missing_rules", "bool_seed",
    "new_queueless_base", "missing_idle_base",
    "duplicate_base", "wrong_hull_rights", "wrong_placement",
    "extra_stock_on_idle", "bad_pointer",
))
def test_incomplete_or_unattributable_sequence_abstains_entirely(case):
    game, specs, carry, plans = prepared()
    opts = {}
    if case == "last_turn_invalid_hull":
        last = list(plans[-1].bases)
        last[1] = replace(last[1], blueprint=replace(last[1].blueprint, hull_id=999))
        plans = (plans[0], replace(plans[-1], bases=tuple(last)))
    elif case == "missing_one_plan": plans = ()
    elif case == "many_turns": plans = plans * 5
    elif case == "new_pbp_eligible_remains":
        carry = replace(carry, player_pbps=((1, 22), (2, 0)))
    elif case == "different_base_owner": game.starbases[20].owner_id = 1
    elif case == "missing_warehouse":
        carry = replace(carry, all_base_warehouses=carry.all_base_warehouses[:2])
    elif case == "duplicate_warehouse":
        carry = replace(carry, all_base_warehouses=carry.all_base_warehouses+((10, StandardComponentWarehouse()),))
    elif case == "phantom_component":
        carry = replace(carry, all_base_warehouses=(
            (10, StandardComponentWarehouse(hulls=((999, 1),))),
            *carry.all_base_warehouses[1:],
        ))
    elif case == "negative_stock":
        carry = replace(carry, all_base_warehouses=(
            (10, StandardComponentWarehouse(hulls=((7, -1),))),
            *carry.all_base_warehouses[1:],
        ))
    elif case == "missing_pbp_owner":
        carry = replace(carry, player_pbps=((1, 21),))
    elif case == "priority_contention":
        carry = replace(carry, player_pbps=((1, 21), (2, 21)))
    elif case == "missing_full_orders":
        opts["complete_all_turn_orders_and_warehouses_asserted"] = False
    elif case == "missing_no_external":
        opts["no_external_pbp_awards_or_interturn_mutations_asserted"] = False
    elif case == "missing_no_other_actions":
        opts["no_combat_movement_clone_or_nonstandard_orders_asserted"] = False
    elif case == "missing_rules": opts["standard_rules_asserted"] = False
    elif case == "bool_seed": opts["seed"] = True
    elif case == "new_queueless_base":
        rows = list(plans[-1].bases)
        rows[2] = replace(rows[2], allowed_hull_ids=frozenset({7}))
        plans = (plans[0], replace(plans[-1], bases=tuple(rows)))
    elif case == "missing_idle_base":
        plans = (plans[0], replace(plans[1], bases=plans[1].bases[:2]))
    elif case == "duplicate_base":
        plans = (plans[0], replace(plans[1], bases=(
            plans[1].bases[0], plans[1].bases[0], plans[1].bases[2],
        )))
    elif case == "wrong_hull_rights":
        rows = list(plans[-1].bases)
        rows[1] = replace(rows[1], allowed_hull_ids=frozenset())
        plans = (plans[0], replace(plans[-1], bases=tuple(rows)))
    elif case == "wrong_placement":
        plans = (plans[0], replace(plans[-1], placement="actual_host_verified"))
    elif case == "extra_stock_on_idle":
        carry = replace(carry, all_base_warehouses=(
            *carry.all_base_warehouses[:2],
            (30, StandardComponentWarehouse(engines=((999, 2),))),
        ))
    elif case == "bad_pointer":
        carry = replace(carry, last_standard_build_planet_id=None)
    frozen = deepcopy((game, specs, carry, plans))
    result = run(game, specs, carry, plans, **opts)
    assert result.status == "ABSTAIN_CLASSIC_MULTITURN_CARRY"
    assert not result.supported
    assert result.state is None
    assert result.carry_after is None and result.turns == ()
    assert not result.nuhost_execution_verified
    assert (game, specs, carry, plans) == frozen


def test_owner_signed_player_orders_schema_still_unmodified():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert tuple(f.name for f in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset((
        "player_id", "ship_orders", "starbase_tech_orders",
    ))
