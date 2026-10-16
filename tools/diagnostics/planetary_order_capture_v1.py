"""Research-only pre-Host order capture admission demonstration and controls.

No NuHost, public8 corpus or real private player orders are read. All HMAC
tokens in this program are TEST ONLY and MUST NOT protect real user data.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from planetary_order_aware_scenarios_v1 import fixture, order, specs
from planets_lab.sim.orders import PlayerOrders, TurnOrders
from planets_lab.sim.planetary_order_capture import (
    admit_prehost_capture, seal_prehost_capture, simulate_admitted_capture,
    state_fingerprint,
)
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice

SCHEMA = "planets-lab.prehost-order-capture-controls.v1"
TEST_ONLY_KEY = b"synthetic-operator-key-never-for-production-v1"
KEYS = {"synthetic-fixture-only": TEST_ONLY_KEY}
CAPTURE = "2026-10-16T08:00:00Z"
WITNESS = "2026-10-16T09:00:00Z"


def check(value: bool, why: str) -> None:
    if not value:
        raise RuntimeError("prehost admission gate failed: " + why)


def complete():
    orders = order(supplies=10, neutronium=5, clans=5)
    return TurnOrders(by_player={
        1: orders.by_player[1],
        2: PlayerOrders(player_id=2),
    })


def seal(state=None, captured=CAPTURE):
    return seal_prehost_capture(
        fixture() if state is None else state,
        complete(),
        captured_at_utc=captured,
        key=TEST_ONLY_KEY,
        key_id="synthetic-fixture-only",
    )


def report():
    state = fixture()
    unchanged = state.clone()
    raw = seal(state)
    admitted = admit_prehost_capture(
        raw, state, keyring=KEYS, observed_host_start_utc=WITNESS,
    )
    check(admitted.admitted and admitted.orders == complete(),
          "complete signed synthetic capture not admitted")
    placements = {}
    for placement in ("transfer_before_planetary", "transfer_after_planetary"):
        result = simulate_admitted_capture(
            PlanetaryOrderAwareSlice(specs(), placement),
            state, raw, keyring=KEYS, observed_host_start_utc=WITNESS, seed=29,
        )
        check(result.outcome is not None and result.outcome.supported, "model not run")
        out = result.outcome
        check(out.state is not None and out.state.turn == 8, "next-state invalid")
        check(len(out.balances) == 15, "phase inventory count drift")
        phase = next(x for x in out.balances if x.category == "explicit_transfer")
        check(not phase.combined_net_delta and not phase.ground_mineral_delta,
              "transfer conservation violated")
        check(state == unchanged, "input state mutated by captured simulation")
        placements[placement] = {
            "status": result.status,
            "to_turn": out.state.turn,
            "phase_resource_balances": len(out.balances),
            "transfer_conservation_checked": True,
            "happiness_and_economy_original_phases_reused": True,
        }

    controls = {}
    tampered = deepcopy(raw)
    tampered["payload"]["orders"][0]["ship_orders"][0]["planet_transfer"]["supplies"] += 1
    controls["changed_signed_transfer"] = (tampered, state, KEYS, WITNESS)
    controls["wrong_key"] = (raw, state, {"synthetic-fixture-only": b"x" * 32}, WITNESS)
    controls["unknown_key"] = (raw, state, {}, WITNESS)
    controls["no_host_start_witness"] = (raw, state, KEYS, None)
    controls["equal_capture_and_host_start"] = (raw, state, KEYS, CAPTURE)
    controls["retroactive_capture"] = (seal(captured="2026-10-16T10:00:00Z"), state, KEYS, WITNESS)
    changed = fixture()
    changed.planets[10].cargo.supplies += 1
    controls["changed_prehost_snapshot"] = (raw, changed, KEYS, WITNESS)
    controls["missing_capture"] = ({}, state, KEYS, WITNESS)
    control_statuses = {}
    for name, (envelope, prestate, keyring, host_start) in controls.items():
        outcome = simulate_admitted_capture(
            PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary"),
            prestate, envelope, keyring=keyring,
            observed_host_start_utc=host_start,
        )
        check(outcome.status.startswith("ABSTAIN_") and outcome.outcome is None,
              "fail-open on " + name)
        control_statuses[name] = outcome.status

    result = {
        "schema": SCHEMA,
        "status": "M2_SYNTHETIC_PREHOST_CAPTURE_ADMISSION_TESTED_NOT_NUHOST_VERIFIED",
        "summary": {
            "synthetic_capture_admitted": True,
            "synthetic_signed_capture_has_all_player_rows": True,
            "modeled_placement_count": len(placements),
            "abstention_controls_passed": len(control_statuses),
            "original_state_unchanged": state == unchanged,
            "actual_NuHost_order_submission_authenticated": False,
            "capture_timestamp_independently_attested": False,
            "NuHost_phase_order_verified": False,
            "historical_differential_verified": False,
            "corpus_files_opened": 0,
        },
        "pre_state_sha256": state_fingerprint(state),
        "placements": placements,
        "abstention_controls": control_statuses,
        "provenance_limitations": [
            "signed local record is NOT server acceptance evidence",
            "capture timestamp and Host boundary are SYNTHETIC",
            "real recorder must have independent pre-Host timing and owner authority",
            "capture API is offline: no authenticated NuHost orders acquired",
            "never publish private input envelopes, submitted orders or secret keys",
        ],
    }
    raw_result = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["report_content_without_digest_sha256"] = sha256(raw_result).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_suffix(".json.tmp")
    staged.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    staged.replace(args.output)
    print("===== M2 PREHOST ORDER CAPTURE ADMISSION =====")
    print("status:", result["status"])
    print("summary:", result["summary"])
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
