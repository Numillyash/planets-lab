"""Self-verifying M2 research vertical slice; Python stdlib only beyond planets_lab.

The scenario source is independent of pytest. CI still executes the full pytest
suite; the server's minimal research environment runs these embedded runtime
acceptance gates before publication.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from planetary_order_aware_scenarios_v1 import (
    fixture, order, orders_sequence, specs, unsupported_scenarios,
)
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice

SCHEMA = "planets-lab.planetary-order-aware-slice.v1"
PLACEMENTS = ("transfer_before_planetary", "transfer_after_planetary")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"M2 runtime gate failed: {message}")


def trace(placement: str) -> list[dict[str, object]]:
    sim = PlanetaryOrderAwareSlice(specs(), placement)
    state = fixture()
    steps: list[dict[str, object]] = []
    for index, orders in enumerate(orders_sequence()):
        unchanged = state.clone()
        result = sim.step(state, orders, seed=13 + index)
        require(state == unchanged, "input state modified")
        require(result.state is not None and result.supported, "unexpected abstention")
        require(result.state.turn == state.turn + 1, "turn was not advanced once")
        require(len(result.balances) == 15, "phase count drift")
        phase_names = [balance.phase for balance in result.balances]
        expected_transfer_index = 0 if placement == "transfer_before_planetary" else 14
        require(phase_names.index("planet_cargo_transfer") == expected_transfer_index,
                "explicit transfer placement drift")
        transfer = result.balances[expected_transfer_index]
        require(transfer.category == "explicit_transfer", "transfer category drift")
        require(not transfer.combined_net_delta and not transfer.ground_mineral_delta,
                "transfer conservation violated")
        if index < 2:
            require(len([event for event in result.events
                         if event.phase == "planet_cargo_transfer"]) == 1,
                    "expected one explicit cargo operation")
        else:
            require(not any(event.phase == "planet_cargo_transfer" for event in result.events),
                    "cargo operation appeared without order")
        require(
            any(balance.phase == "factory_supplies" and
                balance.combined_net_delta.get("supplies", 0) > 0
                for balance in result.balances),
            "factory production not accounted",
        )
        require(
            any(balance.phase == "tax_collection" and
                balance.combined_net_delta.get("megacredits", 0) > 0
                for balance in result.balances),
            "tax income not accounted",
        )
        require(
            any(balance.phase == "mineral_mining" and
                balance.planet_cargo_delta.get(10, {}).get("duranium", 0) > 0 and
                balance.ground_mineral_delta.get(10, {}).get("duranium", 0) < 0
                for balance in result.balances),
            "mining surface/ground accounting not detected",
        )
        expected_ship = (
            (30, 20, 15),
            (26, 15, 12),
            (26, 15, 12),
        )[index]
        actual_ship = result.state.ships[1].cargo
        require(
            (actual_ship.supplies, actual_ship.neutronium, actual_ship.clans)
            == expected_ship,
            f"transfer outcome drift on turn {index}",
        )
        steps.append({
            "from_turn": state.turn,
            "to_turn": result.state.turn,
            "phase_balances": [asdict(balance) for balance in result.balances],
            "events": [asdict(event) for event in result.events],
            "planet_resources": asdict(result.state.planets[10].cargo),
            "ship_resources": asdict(actual_ship),
            "underground_duranium": result.state.planets[10].ground_duranium.amount,
        })
        state = result.state
    require(state.turn == 10, "terminal turn drift")
    return steps


def fail_closed_controls() -> dict[str, str]:
    outcomes = {}
    for label, state, static_specs, orders in unsupported_scenarios():
        unchanged = state.clone()
        outcome = PlanetaryOrderAwareSlice(
            static_specs, "transfer_before_planetary"
        ).attempt_step(state, orders)
        require(outcome.status == "ABSTAIN_UNSUPPORTED_OR_INVALID",
                f"{label} was not abstained")
        require(outcome.state is None and not outcome.events and not outcome.balances,
                f"{label} leaked partial modeled state or evidence")
        require(state == unchanged, f"{label} mutated input on abstention")
        require(bool(outcome.abstain_reason), f"{label} missing refusal reason")
        outcomes[label] = outcome.status
    require(len(outcomes) == 8, "unsupported-control cohort size drift")

    # A historical phase boundary is NOT promoted merely because one
    # hypothetical ordering can satisfy an internal transfer.
    source = fixture()
    before = PlanetaryOrderAwareSlice(
        specs(), "transfer_before_planetary"
    ).attempt_step(source, order(supplies=45))
    after = PlanetaryOrderAwareSlice(
        specs(), "transfer_after_planetary"
    ).attempt_step(source, order(supplies=45))
    require(not before.supported and before.state is None,
            "pre-economy unsupported order unexpectedly succeeded")
    require(after.supported and after.state is not None and
            after.state.ships[1].cargo.supplies == 65,
            "post-economy conditional control drift")
    require(source == fixture(), "phase-order counterfactual mutated input")
    return outcomes


def build_report() -> dict[str, object]:
    # No external databases, no authenticated archival orders, no pytest import.
    abstentions = fail_closed_controls()
    traces = {placement: trace(placement) for placement in PLACEMENTS}
    require(traces == {placement: trace(placement) for placement in PLACEMENTS},
            "non-deterministic full trajectory")
    require(all(len(steps) == 3 and steps[-1]["to_turn"] == 10
                for steps in traces.values()), "three-turn composition failed")
    raw = json.dumps(traces, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": SCHEMA,
        "status": "M2_ORDER_AWARE_INTERNAL_TESTED_NOT_NUHOST_DIFFERENTIAL",
        "phase_boundary": "HYPOTHETICAL_BOTH_PLACEMENTS_NOT_NUHOST_CAUSAL",
        "trace_sha256": sha256(raw).hexdigest(),
        "summary": {
            "modeled_turns_per_placement": 3,
            "placements": len(traces),
            "phase_balances_per_turn": 15,
            "runtime_abstention_controls_passed": len(abstentions),
            "runtime_self_checks_passed": True,
            "actual_NuHost_orders_authenticated": 0,
            "NuHost_phase_order_verified": False,
            "historical_differential_verified": False,
            "canonical_combat_changes": 0,
        },
        "abstention_controls": abstentions,
        "limitations": [
            "no purchase or build orders",
            "no ship movement, missions, combat, starbases or ion storms",
            "no order authenticity from historical archives",
            "unresolved full NuHost global chronology and racial mechanics",
        ],
        "traces": traces,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_suffix(".json.tmp")
    staged.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    staged.replace(args.output)
    print("===== M2 ORDER-AWARE PLANETARY SLICE =====")
    print("status:", result["status"])
    print("summary:", result["summary"])
    print("trace_sha256:", result["trace_sha256"])
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
