from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest

from planets_lab.core import Cargo
from planets_lab.sim.orders import PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_order_capture import (
    ADMITTED, OrderCaptureInvalid, admit_prehost_capture, seal_prehost_capture,
    simulate_admitted_capture, state_fingerprint,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, order, specs

KEY = b"test-key-is-never-used-for-real-captures-v1"
KEYRING = {"synthetic-test": KEY}
START = "2026-10-16T09:00:00Z"
CAPTURED = "2026-10-16T08:00:00Z"


def complete_orders():
    requested = order(supplies=10, clans=5, neutronium=5)
    return TurnOrders(by_player={
        1: requested.by_player[1],
        2: PlayerOrders(player_id=2, ship_orders=()),
    })


def sealed(state=None, orders=None):
    state = state if state is not None else fixture()
    orders = orders if orders is not None else complete_orders()
    return seal_prehost_capture(
        state, orders, captured_at_utc=CAPTURED,
        key=KEY, key_id="synthetic-test",
    )


def admit(bundle, state=None, *, boundary=START, keyring=None):
    return admit_prehost_capture(
        bundle, state if state is not None else fixture(),
        keyring=KEYRING if keyring is None else keyring,
        observed_host_start_utc=boundary,
    )


def test_capture_roundtrip_exact_state_and_ordered_world_scope():
    state = fixture()
    state.metadata["private_token_not_to_serialize"] = "secret-private-value"
    expected = complete_orders()
    original = state.clone()
    bundle = sealed(state, expected)
    assert "secret-private-value" not in json.dumps(bundle)
    assert "test-key-is-never" not in json.dumps(bundle)
    assert bundle["payload"]["pre_state_sha256"] == state_fingerprint(state)
    admission = admit(bundle, state)
    assert admission.status == ADMITTED
    assert admission.orders == expected
    assert state == original
    assert len(bundle["payload"]["orders"]) == 2
    assert bundle["payload"]["orders"][1]["ship_orders"] == []


@pytest.mark.parametrize("placement", ["transfer_before_planetary", "transfer_after_planetary"])
def test_admitted_capture_drives_existing_host_slice_without_duplicating_phases(placement):
    state = fixture()
    before = state.clone()
    orders = complete_orders()
    bundle = sealed(state, orders)
    piped = PlanetaryOrderAwareSlice(specs(), placement)
    result = simulate_admitted_capture(
        piped, state, bundle, keyring=KEYRING,
        observed_host_start_utc=START, seed=23,
    )
    direct = piped.step(state, orders, seed=23)
    assert result.status == "MODELED_OPERATOR_ATTESTED_NOT_NUHOST_DIFFERENTIAL"
    assert result.outcome == direct
    assert len(direct.balances) == 15
    assert state == before


@pytest.mark.parametrize("tamper", [
    "amount", "game_id", "turn", "pre_state_sha256", "origin",
    "coverage", "players", "extra_field", "missing_field",
    "unknown_transfer_field", "negative_amount", "duplicate_player",
    "incomplete_player_scope",
])
def test_tampering_and_malformed_signed_scope_abstain_without_state_or_events(tamper):
    state = fixture()
    bundle = sealed()
    payload = bundle["payload"]
    if tamper == "amount":
        payload["orders"][0]["ship_orders"][0]["planet_transfer"]["supplies"] += 1
    elif tamper == "game_id":
        payload["game_id"] = "wrong-game"
    elif tamper == "turn":
        payload["turn"] = 99
    elif tamper == "pre_state_sha256":
        payload["pre_state_sha256"] = "a" * 64
    elif tamper == "origin":
        payload["source"] = "posthost_inferred"
    elif tamper == "coverage":
        payload["coverage"] = "partial"
    elif tamper == "players":
        payload["player_ids"] = [1]
    elif tamper == "extra_field":
        payload["unexpected_secret"] = "PRIVATE"
    elif tamper == "missing_field":
        payload.pop("captured_at_utc")
    elif tamper == "unknown_transfer_field":
        payload["orders"][0]["ship_orders"][0]["planet_transfer"]["build"] = 1
    elif tamper == "negative_amount":
        payload["orders"][0]["ship_orders"][0]["planet_transfer"]["supplies"] = -1
    elif tamper == "duplicate_player":
        payload["orders"].append(deepcopy(payload["orders"][0]))
    elif tamper == "incomplete_player_scope":
        payload["orders"].pop()
    result = simulate_admitted_capture(
        PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary"),
        state, bundle, keyring=KEYRING,
        observed_host_start_utc=START,
    )
    assert result.status.startswith("ABSTAIN_")
    assert result.outcome is None and result.reason
    assert state == fixture()


def test_correctly_signed_but_wrong_context_fails_closed():
    state = fixture()
    bundle = sealed()
    mutated_state = state.clone()
    mutated_state.planets[10].cargo.supplies += 1
    assert admit(bundle, mutated_state).status == "ABSTAIN_STATE_IDENTITY"
    different_game = state.clone()
    different_game.game_id = "different-game"
    assert admit(bundle, different_game).status == "ABSTAIN_STATE_IDENTITY"
    different_turn = state.clone()
    different_turn.turn += 1
    assert admit(bundle, different_turn).status == "ABSTAIN_STATE_IDENTITY"


@pytest.mark.parametrize("boundary,expected", [
    (None, "ABSTAIN_UNWITNESSED_TIME"),
    ("2026-10-16T08:00:00Z", "ABSTAIN_NOT_PREHOST"),
    ("2026-10-16T07:59:59Z", "ABSTAIN_NOT_PREHOST"),
    ("2026-10-16T07:00:00+00:00", "ABSTAIN_INVALID_CAPTURE"),
    ("not-a-timestamp", "ABSTAIN_INVALID_CAPTURE"),
])
def test_explicit_prehost_boundary_is_mandatory(boundary, expected):
    result = admit(sealed(), boundary=boundary)
    assert result.status == expected
    assert result.orders is None


def test_untrusted_key_and_invalid_mac_never_admit():
    assert admit(sealed(), keyring={}).status == "ABSTAIN_UNTRUSTED_KEY"
    assert admit(sealed(), keyring={"synthetic-test": b"x" * 32}).status == "ABSTAIN_INVALID_ATTESTATION"
    bundle = sealed()
    bundle["attestation"]["tag_hex"] = "zz" * 32
    assert admit(bundle).status == "ABSTAIN_INVALID_ATTESTATION"
    assert admit({}).status == "ABSTAIN_INVALID_CAPTURE"


def test_unsigned_empty_orders_are_not_evidence_of_known_zero_transfers():
    assert admit({"payload": {}, "attestation": {}}).status == "ABSTAIN_INVALID_CAPTURE"
    with pytest.raises(OrderCaptureInvalid, match="every declared game player"):
        seal_prehost_capture(
            fixture(), TurnOrders.empty(), captured_at_utc=CAPTURED,
            key=KEY, key_id="synthetic-test",
        )
    # Explicitly signed empty orders for BOTH players are structurally
    # admissible but NOT proof that NuHost actually received zero orders.
    known_empty = TurnOrders(by_player={
        1: PlayerOrders(player_id=1),
        2: PlayerOrders(player_id=2),
    })
    admitted = admit(sealed(orders=known_empty))
    assert admitted.admitted and admitted.orders == known_empty


def test_unsupported_order_fields_and_missing_players_are_not_silently_dropped():
    state = fixture()
    bad_ship = ShipOrder(ship_id=1, warp=9,
        planet_transfer=complete_orders().by_player[1].ship_orders[0].planet_transfer)
    illegal = TurnOrders(by_player={
        1: PlayerOrders(player_id=1, ship_orders=(bad_ship,)),
        2: PlayerOrders(player_id=2),
    })
    with pytest.raises(OrderCaptureInvalid, match="unknown ship-order"):
        sealed(state, illegal)
    with pytest.raises(OrderCaptureInvalid, match="every declared game player"):
        sealed(state, order(supplies=1))
    with pytest.raises(OrderCaptureInvalid, match=r"32\\+ bytes"):
        seal_prehost_capture(state, complete_orders(), captured_at_utc=CAPTURED,
                             key=b"weak", key_id="demo")


def test_supported_signature_does_not_override_engine_abstention():
    state = fixture()
    state.ships[1].x = 101
    capture = sealed(state)
    result = simulate_admitted_capture(
        PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary"),
        state, capture, keyring=KEYRING, observed_host_start_utc=START,
    )
    assert result.status == "ABSTAIN_UNSUPPORTED_SIMULATION"
    assert result.outcome is None
