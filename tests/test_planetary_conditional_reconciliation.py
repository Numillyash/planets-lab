from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from planets_lab.core import Cargo
from planets_lab.sim.orders import TurnOrders
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_conditional_reconciliation import (
    reconcile_explicit_orders, reconcile_owner_observations,
)
from planets_lab.sim.planetary_owner_capture import seal_owner_observation
from planets_lab.sim.orders import PlayerOrders
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, order, specs


def modeled(placement: str, orders=None):
    pre = fixture()
    orders = order(supplies=10, neutronium=10) if orders is None else orders
    outcome = PlanetaryOrderAwareSlice(specs(), placement).step(pre, orders)
    assert outcome.state is not None
    return pre, orders, outcome.state


def test_exact_reconciliation_does_not_promote_host_causality():
    before, orders, after = modeled("transfer_before_planetary")
    result = reconcile_explicit_orders(
        before, after, orders, specs(), complete_orders=True, complete_snapshots=True,
    )
    assert result.status.startswith("CONDITIONAL_FULL_MATCH")
    assert "transfer_before_planetary" in result.full_match_placements
    assert not result.nuhost_orders_executed_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified
    assert before == fixture()
    assert all(c.balances for c in result.placements if c.status == "CONDITIONAL_MODELED")


def test_absent_provenance_must_not_substitute_empty_orders():
    pre, orders, post = modeled("transfer_before_planetary")
    for complete_orders, complete_snapshots in ((False, True), (True, False)):
        outcome = reconcile_explicit_orders(
            pre, post, TurnOrders.empty(), specs(),
            complete_orders=complete_orders,
            complete_snapshots=complete_snapshots,
        )
        assert outcome.status == "ABSTAIN_INCOMPLETE_ORDER_OR_SNAPSHOT_COVERAGE"
        assert not outcome.placements


def test_signed_resource_residual_is_observed_minus_modeled():
    pre, orders, post = modeled("transfer_before_planetary")
    post.planets[10].cargo.duranium += 5
    result = reconcile_explicit_orders(
        pre, post, orders, specs(), complete_orders=True, complete_snapshots=True,
    )
    assert result.status == "CONDITIONAL_UNATTRIBUTED_MISMATCH"
    assert all(c.resource_residuals["planets"][10]["duranium"] == 5
               for c in result.placements if c.status == "CONDITIONAL_MODELED")


def test_unsupported_incomplete_or_nonphysical_observations_fail_closed():
    pre, orders, post = modeled("transfer_before_planetary")
    variants = []
    missing_ship = deepcopy(post)
    missing_ship.ships.clear()
    variants.append(missing_ship)
    moved_ship = deepcopy(post)
    moved_ship.ships[1].x += 1
    variants.append(moved_ship)
    stale_turn = deepcopy(post)
    stale_turn.turn += 1
    variants.append(stale_turn)
    invalid_cargo = deepcopy(post)
    invalid_cargo.planets[10].cargo.neutronium = -1
    variants.append(invalid_cargo)
    for observed in variants:
        result = reconcile_explicit_orders(
            pre, observed, orders, specs(),
            complete_orders=True, complete_snapshots=True,
        )
        assert result.status == "ABSTAIN_UNSUPPORTED_PAIR"
        assert not result.placements


def test_unsupported_orders_abstain_without_partial_resources():
    pre, orders, post = modeled("transfer_before_planetary")
    pre.ships[1].x += 5
    result = reconcile_explicit_orders(
        pre, post, orders, specs(), complete_orders=True, complete_snapshots=True,
    )
    assert result.status == "ABSTAIN_UNSUPPORTED_PAIR"


def test_owner_admission_required_and_not_host_receipt():
    pre, orders, post = modeled("transfer_before_planetary")
    key = b"x" * 32
    owner_orders = orders.by_player[1]
    own = seal_owner_observation(
        pre, owner_orders, captured_at_utc="2026-10-18T15:00:00Z",
        key=key, key_id="owner1",
    )
    incomplete = reconcile_owner_observations(
        pre, post, [own], specs(),
        owner_keyrings={1: {"owner1": key}},
        observed_host_start_utc="2026-10-18T15:01:00Z",
        complete_snapshots=True,
    )
    assert incomplete.status == "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"
    other = seal_owner_observation(
        pre, PlayerOrders(player_id=2),
        captured_at_utc="2026-10-18T15:00:01Z", key=key, key_id="owner2",
    )
    result = reconcile_owner_observations(
        pre, post, [own, other], specs(),
        owner_keyrings={1: {"owner1": key}, 2: {"owner2": key}},
        observed_host_start_utc="2026-10-18T15:01:00Z",
        complete_snapshots=True,
    )
    assert result.full_match_placements
    assert result.order_source == "ADMITTED_ALL_PLAYERS_OPERATOR_SIGNED_NOT_NUHOST_VERIFIED"
    assert not result.nuhost_orders_executed_verified
