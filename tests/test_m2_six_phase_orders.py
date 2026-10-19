"""M2: 3! explicit conditional tech/cargo/economy phase orderings.

The planetary block stays intact; these are synthetic compatibility
hypotheses and do not establish NuHost order execution or phase order.
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
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_conditional_reconciliation import (
    reconcile_all_standard_tech_phase_orders,
    reconcile_owner_observations_v2_all_tech_phase_orders,
    reconcile_explicit_orders,
)
from planets_lab.sim.planetary_owner_capture_v2 import seal_owner_observation_v2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs

CARGO = "planet_cargo_transfer"
TECH = "starbase_tech_upgrade"
BLOCK = tuple(x.name for x in __import__(
    "planets_lab.sim.planetary_host_pipeline", fromlist=["PlanetaryHostPipeline"],
).PlanetaryHostPipeline().phases)
CAPS = {1: 10}
SLOTS = (
    "tech_before_planetary",
    "tech_between_cargo_and_planetary",
    "tech_after_planetary",
)
PLACEMENTS = ("transfer_before_planetary", "transfer_after_planetary")


def state(*, funds=3000):
    pre = fixture()
    pre.starbases[10] = Starbase(planet_id=10, owner_id=1, tech_engine=7)
    pre.planets[10].cargo.megacredits = funds
    return pre


def player_order(*, transfer=False):
    ships = (
        (ShipOrder(ship_id=1, planet_transfer=PlanetCargoTransferOrder(
            planet_id=10, direction="ship_to_planet", megacredits=600,
        )),) if transfer else ()
    )
    return PlayerOrders(
        player_id=1, ship_orders=ships,
        starbase_tech_orders=(StarbaseTechUpgradeOrder(
            planet_id=10, engine=10,
        ),),
    )


def orders(*, transfer=False):
    return TurnOrders(by_player={
        1: player_order(transfer=transfer),
        2: PlayerOrders(player_id=2),
    })


def slices(placement, slot):
    return PlanetaryOrderAwareSlice(
        specs(), placement, tech_placement=slot,
        standard_tech_level_caps=CAPS,
    )


@pytest.mark.parametrize("placement", PLACEMENTS)
@pytest.mark.parametrize("slot", SLOTS)
def test_exact_ordering_and_tech_resource_ledger_in_all_six_cases(placement, slot):
    pre = state()
    copy = deepcopy(pre)
    result = slices(placement, slot).step(pre, orders())
    names = tuple(b.phase for b in result.balances)
    expected = ((CARGO, *BLOCK) if placement == PLACEMENTS[0] else (*BLOCK, CARGO))
    if slot == SLOTS[0]:
        expected = (TECH, *expected)
    elif slot == SLOTS[-1]:
        expected = (*expected, TECH)
    elif placement == PLACEMENTS[0]:
        expected = (CARGO, TECH, *BLOCK)
    else:
        expected = (*BLOCK, TECH, CARGO)
    assert names == expected
    assert len(names) == len(BLOCK) + 2 == 16
    tech_balances = [b for b in result.balances if b.phase == TECH]
    assert len(tech_balances) == 1
    assert tech_balances[0].combined_net_delta == {"megacredits": -2400}
    assert tech_balances[0].planet_cargo_delta == {10: {"megacredits": -2400}}
    assert result.state is not None and result.state.starbases[10].tech_engine == 10
    assert pre == copy


def test_exhaustive_comparison_evaluates_six_and_identifies_supported_middle():
    pre = state(funds=2000)
    pre.ships[1].cargo.megacredits = 600
    reference = slices(PLACEMENTS[0], SLOTS[1]).step(pre, orders(transfer=True))
    assert reference.supported and reference.state is not None
    result = reconcile_all_standard_tech_phase_orders(
        pre, reference.state, orders(transfer=True), specs(),
        complete_orders=True, complete_snapshots=True,
        standard_tech_level_caps=CAPS,
    )
    assert len(result.placements) == 6
    labels = [r.placement for r in result.placements]
    assert len(set(labels)) == 6
    assert labels == [p + "|" + slot for slot in SLOTS for p in PLACEMENTS]
    expected_label = PLACEMENTS[0] + "|" + SLOTS[1]
    assert expected_label in result.full_match_placements
    assert any(c.status == "ABSTAIN_PLACEMENT_UNSUPPORTED" for c in result.placements)
    assert result.status.startswith("CONDITIONAL_FULL_MATCH")
    assert not result.nuhost_orders_executed_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified


def test_no_tech_five_or_six_way_search_fails_closed():
    before = fixture()
    observed = deepcopy(before)
    observed.turn += 1
    for complete_orders, complete_snapshots, caps, order_set, wanted in (
        (False, True, CAPS, orders(), "ABSTAIN_INCOMPLETE_ORDER_OR_SNAPSHOT_COVERAGE"),
        (True, False, CAPS, orders(), "ABSTAIN_INCOMPLETE_ORDER_OR_SNAPSHOT_COVERAGE"),
        (True, True, None, orders(), "ABSTAIN_UNSUPPORTED_TECH_PRICING_SCOPE"),
        (True, True, CAPS, TurnOrders.empty(), "ABSTAIN_NO_EXPLICIT_TECH_ORDERS"),
    ):
        result = reconcile_all_standard_tech_phase_orders(
            before, observed, order_set, specs(),
            complete_orders=complete_orders,
            complete_snapshots=complete_snapshots,
            standard_tech_level_caps=caps,
        )
        assert result.status == wanted
        assert not result.full_match_placements
        assert not result.placements


def test_middle_slot_observed_mismatch_has_signed_residual_not_host_promotion():
    pre = state()
    actual = slices(PLACEMENTS[0], SLOTS[1]).step(pre, orders()).state
    assert actual is not None
    observed = deepcopy(actual)
    observed.planets[10].cargo.megacredits += 21
    out = reconcile_explicit_orders(
        pre, observed, orders(), specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement=SLOTS[1],
        standard_tech_level_caps=CAPS,
    )
    assert out.status == "CONDITIONAL_UNATTRIBUTED_MISMATCH"
    assert any(
        x.resource_residuals.get("planets", {}).get(10, {}).get("megacredits") == 21
        for x in out.placements if x.status == "CONDITIONAL_MODELED"
    )


def test_v2_all_owner_signatures_required_to_enumerate_six():
    pre = state()
    ref = slices(PLACEMENTS[0], SLOTS[1]).step(pre, orders()).state
    assert ref is not None
    key1, key2 = b"1" * 32, b"2" * 32
    rows = [
        seal_owner_observation_v2(
            pre, orders().by_player[1],
            captured_at_utc="2026-10-19T12:00:00Z",
            key=key1, key_id="one",
        ),
        seal_owner_observation_v2(
            pre, orders().by_player[2],
            captured_at_utc="2026-10-19T12:00:00Z",
            key=key2, key_id="two",
        ),
    ]
    params = dict(
        owner_keyrings={1: {"one": key1}, 2: {"two": key2}},
        observed_host_start_utc="2026-10-19T12:01:00Z",
        complete_snapshots=True, standard_tech_level_caps=CAPS,
    )
    accepted = reconcile_owner_observations_v2_all_tech_phase_orders(
        pre, ref, rows, specs(), **params,
    )
    assert accepted.status.startswith("CONDITIONAL_FULL_MATCH")
    assert len(accepted.placements) == 6
    assert accepted.order_source.startswith("ADMITTED_ALL_PLAYERS_OPERATOR_SIGNED_V2")
    assert not accepted.nuhost_orders_executed_verified
    assert not accepted.independent_host_parity_verified

    missing = reconcile_owner_observations_v2_all_tech_phase_orders(
        pre, ref, rows[:1], specs(), **params,
    )
    assert missing.status == "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE"
    assert missing.placements == ()
    assert not missing.full_match_placements

    tampered = deepcopy(rows)
    tampered[0]["payload"]["player_orders"]["starbase_tech_orders"][0]["engine"] = 9
    invalid = reconcile_owner_observations_v2_all_tech_phase_orders(
        pre, ref, tampered, specs(), **params,
    )
    assert invalid.status == "ABSTAIN_INVALID_ATTESTATION"
    assert invalid.placements == ()
