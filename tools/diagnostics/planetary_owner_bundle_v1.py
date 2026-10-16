"""Synthetic owner-scoped cargo admission gate: private envelopes never published."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from planetary_order_aware_scenarios_v1 import fixture, order, specs
from planets_lab.sim.orders import PlayerOrders
from planets_lab.sim.planetary_owner_capture import (
    aggregate_owner_observations, seal_owner_observation,
    simulate_owner_bundle,
)
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice

SCHEMA = "planets-lab.prehost-owner-bundle-controls.v1"
T1, T2 = b"research-player1-key-only-not-production-v1", b"research-player2-key-only-not-production-v1"
KEYS = {1: {"player1-test": T1}, 2: {"player2-test": T2}}
STAMP = "2026-10-16T08:00:00Z"
HOST_START = "2026-10-16T09:00:00Z"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("owner-bundle gate: " + message)


def input_bundle():
    state = fixture()
    own1 = order(supplies=10, clans=5, neutronium=5).by_player[1]
    own2 = PlayerOrders(player_id=2)
    a = seal_owner_observation(
        state, own1, captured_at_utc=STAMP, key=T1, key_id="player1-test",
    )
    b = seal_owner_observation(
        state, own2, captured_at_utc=STAMP, key=T2, key_id="player2-test",
    )
    return state, a, b


def build_report():
    state, a, b = input_bundle()
    original = state.clone()
    admission = aggregate_owner_observations(
        [b, a], state, owner_keyrings=KEYS, observed_host_start_utc=HOST_START,
    )
    require(admission.admitted and admission.orders is not None, "complete cohort rejected")
    require(admission.covered_player_ids == (1, 2), "wrong player coverage")
    placement_outcomes = {}
    for placement in ("transfer_before_planetary", "transfer_after_planetary"):
        sim = simulate_owner_bundle(
            PlanetaryOrderAwareSlice(specs(), placement),
            state, [a, b], owner_keyrings=KEYS,
            observed_host_start_utc=HOST_START,
            seed=23,
        )
        require(sim.outcome is not None and sim.outcome.supported, "supported model refused")
        require(len(sim.outcome.balances) == 15, "phase count drift")
        transfer = next(
            entry for entry in sim.outcome.balances
            if entry.category == "explicit_transfer"
        )
        require(
            not transfer.combined_net_delta and not transfer.ground_mineral_delta,
            "transfer resource conservation lost",
        )
        placement_outcomes[placement] = {
            "status": sim.status,
            "phase_balances": len(sim.outcome.balances),
            "resource_conservation_passed": True,
        }
    controls = {}
    controls["missing_player2"] = (
        [a], state, KEYS, HOST_START, "ABSTAIN_INCOMPLETE_PLAYER_COVERAGE",
    )
    controls["duplicate_owner"] = (
        [a, a, b], state, KEYS, HOST_START, "ABSTAIN_DUPLICATE_OWNER",
    )
    modified = deepcopy(a)
    modified["payload"]["player_orders"]["ship_orders"][0]["planet_transfer"]["supplies"] += 1
    controls["modified_signed_cargo"] = (
        [modified, b], state, KEYS, HOST_START, "ABSTAIN_INVALID_ATTESTATION",
    )
    controls["wrong_owner_key"] = (
        [a, b], state, {1: {"player1-test": T2}, 2: KEYS[2]}, HOST_START,
        "ABSTAIN_INVALID_ATTESTATION",
    )
    controls["missing_host_witness"] = (
        [a, b], state, KEYS, None, "ABSTAIN_UNWITNESSED_TIME",
    )
    controls["host_before_capture"] = (
        [a, b], state, KEYS, STAMP, "ABSTAIN_NOT_PREHOST",
    )
    changed = state.clone()
    changed.planets[10].cargo.supplies += 1
    controls["changed_initial_state"] = (
        [a, b], changed, KEYS, HOST_START, "ABSTAIN_STATE_IDENTITY",
    )
    fraudulent = deepcopy(b)
    fraudulent["payload"]["server_submission_acknowledged"] = True
    controls["forged_ack_claim"] = (
        [a, fraudulent], state, KEYS, HOST_START, "ABSTAIN_INVALID_SCOPE",
    )
    outcome_counts = {}
    for label, (captures, prestate, keys, host_start, expected) in controls.items():
        result = aggregate_owner_observations(
            captures, prestate, owner_keyrings=keys,
            observed_host_start_utc=host_start,
        )
        require(result.status == expected, f"{label} produced {result.status}")
        require(result.orders is None, f"{label} leaked partial orders")
        outcome_counts[label] = result.status
    require(state == original, "source state mutated")
    return {
        "schema": SCHEMA,
        "status": "M2_OWNER_SCOPED_CAPTURE_SYNTHETIC_TESTED_NO_NUHOST_ORDERS",
        "summary": {
            "synthetic_players_independently_signed": 2,
            "complete_bundle_accepted": True,
            "missing_player_abstains": True,
            "placement_count": 2,
            "abstain_controls_passed": len(outcome_counts),
            "source_state_unchanged": True,
            "NuHost_orders_authenticated": False,
            "independent_server_submission_acknowledged": False,
            "independent_clock_provenance_verified": False,
            "historical_differential_verified": False,
            "corpus_files_opened": 0,
            "C5_changes": 0,
        },
        "placements": placement_outcomes,
        "controls": outcome_counts,
        "limitations": [
            "operator signatures are not NuHost server acknowledgements",
            "synthetic captures only; no private owner orders read",
            "caller-supplied host clock is not independently attested",
            "no causal NuHost phase order or historical validation",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_suffix(".json.tmp")
    staged.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staged.replace(args.output)
    print("===== M2 OWNER-SCOPED PREHOST CAPTURE BUNDLE =====")
    print("status:", result["status"])
    print("summary:", result["summary"])
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
