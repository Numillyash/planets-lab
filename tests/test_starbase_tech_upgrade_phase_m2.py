"""M2 documented-price tech purchases remain conditional, not Host witnesses."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.core import Cargo, Starbase
from planets_lab.data.nu_build_cost_calibration import (
    published_standard_tech_upgrade_cost_mc,
)
from planets_lab.sim.engine import HostEngine
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder,
    StarbaseTechUpgradeOrder, TurnOrders,
)
from planets_lab.sim.planetary_conditional_reconciliation import reconcile_explicit_orders
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_order_capture import (
    OrderCaptureInvalid, seal_prehost_capture,
)
from planets_lab.sim.planetary_owner_capture import seal_owner_observation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs


def source(*, mc: int = 3000):
    state = fixture()
    state.starbases[10] = Starbase(planet_id=10, owner_id=1, tech_engine=7)
    state.planets[10].cargo.megacredits = mc
    return state


def tech_order(*, engine=10, hull=None, with_transfer=False):
    ship_orders = ()
    if with_transfer:
        ship_orders = (ShipOrder(
            ship_id=1, planet_transfer=PlanetCargoTransferOrder(
                planet_id=10, direction="ship_to_planet", megacredits=600,
            ),
        ),)
    return TurnOrders(by_player={
        1: PlayerOrders(
            player_id=1,
            ship_orders=ship_orders,
            starbase_tech_orders=(StarbaseTechUpgradeOrder(
                planet_id=10, engine=engine, hull=hull,
            ),),
        ),
    })


def slice_(tech_placement="tech_before_planetary", *, cap=10, transfer_placement="transfer_before_planetary"):
    return PlanetaryOrderAwareSlice(
        specs(), transfer_placement,
        tech_placement=tech_placement, standard_tech_level_caps={1: cap},
    )


@pytest.mark.parametrize("tech_placement", ["tech_before_planetary", "tech_after_planetary"])
def test_standard_upgrade_cost_and_phase_ledger(tech_placement):
    state = source()
    old = deepcopy(state)
    result = slice_(tech_placement).attempt_step(state, tech_order())
    assert result.supported
    assert state == old
    assert result.state is not None
    assert result.state.turn == state.turn + 1
    assert result.state.starbases[10].tech_engine == 10
    assert published_standard_tech_upgrade_cost_mc(7, 10) == 2400
    assert len(result.balances) == 16
    tech = [b for b in result.balances if b.phase == "starbase_tech_upgrade"]
    assert len(tech) == 1
    b = tech[0]
    assert b.category == "explicit_standard_starbase_technology"
    assert b.planet_cargo_delta == {10: {"megacredits": -2400}}
    assert b.combined_net_delta == {"megacredits": -2400}
    assert b.ship_cargo_delta == {}
    assert b.ground_mineral_delta == {}
    assert "starbase_tech_upgraded_standard_conditional" in b.event_kinds
    assert result.balances[0 if tech_placement == "tech_before_planetary" else -1].phase == "starbase_tech_upgrade"


def test_tech_placement_affects_funding_by_explicit_ship_transfer():
    state = source(mc=2000)
    state.ships[1].cargo.megacredits = 600
    order = tech_order(with_transfer=True)
    before = slice_("tech_before_planetary").attempt_step(state, order)
    after = slice_("tech_after_planetary").attempt_step(state, order)
    assert not before.supported
    assert before.state is None and before.balances == ()
    assert after.supported and after.state is not None
    assert after.state.starbases[10].tech_engine == 10
    assert after.state.planets[10].cargo.megacredits >= 0
    assert state.starbases[10].tech_engine == 7
    assert state.planets[10].cargo.megacredits == 2000


def test_multi_field_purchase_only_consumes_standard_mc():
    state = source(mc=4000)
    outcome = slice_().attempt_step(state, tech_order(hull=3))
    assert outcome.supported and outcome.state is not None
    assert outcome.state.starbases[10].tech_hull == 3
    ledger = next(b for b in outcome.balances if b.phase == "starbase_tech_upgrade")
    assert ledger.combined_net_delta == {"megacredits": -2700}
    assert ledger.planet_cargo_delta == {10: {"megacredits": -2700}}
    assert all(name not in ledger.combined_net_delta
               for name in ("duranium", "tritanium", "molybdenum", "neutronium"))


@pytest.mark.parametrize("problem", [
    "no_opt_in", "funds", "cap", "downlevel", "other_owner",
    "missing_base", "duplicate", "no_upgrade", "missing_cap",
])
def test_invalid_orders_fail_closed_without_mutation(problem):
    state = source()
    orders = tech_order()
    pipe = slice_()
    if problem == "no_opt_in":
        pipe = PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary")
    elif problem == "funds":
        state.planets[10].cargo.megacredits = 0
    elif problem == "cap":
        pipe = slice_(cap=7)
    elif problem == "downlevel":
        orders = tech_order(engine=6)
    elif problem == "other_owner":
        state.starbases[10].owner_id = 2
    elif problem == "missing_base":
        state.starbases.clear()
    elif problem == "duplicate":
        owner = orders.by_player[1]
        orders = TurnOrders(by_player={1: PlayerOrders(
            player_id=1,
            starbase_tech_orders=(owner.starbase_tech_orders[0],) * 2,
        )})
    elif problem == "no_upgrade":
        orders = tech_order(engine=7)
    elif problem == "missing_cap":
        pipe = slice_(cap=0)
    old = deepcopy(state)
    result = pipe.attempt_step(state, orders)
    assert result.status == "ABSTAIN_UNSUPPORTED_OR_INVALID"
    assert result.state is None and not result.balances and not result.events
    assert state == old


def test_host_engine_and_legacy_capture_do_not_discard_tech_orders():
    state = source()
    orders = tech_order()
    with pytest.raises(ValueError, match="explicit technology phase"):
        HostEngine().step(state, orders)
    with pytest.raises(OrderCaptureInvalid, match="not supported by V1"):
        seal_prehost_capture(
            state, TurnOrders(by_player={
                1: orders.by_player[1], 2: PlayerOrders(player_id=2),
            }), captured_at_utc="2026-10-19T10:00:00Z",
            key=b"k" * 32, key_id="operator",
        )
    with pytest.raises(OrderCaptureInvalid, match="not supported by V1"):
        seal_owner_observation(
            state, orders.by_player[1], captured_at_utc="2026-10-19T10:00:00Z",
            key=b"k" * 32, key_id="owner",
        )


def test_bounded_full_state_reconciliation_with_tech_snapshot():
    state = source()
    orders = tech_order()
    simulation = slice_("tech_before_planetary").step(state, orders)
    assert simulation.state is not None
    result = reconcile_explicit_orders(
        state, simulation.state, orders, specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    )
    assert result.full_match_placements
    assert any("|tech_before_planetary" in p for p in result.full_match_placements)
    assert not result.nuhost_orders_executed_verified
    assert not result.independent_host_parity_verified
    no_tech = reconcile_explicit_orders(
        state, simulation.state, orders, specs(),
        complete_orders=True, complete_snapshots=True,
    )
    assert no_tech.status == "ABSTAIN_UNSUPPORTED_PAIR"
    no_cap = reconcile_explicit_orders(
        state, simulation.state, orders, specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement="tech_before_planetary",
    )
    assert no_cap.status == "ABSTAIN_UNSUPPORTED_TECH_PRICING_SCOPE"
    changed = deepcopy(simulation.state)
    changed.starbases[10].defense += 1
    invalid = reconcile_explicit_orders(
        state, changed, orders, specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    )
    assert invalid.status == "ABSTAIN_UNSUPPORTED_PAIR"
    changed = deepcopy(simulation.state)
    changed.planets[10].cargo.megacredits += 17
    mismatch = reconcile_explicit_orders(
        state, changed, orders, specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    )
    assert mismatch.status == "CONDITIONAL_UNATTRIBUTED_MISMATCH"
    assert any(
        c.resource_residuals.get("planets", {}).get(10, {}).get("megacredits") == 17
        for c in mismatch.placements if c.status == "CONDITIONAL_MODELED"
    )
