"""Research-only standard base creation, garrisons and planet economy."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.core import Starbase
from planets_lab.sim.standard_starbase_facilities_phase import (
    StandardBaseCreateOrder, StandardBaseArmOrder,
    STANDARD_BASE_CREATION, STANDARD_BASE_DEFENSE_COST,
    STANDARD_BASE_FIGHTER_COST,
)
from planets_lab.sim.standard_starbase_facilities_turn import (
    STATUS, FACILITY_PLACEMENTS, simulate_standard_starbase_facilities_turn,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def before():
    state = fixture()
    state.ships.clear()
    a = state.planets[10]
    a.cargo.megacredits = 1500
    a.cargo.duranium = 300
    a.cargo.tritanium = 700
    a.cargo.molybdenum = 500
    a.cargo.supplies = 90
    b = deepcopy(a)
    b.id = 20
    b.owner_id = 2
    b.x = 300
    b.y = 300
    b.cargo.megacredits = 1600
    state.planets[20] = b
    state.starbases[20] = Starbase(
        planet_id=20, owner_id=2, defense=3, fighters=5,
    )
    state.validate()
    return state


def planned():
    return {
        1: (StandardBaseCreateOrder(planet_id=10),),
        2: (StandardBaseArmOrder(
            planet_id=20, defense_target=5, fighter_target=7,
        ),),
    }


def run(state, orders=None, **kwargs):
    opts = dict(
        placement="facilities_before_planetary",
        standard_rules_asserted=True,
        complete_owner_facility_scope_asserted=True,
    )
    opts.update(kwargs)
    return simulate_standard_starbase_facilities_turn(
        state, planned() if orders is None else orders, **opts,
    )


@pytest.mark.parametrize("placement", FACILITY_PLACEMENTS)
def test_two_owner_base_creation_and_garrison_economy_ledger(placement):
    initial = before()
    frozen = deepcopy(initial)
    first = run(initial, placement=placement)
    repeat = run(initial, placement=placement)
    assert first == repeat
    assert first.status == STATUS and first.supported
    assert initial == frozen
    assert first.state.turn == initial.turn + 1
    assert first.state.starbases[10] == Starbase(planet_id=10, owner_id=1)
    assert first.state.starbases[20].defense == 5
    assert first.state.starbases[20].fighters == 7
    assert first.state.starbases[20].tech_hull == 1
    assert len(first.base_balances) == 2
    creation, arming = first.base_balances
    assert creation.created and creation.planet_id == 10
    assert dict(creation.spent) == dict(STANDARD_BASE_CREATION)
    assert not arming.created and arming.planet_id == 20
    assert arming.defense_added == 2 and arming.fighters_added == 2
    assert dict(arming.spent) == {
        "megacredits": 220, "duranium": 2,
        "tritanium": 6, "molybdenum": 4,
    }
    assert len(first.planet_balances) == 2
    assert all(x.resource_balance_exact for x in first.planet_balances)
    assert all(x.exact for x in first.base_balances)
    # Duranium is simultaneously mined by the unchanged economy phases.
    # Compare base consumption PLUS the independently reconciled mining
    # receipt, rather than pretending an economically active planet is inert.
    for pid, purchased in ((10, dict(creation.spent)), (20, dict(arming.spent))):
        source = initial.planets[pid].cargo
        final = first.state.planets[pid].cargo
        mined = next(x for x in first.planet_balances if x.planet_id == pid)
        for index, mineral in enumerate(("neutronium", "duranium", "tritanium", "molybdenum")):
            assert getattr(final, mineral) - getattr(source, mineral) == (
                mined.mined_minerals[index] - purchased.get(mineral, 0)
            )
    assert not first.nuhost_order_execution_verified
    assert not first.nuhost_phase_placement_verified
    assert not first.independent_host_parity_verified
    assert not any(x.phase.startswith("starbase_ship") for x in first.events)


def test_tax_revenue_can_enable_base_purchase_only_after_economy():
    state = before()
    state.planets[10].cargo.megacredits = 899
    original = deepcopy(state)
    early = run(state, placement="facilities_before_planetary")
    late = run(state, placement="facilities_after_planetary")
    assert early.status == "ABSTAIN_STANDARD_STARBASE_FACILITIES_TURN"
    assert early.state is None
    assert late.supported
    assert late.state.starbases[10].owner_id == 1
    assert late.planet_balances[0].taxes_collected > 0
    assert state == original


def test_full_resource_exact_creation_cost_and_no_neutronium_or_supplies_cost():
    state = before()
    state.planets[10].cargo.megacredits = 900
    state.planets[10].cargo.duranium = 120
    state.planets[10].cargo.tritanium = 402
    state.planets[10].cargo.molybdenum = 340
    old_supplies = state.planets[10].cargo.supplies
    old_fuel = state.planets[10].cargo.neutronium
    result = run(state)
    assert result.supported
    assert dict(result.base_balances[0].spent) == {
        "megacredits": 900, "duranium": 120,
        "tritanium": 402, "molybdenum": 340,
    }
    assert result.state.planets[10].cargo.neutronium == old_fuel
    assert result.state.planets[10].cargo.supplies >= old_supplies


@pytest.mark.parametrize("invalid", (
    "missing_owner", "invalid_owner_record", "empty", "duplicate", "foreign",
    "not_planet", "existing", "no_base", "wrong_base_owner",
    "insufficient_base_mc", "insufficient_base_duranium",
    "insufficient_base_tritanium", "insufficient_base_molybdenum",
    "insufficient_garrison_mc", "insufficient_garrison_duranium",
    "insufficient_garrison_tritanium", "insufficient_garrison_molybdenum",
    "over_defense", "over_fighters", "below_defense", "below_fighters",
    "empty_target", "no_change", "boolean_target", "bad_order_type",
    "unsupported_ships", "metadata", "storm", "missing_rules",
    "missing_scope", "wrong_placement",
))
def test_unsupported_cases_abstain_without_partial_state(invalid):
    state = before()
    orders = planned()
    opts = {}
    if invalid == "missing_owner":
        orders.pop(2)
    elif invalid == "invalid_owner_record":
        orders = {1: None, 2: orders[2]}
    elif invalid == "empty":
        orders = {1: (), 2: ()}
    elif invalid == "duplicate":
        orders[1] = orders[1] * 2
    elif invalid == "foreign":
        orders[1] = (StandardBaseCreateOrder(20),)
        orders[2] = ()
    elif invalid == "not_planet":
        orders[1] = (StandardBaseCreateOrder(999),)
    elif invalid == "existing":
        orders[2] = (StandardBaseCreateOrder(20),)
    elif invalid == "no_base":
        orders[1] = (StandardBaseArmOrder(10, defense_target=1),)
    elif invalid == "wrong_base_owner":
        state.starbases[20].owner_id = 1
    elif invalid.startswith("insufficient_base_"):
        key = invalid.removeprefix("insufficient_base_")
        setattr(state.planets[10].cargo, key if key != "mc" else "megacredits", 0)
    elif invalid.startswith("insufficient_garrison_"):
        key = invalid.removeprefix("insufficient_garrison_")
        setattr(state.planets[20].cargo, key if key != "mc" else "megacredits", 0)
    elif invalid == "over_defense":
        orders[2] = (StandardBaseArmOrder(20, defense_target=201),)
    elif invalid == "over_fighters":
        orders[2] = (StandardBaseArmOrder(20, fighter_target=61),)
    elif invalid == "below_defense":
        orders[2] = (StandardBaseArmOrder(20, defense_target=2),)
    elif invalid == "below_fighters":
        orders[2] = (StandardBaseArmOrder(20, fighter_target=4),)
    elif invalid == "empty_target":
        orders[2] = (StandardBaseArmOrder(20),)
    elif invalid == "no_change":
        orders[2] = (StandardBaseArmOrder(20, defense_target=3),)
    elif invalid == "boolean_target":
        orders[2] = (StandardBaseArmOrder(20, fighter_target=True),)
    elif invalid == "bad_order_type":
        orders[1] = ({"planet_id": 10},)
    elif invalid == "unsupported_ships":
        state.ships = fixture().ships
    elif invalid == "metadata":
        state.metadata["race_special"] = True
    elif invalid == "storm":
        from planets_lab.core import IonStorm
        state.ion_storms[1] = IonStorm(
            id=1, x=100, y=100, radius=5, voltage=5, warp=0, heading=0,
        )
    elif invalid == "missing_rules":
        opts["standard_rules_asserted"] = False
    elif invalid == "missing_scope":
        opts["complete_owner_facility_scope_asserted"] = False
    elif invalid == "wrong_placement":
        opts["placement"] = "claimed_verified_host_order"
    frozen = deepcopy(state)
    result = run(state, orders, **opts)
    assert result.status == "ABSTAIN_STANDARD_STARBASE_FACILITIES_TURN"
    assert not result.supported
    assert result.state is None and result.events == ()
    assert result.planet_balances == () and result.base_balances == ()
    assert not result.nuhost_order_execution_verified
    assert state == frozen


@pytest.mark.parametrize("tamper", (
    "base_missing", "defense", "fighter", "extra_base",
    "mc", "duranium", "tritanium", "molybdenum",
    "receipt_removed", "receipt_duplicate", "receipt_wrong_cost",
    "receipt_wrong_kind", "receipt_wrong_delta", "unauthorized_tech",
))
def test_corrupted_state_or_purchase_event_abstains(tamper, monkeypatch):
    import planets_lab.sim.standard_starbase_facilities_turn as module
    real = module.HostEngine.step

    def corrupted(self, pre, orders, *, seed=0):
        next_state, events = real(self, pre, orders, seed=seed)
        next_state = deepcopy(next_state)
        events = list(events)
        if tamper == "base_missing":
            next_state.starbases.pop(10)
        elif tamper == "defense":
            next_state.starbases[20].defense += 1
        elif tamper == "fighter":
            next_state.starbases[20].fighters += 1
        elif tamper == "extra_base":
            next_state.starbases[11] = Starbase(11, owner_id=1)
        elif tamper in ("mc", "duranium", "tritanium", "molybdenum"):
            key = "megacredits" if tamper == "mc" else tamper
            setattr(next_state.planets[10].cargo, key,
                    getattr(next_state.planets[10].cargo, key) + 1)
        elif tamper == "unauthorized_tech":
            next_state.starbases[20].tech_engine += 1
        elif tamper == "receipt_removed":
            events = [e for e in events
                      if e.phase != "standard_starbase_facilities_conditional"]
        elif tamper == "receipt_duplicate":
            events += [e for e in events
                       if e.phase == "standard_starbase_facilities_conditional"]
        elif tamper in ("receipt_wrong_cost", "receipt_wrong_delta", "receipt_wrong_kind"):
            index = next(i for i, e in enumerate(events)
                         if e.phase == "standard_starbase_facilities_conditional")
            ev = events[index]
            d = dict(ev.details)
            if tamper == "receipt_wrong_cost":
                d["spent_duranium"] = "119"
            elif tamper == "receipt_wrong_delta":
                d["fighters_added"] = "1"
            events[index] = replace(
                ev, kind="fake_purchase" if tamper == "receipt_wrong_kind"
                else ev.kind, details=tuple(d.items()),
            )
        return next_state, tuple(events)

    monkeypatch.setattr(module.HostEngine, "step", corrupted)
    state = before()
    frozen = deepcopy(state)
    result = run(state)
    assert result.status == "ABSTAIN_STANDARD_STARBASE_FACILITIES_TURN"
    assert result.state is None and result.events == ()
    assert result.planet_balances == () and result.base_balances == ()
    assert state == frozen


def test_legacy_signed_player_orders_and_planet_pipeline_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    assert tuple(x.name for x in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
    assert len(PlanetaryHostPipeline().phases) == 14
