"""Multi-planet multi-turn standard economic contract, all fictional.

These tests are NOT independent NuHost differential evidence. They
exercise the existing synthetic economy pipeline over several turns.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.sim.planetary_structure_multiturn import (
    CONTRACT_STATUS, MAX_TURNS, StructureTurnPlan,
    simulate_multiturn_standard_economy,
)
from planets_lab.sim.planetary_structure_turn_slice import (
    simulate_explicit_structure_turn,
)
from planets_lab.sim.standard_structure_build import StructureBuildTargets

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def two_planets():
    pre = fixture()
    pre.ships.clear()
    original = pre.planets[10]
    second = deepcopy(original)
    second.id = 20
    second.x, second.y = 300, 300
    second.owner_id = 2
    second.factories = 5
    second.mines = 8
    second.ground_duranium.amount = 500
    second.ground_duranium.density = 100
    second.cargo.megacredits = 25
    second.cargo.supplies = 35
    pre.planets[20] = second
    pre.validate()
    return pre


def plan(*, first=(), second=(), placement="structures_before_planetary", sale=True):
    return StructureTurnPlan(
        targets_by_player={1: first, 2: second},
        placement=placement,
        automatic_supply_sale_enabled=sale,
    )


def target(pid, **kwargs):
    return StructureBuildTargets(planet_id=pid, **kwargs)


def three_turns():
    return (
        plan(first=(target(10, factories=12, mines=12),),
             second=(target(20, factories=6, mines=9),),
             placement="structures_before_planetary"),
        plan(first=(target(10, factories=13, defense_posts=1),),
             second=(target(20, mines=11),),
             placement="structures_after_planetary"),
        plan(first=(target(10, mines=15),),
             second=(target(20, factories=8),),
             placement="structures_before_planetary"),
    )


def run(pre, schedule):
    return simulate_multiturn_standard_economy(
        pre, schedule, standard_rules_asserted=True,
        complete_structure_target_scope_asserted=True,
    )


def test_three_turn_two_owner_two_planet_balance_and_state_continuity():
    before = two_planets()
    original = deepcopy(before)
    steps = three_turns()
    a = run(before, steps)
    b = run(before, steps)
    assert a.supported and a.status == CONTRACT_STATUS
    assert a == b
    assert len(a.checkpoints) == 3
    assert a.final_state is not None and a.final_state.turn == before.turn + 3
    assert set(a.final_state.planets) == {10, 20}
    assert a.final_state.planets[10].owner_id == 1
    assert a.final_state.planets[20].owner_id == 2
    assert before == original
    assert not a.nuhost_execution_verified
    assert not a.nuhost_phase_placement_verified
    assert not a.independent_host_parity_verified

    prior = before
    all_tax = all_supplies = all_minerals = all_built = 0
    for index, checkpoint in enumerate(a.checkpoints):
        assert (checkpoint.turn_before, checkpoint.turn_after) == (
            before.turn + index, before.turn + index + 1,
        )
        assert checkpoint.resource_balance_exact
        assert checkpoint.placement == steps[index].placement
        assert tuple(row.planet_id for row in checkpoint.planet_balances) == (10, 20)
        assert all(row.resource_balance_exact for row in checkpoint.planet_balances)
        assert all(row.construction_mc_spent >= 0 for row in checkpoint.planet_balances)
        assert all(row.construction_supplies_sold >= 0 for row in checkpoint.planet_balances)
        all_tax += sum(row.taxes_collected for row in checkpoint.planet_balances)
        all_supplies += sum(row.supplies_produced for row in checkpoint.planet_balances)
        all_minerals += sum(sum(row.mined_minerals) for row in checkpoint.planet_balances)
        all_built += sum(row.built_factories + row.built_mines + row.built_defense_posts
                         for row in checkpoint.planet_balances)
        direct = simulate_explicit_structure_turn(
            prior, steps[index].targets_by_player,
            placement=steps[index].placement,
            standard_rules_asserted=True,
            complete_structure_target_scope_asserted=True,
            automatic_supply_sale_enabled=steps[index].automatic_supply_sale_enabled,
            seed=index,
        )
        assert direct.supported and checkpoint.end_state == direct.state
        assert checkpoint.events == direct.events
        prior = checkpoint.end_state
    assert a.final_state == prior
    assert all_tax > 0
    assert all_supplies > 0
    assert all_minerals > 0
    assert all_built >= 8


@pytest.mark.parametrize("placement", [
    "structures_before_planetary",
    "structures_after_planetary",
])
def test_repeated_target_is_not_double_purchased_across_turns(placement):
    pre = two_planets()
    seq = (
        plan(first=(target(10, factories=11),), placement=placement),
        plan(first=(target(10, factories=11),), placement=placement),
    )
    result = run(pre, seq)
    assert result.supported
    assert result.final_state.planets[10].factories == 11
    first = result.checkpoints[0].planet_balances[0]
    second = result.checkpoints[1].planet_balances[0]
    assert first.built_factories == 1
    assert second.built_factories == 0
    assert second.construction_mc_spent == 0
    assert second.construction_supplies == 0


def test_two_phase_hypotheses_are_different_but_not_host_attributed():
    pre = two_planets()
    before = run(pre, (plan(first=(target(10, factories=11),),
                            placement="structures_before_planetary"),))
    after = run(pre, (plan(first=(target(10, factories=11),),
                           placement="structures_after_planetary"),))
    assert before.supported and after.supported
    assert (before.final_state.planets[10].cargo.supplies
            - after.final_state.planets[10].cargo.supplies) == 1
    assert not before.nuhost_phase_placement_verified
    assert not after.nuhost_phase_placement_verified


@pytest.mark.parametrize("invalid", [
    "zero_steps", "too_many", "mutable_list", "bad_seed", "coverage",
    "rules", "missing_owner", "wrong_owner", "unsupported_late_step",
    "invalid_step_type", "invalid_placement", "invalid_sale", "special_mode",
])
def test_invalid_schedule_or_late_failure_never_exposes_partial_state(invalid):
    pre = two_planets()
    original = deepcopy(pre)
    schedule = list(three_turns())
    options = dict(standard_rules_asserted=True,
                   complete_structure_target_scope_asserted=True, seed=0)
    if invalid == "zero_steps": schedule = []
    if invalid == "too_many": schedule = schedule * 3
    if invalid == "bad_seed": options["seed"] = True
    if invalid == "coverage": options["complete_structure_target_scope_asserted"] = False
    if invalid == "rules": options["standard_rules_asserted"] = False
    if invalid == "missing_owner":
        schedule[1] = plan(first=(target(10, factories=13),))
        schedule[1] = replace(schedule[1], targets_by_player={
            1: schedule[1].targets_by_player[1],
        })
    if invalid == "wrong_owner":
        schedule[1] = plan(second=(target(10, factories=13),))
    if invalid == "unsupported_late_step":
        schedule[1] = plan(first=(target(10, factories=8),))
    if invalid == "invalid_step_type": schedule[1] = "not a turn plan"
    if invalid == "invalid_placement":
        schedule[1] = replace(schedule[1], placement="nuhost-verified")
    if invalid == "invalid_sale":
        schedule[1] = replace(schedule[1], automatic_supply_sale_enabled="maybe")
    if invalid == "special_mode": pre.metadata["no_supplies"] = True
    if invalid == "mutable_list":
        schedule_value = schedule
    else:
        schedule_value = tuple(schedule)
    original = deepcopy(pre)
    result = simulate_multiturn_standard_economy(pre, schedule_value, **options)
    assert result.status == "ABSTAIN_MULTITURN_STANDARD_ECONOMY"
    assert result.final_state is None
    assert result.checkpoints == ()
    assert not result.nuhost_execution_verified
    assert pre == original


@pytest.mark.parametrize("tamper", [
    "mc", "supplies", "ground", "surface", "factories", "missing_receipt",
])
def test_unexplained_internal_model_delta_forces_whole_sequence_abstain(monkeypatch, tamper):
    import planets_lab.sim.planetary_structure_multiturn as module
    real = module.simulate_explicit_structure_turn
    calls = 0

    def corrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        outcome = real(*args, **kwargs)
        if calls != 2:
            return outcome
        assert outcome.state is not None
        changed = deepcopy(outcome.state)
        planet = changed.planets[20]
        events = outcome.events
        if tamper == "mc": planet.cargo.megacredits += 1
        if tamper == "supplies": planet.cargo.supplies += 1
        if tamper == "ground": planet.ground_duranium.amount += 1
        if tamper == "surface": planet.cargo.duranium += 1
        if tamper == "factories": planet.factories += 1
        if tamper == "missing_receipt":
            events = tuple(x for x in events if x.phase !=
                           "standard_structure_build_conditional")
        return replace(outcome, state=changed, events=events)

    monkeypatch.setattr(module, "simulate_explicit_structure_turn", corrupted)
    initial = two_planets()
    result = run(initial, three_turns())
    assert calls == 2
    assert result.status == "ABSTAIN_MULTITURN_STANDARD_ECONOMY"
    assert result.final_state is None
    assert result.checkpoints == ()
