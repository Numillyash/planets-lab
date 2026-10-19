"""V2 owner observations contain exact cargo AND base technology orders.

All inputs are synthetic; HMAC is operator-record integrity, not server
submission acknowledgement or independent Host-start clock provenance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.core import Starbase
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder,
    StarbaseTechUpgradeOrder, TurnOrders,
)
from planets_lab.sim.planetary_owner_capture_v2 import (
    ADMITTED_V2, SCHEMA_V2,
    aggregate_owner_observations_v2,
    seal_owner_observation_v2,
)
from planets_lab.sim.planetary_owner_capture import seal_owner_observation
from planets_lab.sim.planetary_order_capture import OrderCaptureInvalid
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_conditional_reconciliation import (
    reconcile_owner_observations_v2,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs

KEY_ONE = b"owner1" * 6
KEY_TWO = b"owner2" * 6
BEFORE_HOST = "2026-10-19T10:00:00Z"
HOST_START = "2026-10-19T10:01:00Z"
KEYS = {1: {"owner-1": KEY_ONE}, 2: {"owner-2": KEY_TWO}}


def state():
    game = fixture()
    game.starbases[10] = Starbase(
        planet_id=10, owner_id=1, tech_hull=2, tech_engine=7,
    )
    game.planets[10].cargo.megacredits = 3000
    return game


def owner_orders():
    return PlayerOrders(
        player_id=1,
        ship_orders=(ShipOrder(
            ship_id=1,
            planet_transfer=PlanetCargoTransferOrder(
                planet_id=10, direction="planet_to_ship", supplies=2,
            ),
        ),),
        starbase_tech_orders=(StarbaseTechUpgradeOrder(
            planet_id=10, engine=10,
        ),),
    )


def envelopes(game, first=None, second=None):
    if first is None:
        first = owner_orders()
    if second is None:
        second = PlayerOrders(player_id=2)
    return [
        seal_owner_observation_v2(
            game, first, captured_at_utc=BEFORE_HOST, key=KEY_ONE, key_id="owner-1",
        ),
        seal_owner_observation_v2(
            game, second, captured_at_utc=BEFORE_HOST, key=KEY_TWO, key_id="owner-2",
        ),
    ]


def admit(game, rows, *, clock=HOST_START):
    return aggregate_owner_observations_v2(
        rows, game, owner_keyrings=KEYS, observed_host_start_utc=clock,
    )


def test_v2_signed_mixed_order_roundtrip_and_full_owner_coverage():
    game = state()
    rows = envelopes(game)
    original = deepcopy(game)
    result = admit(game, rows)
    assert result.status == ADMITTED_V2
    assert result.admitted and result.orders is not None
    assert result.covered_player_ids == (1, 2)
    assert not result.missing_player_ids
    assert result.orders.by_player[1] == owner_orders()
    assert result.orders.by_player[2] == PlayerOrders(player_id=2)
    assert rows[0]["payload"]["schema"] == SCHEMA_V2
    assert rows[0]["payload"]["server_submission_acknowledged"] is False
    assert rows[0]["payload"]["player_orders"]["starbase_tech_orders"] == [{
        "planet_id": 10, "hull": None, "engine": 10,
        "beam": None, "torpedo": None,
    }]
    assert game == original


def test_v2_reconcile_is_local_conditional_not_nuhost_execution():
    game = state()
    orders = TurnOrders(by_player={
        1: owner_orders(), 2: PlayerOrders(player_id=2),
    })
    modeled = PlanetaryOrderAwareSlice(
        specs(), "transfer_before_planetary",
        tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    ).step(game, orders)
    assert modeled.state is not None
    result = reconcile_owner_observations_v2(
        game, modeled.state, envelopes(game), specs(),
        owner_keyrings=KEYS, observed_host_start_utc=HOST_START,
        complete_snapshots=True, tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    )
    assert result.full_match_placements
    assert result.order_source == ADMITTED_V2
    assert not result.nuhost_orders_executed_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified
    without_pricing = reconcile_owner_observations_v2(
        game, modeled.state, envelopes(game), specs(),
        owner_keyrings=KEYS, observed_host_start_utc=HOST_START,
        complete_snapshots=True,
    )
    assert without_pricing.status == "ABSTAIN_UNSUPPORTED_TECH_PRICING_SCOPE"
    assert not without_pricing.placements


@pytest.mark.parametrize("change,expected_status", [
    ("missing_owner", "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"),
    ("duplicate_owner", "ABSTAIN_DUPLICATE_OWNER"),
    ("tampered_upgrade", "ABSTAIN_INVALID_ATTESTATION"),
    ("tampered_cargo", "ABSTAIN_INVALID_ATTESTATION"),
    ("v1_mixed", "ABSTAIN_INVALID_SCOPE"),
    ("wrong_owner_key", "ABSTAIN_INVALID_ATTESTATION"),
    ("wrong_game", "ABSTAIN_STATE_IDENTITY"),
    ("wrong_turn", "ABSTAIN_STATE_IDENTITY"),
    ("future_capture", "ABSTAIN_NOT_PREHOST"),
    ("unwitnessed_host_start", "ABSTAIN_UNWITNESSED_TIME"),
])
def test_v2_signatures_coverage_identity_and_clock_fail_closed(change, expected_status):
    game = state()
    rows = envelopes(game)
    clock = HOST_START
    if change == "missing_owner":
        rows.pop()
    elif change == "duplicate_owner":
        rows.append(deepcopy(rows[0]))
    elif change == "tampered_upgrade":
        rows[0]["payload"]["player_orders"]["starbase_tech_orders"][0]["engine"] = 9
    elif change == "tampered_cargo":
        rows[0]["payload"]["player_orders"]["ship_orders"][0]["planet_transfer"]["supplies"] = 3
    elif change == "v1_mixed":
        rows[1] = seal_owner_observation(
            game, PlayerOrders(player_id=2),
            captured_at_utc=BEFORE_HOST, key=KEY_TWO, key_id="owner-2",
        )
    elif change == "wrong_owner_key":
        rows[0]["attestation"]["tag_hex"] = rows[1]["attestation"]["tag_hex"]
    elif change == "wrong_game":
        game.game_id = "changed-game"
    elif change == "wrong_turn":
        game.turn += 1
    elif change == "future_capture":
        clock = BEFORE_HOST
    elif change == "unwitnessed_host_start":
        clock = None
    result = admit(game, rows, clock=clock)
    assert result.status == expected_status
    assert result.orders is None


@pytest.mark.parametrize("change", [
    "foreign_base", "missing_base", "duplicate_tech", "empty_tech",
    "tech_downgrade", "tech_beyond_10", "bad_boolean", "missing_owned_planet",
])
def test_seal_refuses_incomplete_or_unrepresentable_technology(change):
    game = state()
    player = owner_orders()
    tech = list(player.starbase_tech_orders)
    if change == "foreign_base":
        game.starbases[10].owner_id = 2
    elif change == "missing_base":
        game.starbases.clear()
    elif change == "missing_owned_planet":
        game.planets[10].owner_id = 2
    elif change == "duplicate_tech":
        tech = tech * 2
    elif change == "empty_tech":
        tech = [StarbaseTechUpgradeOrder(planet_id=10)]
    elif change == "tech_downgrade":
        tech = [StarbaseTechUpgradeOrder(planet_id=10, engine=6)]
    elif change == "tech_beyond_10":
        tech = [StarbaseTechUpgradeOrder(planet_id=10, engine=11)]
    elif change == "bad_boolean":
        tech = [StarbaseTechUpgradeOrder(planet_id=10, engine=True)]
    player = PlayerOrders(
        player_id=1, ship_orders=player.ship_orders,
        starbase_tech_orders=tuple(tech),
    )
    with pytest.raises(OrderCaptureInvalid):
        seal_owner_observation_v2(
            game, player, captured_at_utc=BEFORE_HOST,
            key=KEY_ONE, key_id="owner-1",
        )


def test_v2_signed_payload_rejected_if_malformed_even_with_valid_mac():
    game = state()
    rows = envelopes(game)
    # A trusted owner might sign a malformed record; exact schema and
    # canonical replay must still independently reject it.
    import hashlib
    import hmac
    from planets_lab.sim.planetary_order_capture import _canonical
    rows[0]["payload"]["player_orders"]["starbase_tech_orders"][0]["surprise"] = 5
    rows[0]["attestation"]["tag_hex"] = hmac.new(
        KEY_ONE, b"planets-lab-owner-order-observation-v2\x00"
        + _canonical(rows[0]["payload"]), hashlib.sha256,
    ).hexdigest()
    result = admit(game, rows)
    assert result.status == "ABSTAIN_INVALID_OWNER_BUNDLE"
    assert result.orders is None
