"""Deterministic M2 research vertical-slice report (not NuHost validation)."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_planetary_order_aware_slice import fixture, order, specs
from planets_lab.sim.orders import TurnOrders
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice

SCHEMA = "planets-lab.planetary-order-aware-slice.v1"


def trace(placement: str):
    sim = PlanetaryOrderAwareSlice(specs(), placement)
    state = fixture()
    steps = []
    for index, orders in enumerate((
        order(supplies=10, neutronium=10, clans=5),
        order("ship_to_planet", supplies=4, neutronium=5, clans=3),
        TurnOrders.empty(),
    )):
        result = sim.step(state, orders, seed=13 + index)
        assert result.state is not None and result.supported
        steps.append({
            "from_turn": state.turn,
            "to_turn": result.state.turn,
            "phase_balances": [asdict(b) for b in result.balances],
            "events": [asdict(e) for e in result.events],
            "planet_resources": asdict(result.state.planets[10].cargo),
            "ship_resources": asdict(result.state.ships[1].cargo),
            "underground_duranium": result.state.planets[10].ground_duranium.amount,
        })
        state = result.state
    return steps


def build_report():
    traces = {placement: trace(placement) for placement in (
        "transfer_before_planetary", "transfer_after_planetary",
    )}
    if traces != {k: trace(k) for k in traces}:
        raise RuntimeError("non-deterministic full trajectory")
    for steps in traces.values():
        assert len(steps) == 3
        assert all(len(step["phase_balances"]) == 15 for step in steps)
        assert steps[-1]["to_turn"] == 10
        for step in steps:
            for balance in step["phase_balances"]:
                if balance["category"] == "explicit_transfer":
                    assert not balance["combined_net_delta"]
                    assert not balance["ground_mineral_delta"]
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
            "actual_NuHost_orders_authenticated": 0,
            "NuHost_phase_order_verified": False,
            "historical_differential_verified": False,
            "canonical_combat_changes": 0,
        },
        "limitations": [
            "no purchase or build orders",
            "no ship movement, missions, combat, starbases or ion storms",
            "no order authenticity from historical archives",
            "unresolved full NuHost global chronology and racial mechanics",
        ],
        "traces": traces,
    }


def main():
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
