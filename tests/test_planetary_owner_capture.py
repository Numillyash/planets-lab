from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.sim.orders import PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.planetary_order_capture import OrderCaptureInvalid
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_owner_capture import (
    ADMITTED, aggregate_owner_observations, seal_owner_observation,
    simulate_owner_bundle,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, order, specs

K1 = b"player-one-operator-only-test-key-v1"
K2 = b"player-two-operator-only-test-key-v1"
KEYS = {1: {"p1": K1}, 2: {"p2": K2}}
START = "2026-10-16T09:00:00Z"
BEFORE = "2026-10-16T08:00:00Z"


def bundles(state=None):
    state = fixture() if state is None else state
    own1 = order(supplies=10, neutronium=5, clans=5).by_player[1]
    own2 = PlayerOrders(player_id=2, ship_orders=())
    a = seal_owner_observation(
        state, own1, captured_at_utc=BEFORE, key=K1, key_id="p1",
    )
    b = seal_owner_observation(
        state, own2, captured_at_utc=BEFORE, key=K2, key_id="p2",
    )
    return a, b


def admit(records, state=None, *, rings=KEYS, host=START):
    return aggregate_owner_observations(
        records, fixture() if state is None else state,
        owner_keyrings=rings, observed_host_start_utc=host,
    )


def test_two_independently_signed_owners_aggregate_without_synthesizing_orders():
    state = fixture()
    saved_state = state.clone()
    a, b = bundles(state)
    assert a["payload"]["player_id"] == 1
    assert b["payload"]["player_id"] == 2
    assert len(a["payload"]["player_orders"]["ship_orders"]) == 1
    assert not b["payload"]["player_orders"]["ship_orders"]
    assert "player_ids" not in a["payload"]
    assert not a["payload"]["server_submission_acknowledged"]
    assert "player_orders" in a["payload"]
    candidate = admit([b, a], state)
    assert candidate.admitted and candidate.status == ADMITTED
    assert candidate.covered_player_ids == (1, 2)
    assert candidate.missing_player_ids == ()
    assert candidate.orders is not None
    assert candidate.orders.by_player[2] == PlayerOrders(player_id=2)
    assert state == saved_state
    for placement in ("transfer_before_planetary", "transfer_after_planetary"):
        sim = PlanetaryOrderAwareSlice(specs(), placement)
        result = simulate_owner_bundle(
            sim, state, (a, b), owner_keyrings=KEYS,
            observed_host_start_utc=START, seed=13,
        )
        assert result.status == "MODELED_OWNER_BUNDLE_NOT_NUHOST_DIFFERENTIAL"
        assert result.outcome == sim.step(state, candidate.orders, seed=13)
        assert result.outcome is not None and len(result.outcome.balances) == 15
        assert state == saved_state


def test_single_owner_is_partial_not_false_empty_or_full():
    a, b = bundles()
    only_a = admit([a])
    assert only_a.status == "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"
    assert only_a.orders is None
    assert only_a.covered_player_ids == (1,)
    assert only_a.missing_player_ids == (2,)
    only_b = admit([b])
    assert only_b.status == "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"
    assert only_b.missing_player_ids == (1,)
    simulation = simulate_owner_bundle(
        PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary"),
        fixture(), [a], owner_keyrings=KEYS,
        observed_host_start_utc=START,
    )
    assert simulation.status == "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"
    assert simulation.outcome is None


def test_cross_player_key_not_a_credential_for_other_owner():
    a, b = bundles()
    misplaced = deepcopy(b)
    misplaced["attestation"]["key_id"] = "p1"
    assert admit([a, misplaced]).status == "ABSTAIN_UNTRUSTED_OWNER_KEY"
    fake_registry = {1: KEYS[1], 2: {"p2": K1}}
    assert admit([a, b], rings=fake_registry).status == "ABSTAIN_INVALID_ATTESTATION"


@pytest.mark.parametrize("mutation,expected", [
    ("duplicate", "ABSTAIN_DUPLICATE_OWNER"),
    ("tamper", "ABSTAIN_INVALID_ATTESTATION"),
    ("wrong_turn", "ABSTAIN_INVALID_ATTESTATION"),
    ("unknown_owner", "ABSTAIN_FOREIGN_OWNER"),
    ("different_state", "ABSTAIN_STATE_IDENTITY"),
    ("reassigned_owner", "ABSTAIN_INVALID_ATTESTATION"),
    ("missing_envelope", "ABSTAIN_INVALID_OWNER_BUNDLE"),
    ("self_claim_server_ack", "ABSTAIN_INVALID_SCOPE"),
    ("partial_claim", "ABSTAIN_INVALID_SCOPE"),
    ("unknown_field", "ABSTAIN_INVALID_OWNER_BUNDLE"),
])
def test_invalid_captures_fail_closed_without_leaking_partial_orders(mutation, expected):
    a, b = bundles()
    state = fixture()
    selected = [a, b]
    if mutation == "duplicate":
        selected.append(deepcopy(a))
    elif mutation == "tamper":
        a["payload"]["player_orders"]["ship_orders"][0]["planet_transfer"]["supplies"] += 1
    elif mutation == "wrong_turn":
        b["payload"]["turn"] += 1
    elif mutation == "unknown_owner":
        b["payload"]["player_id"] = 3
    elif mutation == "different_state":
        state.planets[10].cargo.supplies += 1
    elif mutation == "reassigned_owner":
        b["payload"]["player_orders"]["player_id"] = 1
    elif mutation == "missing_envelope":
        selected[0] = {"wrong": "schema"}
    elif mutation == "self_claim_server_ack":
        b["payload"]["server_submission_acknowledged"] = True
    elif mutation == "partial_claim":
        a["payload"]["owner_orders_complete"] = False
    elif mutation == "unknown_field":
        b["payload"]["new_sensitive_value"] = "DO_NOT_INCLUDE"
    outcome = admit(selected, state)
    assert outcome.status == expected
    assert outcome.orders is None


@pytest.mark.parametrize("host,expected", [
    (None, "ABSTAIN_UNWITNESSED_TIME"),
    (BEFORE, "ABSTAIN_NOT_PREHOST"),
    ("2026-10-16T07:59:00Z", "ABSTAIN_NOT_PREHOST"),
    ("bad-clock", "ABSTAIN_INVALID_OWNER_BUNDLE"),
])
def test_host_start_witness_is_required_but_not_cryptographically_verified(host, expected):
    assert admit(bundles(), host=host).status == expected


def test_ownership_and_unknown_ship_commands_fail_at_local_capture():
    state = fixture()
    bad_order = PlayerOrders(
        player_id=2, ship_orders=order(supplies=1).by_player[1].ship_orders,
    )
    with pytest.raises(OrderCaptureInvalid, match="owned"):
        seal_owner_observation(
            state, bad_order, captured_at_utc=BEFORE, key=K2, key_id="p2",
        )
    custom = PlayerOrders(
        player_id=1, ship_orders=(ShipOrder(ship_id=1, warp=5,
            planet_transfer=order(supplies=1).by_player[1].ship_orders[0].planet_transfer),)
    )
    with pytest.raises(OrderCaptureInvalid, match="unmodeled|unknown"):
        seal_owner_observation(
            state, custom, captured_at_utc=BEFORE, key=K1, key_id="p1",
        )


def test_unknown_owner_and_short_key_cannot_create_captures():
    state=fixture()
    with pytest.raises(OrderCaptureInvalid, match="owner"):
        seal_owner_observation(
            state, PlayerOrders(player_id=3), captured_at_utc=BEFORE,
            key=K1, key_id="p3",
        )
    with pytest.raises(OrderCaptureInvalid, match="32"):
        seal_owner_observation(
            state, PlayerOrders(player_id=1), captured_at_utc=BEFORE,
            key=b"bad", key_id="p1",
        )
