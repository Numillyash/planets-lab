"""Late PQ waiting -> exact external loss -> one build -> full-cap logistics."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_capped_existing_fleet_cargo import CappedFleetCargoTurn
from planets_lab.sim.late_pq_capped_no_build_carry import (
    simulate_soft_capped_pq_no_build_carry,
)
from planets_lab.sim.late_pq_external_loss_multiturn import (
    LatePQExplicitTurn, LatePQTurnBase,
)
from planets_lab.sim.late_pq_external_regular_economy import (
    LatePQBase, LatePQContext, simulate_late_pq_external_selected_economic_turn,
)
from planets_lab.sim.late_pq_mixed_calendar import (
    STATUS, simulate_mixed_late_pq_wait_loss_build_fleet_calendar,
)
from test_late_pq_capped_no_build_carry import fixture_capped
from test_late_pq_capped_existing_fleet_cargo import orders as fleet_orders


def setup():
    state, specs, carry, standard_queue = fixture_capped()
    specs.engines[9] = replace(
        specs.engines[9],
        warp_fuel_factors=(0, 2000, 4000, 10000, 20000,
                           50000, 80000, 130000, 160000, 180000),
    )
    waiting = (standard_queue[0], standard_queue[0])
    stopped = simulate_soft_capped_pq_no_build_carry(
        state, specs, carry, waiting,
        standard_rules_asserted=True,
        complete_owner_planet_base_fleet_and_queue_roster_asserted=True,
        no_priority_clone_mining_stations_or_external_actions_asserted=True,
        default_no_pp_income_or_regular_pp_spend_asserted=True,
    )
    assert stopped.supported
    after_loss = stopped.state.clone()
    after_loss.ships.pop(1)
    loss_build = LatePQExplicitTurn(
        bases=tuple(LatePQTurnBase(
            p.planet_id, p.blueprint, p.allowed_hull_ids,
        ) for p in waiting[-1].all_bases),
        selected_planet_id=10, selected_ship_id=1,
        placement="late_pq_build_before_economy",
        external_removed_ship_id=1,
        externally_supplied_preturn_state=after_loss,
        external_single_inert_ship_loss_asserted=True,
    )
    stock = dict(carry.all_base_warehouses)
    context = LatePQContext(
        soft_ship_limit=carry.soft_ship_limit,
        selected_planet_id=loss_build.selected_planet_id,
        selected_ship_id=loss_build.selected_ship_id,
        all_bases=tuple(LatePQBase(
            row.planet_id, stock[row.planet_id], row.blueprint,
            row.allowed_hull_ids if row.blueprint else None,
        ) for row in loss_build.bases),
        player_pp=carry.owner_pp,
        complete_fleet_planets_all_buildable_bases_and_warehouses_asserted=True,
        caller_explicit_random_selected_base_asserted=True,
        no_priority_cloning_mining_stations_or_other_actions_asserted=True,
        default_regular_zero_pp_no_idle_pp_income_asserted=True,
    )
    built = simulate_late_pq_external_selected_economic_turn(
        after_loss, specs, context,
        placement=loss_build.placement,
        standard_rules_asserted=True,
        full_independent_economic_inventory_asserted=True,
    )
    assert built.supported
    fleets = (
        CappedFleetCargoTurn(
            ordinary_queue=standard_queue[1],
            all_ship_orders=fleet_orders(built.state),
            active_ship_id=10, placement="load_move_before_economy",
            no_other_fleet_or_host_actions_asserted=True,
        ),
        CappedFleetCargoTurn(
            ordinary_queue=standard_queue[1],
            all_ship_orders=fleet_orders(
                built.state, dest=320, transfer=False,
            ),
            active_ship_id=10, placement="economy_before_load_move",
            no_other_fleet_or_host_actions_asserted=True,
        ),
    )
    return state, specs, carry, waiting, loss_build, fleets


def run(state, specs, carry, waiting, external, fleet, **kwargs):
    flags = dict(
        full_state_and_all_queue_rosters_asserted=True,
        independently_sourced_external_loss_boundary_asserted=True,
        no_other_priority_clones_miners_combat_or_external_changes_asserted=True,
        standard_rules_asserted=True,
    )
    flags.update(kwargs)
    return simulate_mixed_late_pq_wait_loss_build_fleet_calendar(
        state, specs, carry, waiting, external, fleet, **flags,
    )


@pytest.mark.parametrize("placement", (
    "late_pq_build_before_economy", "late_pq_build_after_economy",
))
def test_complete_wait_loss_rebuild_then_two_capped_cargo_flights(placement):
    state, specs, carry, waiting, external, fleet = setup()
    external = replace(external, placement=placement)
    frozen = deepcopy((state, specs, carry, waiting, external, fleet))
    out = run(state, specs, carry, waiting, external, fleet)
    assert out.supported and out.status == STATUS, out.reason
    assert out == run(state, specs, carry, waiting, external, fleet)
    assert out.state.turn == state.turn + 2 + 1 + 2
    assert out.state.ships[1].owner_id == 1
    assert out.state.ships[1].engine_id == 9
    assert out.state.ships[10].owner_id == 2
    assert (out.state.ships[10].x, out.state.ships[10].y) == (320, 300)
    assert out.external_removed_ship_id == 1
    assert len(out.state.ships) == carry.soft_ship_limit == 10
    assert len(out.waiting_turns) == 2
    assert len(out.fleet_turns) == 2
    assert out.build.ship_receipt.ship_id == 1
    assert all(all(b.resource_balance_exact for b in x.planet_balances)
               for x in out.waiting_turns)
    assert all(all(b.resource_balance_exact for b in t.planet_balances)
               for t in out.fleet_turns)
    assert all(t.built_ship_ids == () for t in out.fleet_turns)
    assert out.carry_after.owner_pp == carry.owner_pp
    assert len(out.carry_after.all_base_warehouses) == len(carry.all_base_warehouses)
    assert not out.external_ship_loss_independently_verified
    assert not out.pq_winning_base_verified
    assert not out.nuhost_phase_placement_verified
    assert not out.accepted_host_orders_verified
    assert not out.independent_host_parity_verified
    assert (state, specs, carry, waiting, external, fleet) == frozen


@pytest.mark.parametrize("case", (
    "no_external_snapshot", "no_loss_claim", "bool_loss_id",
    "wrong_loss_id", "two_ships_lost", "ship_added", "planet_mc_changed",
    "base_owner_changed", "turn_advanced", "not_inert_removed_ship",
    "loss_with_cargo", "queue_modified", "duplicate_external_base",
    "builder_not_queued", "not_lowest_ship_id",
    "no_complete_state", "no_external_claim", "no_other_actions",
    "no_standard", "boolean_seed", "empty_wait", "empty_fleet",
    "late_fleet_wrong_ship", "late_fleet_tech", "late_fleet_missing_owner",
))
def test_inconsistent_interstage_contract_abstains_without_any_stage_outputs(case):
    state, specs, carry, waiting, external, fleet = setup()
    wait = list(waiting)
    plan = list(deepcopy(fleet))
    kwargs = {}
    if case == "no_external_snapshot":
        external = replace(external, externally_supplied_preturn_state=None)
    elif case == "no_loss_claim":
        external = replace(external, external_single_inert_ship_loss_asserted=False)
    elif case == "bool_loss_id":
        external = replace(external, external_removed_ship_id=True)
    elif case == "wrong_loss_id":
        external = replace(external, external_removed_ship_id=2)
    elif case == "two_ships_lost":
        after = external.externally_supplied_preturn_state.clone()
        after.ships.pop(2)
        external = replace(external, externally_supplied_preturn_state=after)
    elif case == "ship_added":
        after = external.externally_supplied_preturn_state.clone()
        after.ships[42] = deepcopy(after.ships[2])
        after.ships[42].id = 42
        external = replace(external, externally_supplied_preturn_state=after)
    elif case == "planet_mc_changed":
        after = external.externally_supplied_preturn_state.clone()
        after.planets[10].cargo.megacredits += 1
        external = replace(external, externally_supplied_preturn_state=after)
    elif case == "base_owner_changed":
        after = external.externally_supplied_preturn_state.clone()
        after.starbases[20].owner_id = 1
        external = replace(external, externally_supplied_preturn_state=after)
    elif case == "turn_advanced":
        after = external.externally_supplied_preturn_state.clone()
        after.turn += 1
        external = replace(external, externally_supplied_preturn_state=after)
    elif case == "not_inert_removed_ship":
        state.ships[1].warp = 8
    elif case == "loss_with_cargo":
        state.ships[1].cargo.megacredits = 1
    elif case == "queue_modified":
        rows = list(external.bases)
        rows[0] = replace(rows[0], blueprint=None, allowed_hull_ids=frozenset())
        external = replace(external, bases=tuple(rows))
    elif case == "duplicate_external_base":
        rows = list(external.bases)
        rows[1] = rows[0]
        external = replace(external, bases=tuple(rows))
    elif case == "builder_not_queued":
        external = replace(external, selected_planet_id=30)
    elif case == "not_lowest_ship_id":
        external = replace(external, selected_ship_id=77)
    elif case == "no_complete_state":
        kwargs["full_state_and_all_queue_rosters_asserted"] = False
    elif case == "no_external_claim":
        kwargs["independently_sourced_external_loss_boundary_asserted"] = False
    elif case == "no_other_actions":
        kwargs["no_other_priority_clones_miners_combat_or_external_changes_asserted"] = False
    elif case == "no_standard":
        kwargs["standard_rules_asserted"] = False
    elif case == "boolean_seed":
        kwargs["seed"] = True
    elif case == "empty_wait":
        wait = []
    elif case == "empty_fleet":
        plan = []
    elif case == "late_fleet_wrong_ship":
        plan[1] = replace(plan[1], active_ship_id=999)
    elif case == "late_fleet_tech":
        own = plan[1].all_ship_orders.by_player[2]
        plan[1].all_ship_orders.by_player[2] = replace(
            own, starbase_tech_orders=("unknown",),
        )
    elif case == "late_fleet_missing_owner":
        plan[1].all_ship_orders.by_player.pop(1)
    frozen = deepcopy((state, specs, carry, tuple(wait), external, tuple(plan)))
    result = run(state, specs, carry, tuple(wait), external, tuple(plan), **kwargs)
    assert not result.supported
    assert result.state is None and result.carry_after is None
    assert result.waiting_turns == () and result.fleet_turns == ()
    assert result.build is None and result.external_removed_ship_id is None
    assert (state, specs, carry, tuple(wait), external, tuple(plan)) == frozen


@pytest.mark.parametrize("stage", ("wait", "build", "fleet"))
def test_corrupt_interstage_component_output_forces_global_abstention(monkeypatch, stage):
    import planets_lab.sim.late_pq_mixed_calendar as module
    state, specs, carry, wait, external, fleet = setup()
    if stage == "wait":
        actual = module.simulate_soft_capped_pq_no_build_carry
        def forged(*args, **kwargs):
            out = actual(*args, **kwargs)
            return replace(out, carry_after=replace(
                out.carry_after, owner_pp=((1, 99), (2, 7)),
            ))
        monkeypatch.setattr(module, "simulate_soft_capped_pq_no_build_carry", forged)
    elif stage == "build":
        actual = module.simulate_late_pq_external_selected_economic_turn
        def forged(*args, **kwargs):
            out = actual(*args, **kwargs)
            return replace(out, player_pp_after=((1, 99), (2, 7)))
        monkeypatch.setattr(module, "simulate_late_pq_external_selected_economic_turn", forged)
    else:
        actual = module.simulate_capped_pq_existing_ship_cargo_carry
        def forged(*args, **kwargs):
            out = actual(*args, **kwargs)
            return replace(out, carry_after=replace(
                out.carry_after, owner_pp=((1, 99), (2, 7)),
            ))
        monkeypatch.setattr(module, "simulate_capped_pq_existing_ship_cargo_carry", forged)
    original = deepcopy((state, specs, carry, wait, external, fleet))
    result = run(state, specs, carry, wait, external, fleet)
    assert not result.supported and result.state is None
    assert result.build is None and result.waiting_turns == ()
    assert result.fleet_turns == () and result.carry_after is None
    assert (state, specs, carry, wait, external, fleet) == original
