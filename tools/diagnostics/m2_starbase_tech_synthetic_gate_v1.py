"""Dependency-light M2 synthetic starbase technology gate; no corpus or credentials.

Explicit standard-rule hypotheses are local tests, NOT independent NuHost
orders, receipts, or phase-order evidence. No private observations are read.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "diagnostics"))

from planets_lab.core import Starbase
from planets_lab.data.nu_build_cost_calibration import (
    published_standard_tech_upgrade_cost_mc,
)
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder,
    StarbaseTechUpgradeOrder, TurnOrders,
)
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_conditional_reconciliation import (
    reconcile_explicit_orders,
)
from planetary_order_aware_scenarios_v1 import fixture, specs


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def state_with_base(planet_mc: int):
    state = fixture()
    state.planets[10].cargo.megacredits = planet_mc
    state.starbases[10] = Starbase(planet_id=10, owner_id=1, tech_engine=7)
    return state


def orders(with_transfer: bool = False):
    ships = (
        (ShipOrder(
            ship_id=1, planet_transfer=PlanetCargoTransferOrder(
                planet_id=10, direction="ship_to_planet", megacredits=600,
            ),
        ),)
        if with_transfer else ()
    )
    return TurnOrders(by_player={
        1: PlayerOrders(
            player_id=1,
            ship_orders=ships,
            starbase_tech_orders=(StarbaseTechUpgradeOrder(planet_id=10, engine=10),),
        ),
    })


def pipe(tech_placement: str, cap: int = 10):
    return PlanetaryOrderAwareSlice(
        specs(), "transfer_before_planetary",
        tech_placement=tech_placement,
        standard_tech_level_caps={1: cap},
    )


def main() -> int:
    checks = 0
    initial = state_with_base(3000)
    copy = deepcopy(initial)
    price = published_standard_tech_upgrade_cost_mc(7, 10)
    require(price == 2400, "incorrect documented standard level-cost table")
    checks += 1

    for placement in ("tech_before_planetary", "tech_after_planetary"):
        outcome = pipe(placement).attempt_step(initial, orders())
        require(outcome.supported and outcome.state is not None, "upgrade unexpectedly unsupported")
        require(outcome.state.starbases[10].tech_engine == 10, "tech target not set")
        ledger = [x for x in outcome.balances if x.phase == "starbase_tech_upgrade"]
        require(len(ledger) == 1, "tech phase missing or duplicated")
        record = ledger[0]
        require(record.combined_net_delta == {"megacredits": -price}, "nonconserved purchase")
        require(record.planet_cargo_delta == {10: {"megacredits": -price}}, "MC wrong source")
        require(not record.ship_cargo_delta and not record.ground_mineral_delta,
                "purchase unexpectedly changed other resource sections")
        require(initial == copy, "source state mutated")
        checks += 1

    funded = state_with_base(2000)
    funded.ships[1].cargo.megacredits = 600
    cannot_pay = pipe("tech_before_planetary").attempt_step(funded, orders(True))
    can_pay = pipe("tech_after_planetary").attempt_step(funded, orders(True))
    require(not cannot_pay.supported and cannot_pay.state is None
            and not cannot_pay.balances, "failed placement exposed partial state")
    require(can_pay.supported and can_pay.state is not None
            and can_pay.state.starbases[10].tech_engine == 10,
            "explicit transfer did not finance conditional purchase")
    checks += 1

    insufficient = pipe("tech_after_planetary", cap=7).attempt_step(initial, orders())
    require(not insufficient.supported and insufficient.state is None,
            "unverified tech eligibility silently accepted")
    checks += 1

    after = pipe("tech_before_planetary").step(initial, orders()).state
    require(after is not None, "modeled state missing")
    differential = reconcile_explicit_orders(
        initial, after, orders(), specs(),
        complete_orders=True, complete_snapshots=True,
        tech_placement="tech_before_planetary",
        standard_tech_level_caps={1: 10},
    )
    require(bool(differential.full_match_placements), "synthetic poststate mismatch")
    require(not differential.nuhost_orders_executed_verified
            and not differential.independent_host_parity_verified,
            "synthetic equality was incorrectly promoted to NuHost evidence")
    checks += 1

    print("===== M2 SYNTHETIC STARBASE TECH GATE =====")
    print("status: M2_STANDARD_STARBASE_TECH_LOCAL_TESTED_NOT_NUHOST_VERIFIED")
    print(f"checks: {checks}")
    print(f"standard_engine_7_to_10_cost_mc: {price}")
    print("phase_placements_tested: 2")
    print("orders_independently_server_authenticated: false")
    print("historical_differential_verified: false")
    print("nu_host_phase_order_verified: false")
    print("corpus_read: false")
    print("heldout_entity_records_read: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
