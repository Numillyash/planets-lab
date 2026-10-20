"""M2 readiness gates distinguish locally signed replay from Host evidence."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys

from planets_lab.core import Starbase
from planets_lab.sim.orders import PlayerOrders, StarbaseTechUpgradeOrder, TurnOrders
from planets_lab.sim.planetary_owner_capture_v2 import seal_owner_observation_v2
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice
from planets_lab.sim.planetary_host_differential_readiness import (
    assess_host_differential_evidence, EXTERNAL_BLOCKERS, LOCAL_STATUS,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs


def case():
    pre = fixture()
    pre.starbases[10] = Starbase(planet_id=10, owner_id=1, tech_engine=7)
    pre.planets[10].cargo.megacredits = 3000
    owner1 = PlayerOrders(player_id=1, starbase_tech_orders=(
        StarbaseTechUpgradeOrder(planet_id=10, engine=10),
    ))
    owner2 = PlayerOrders(player_id=2)
    orders = TurnOrders(by_player={1: owner1, 2: owner2})
    t = "2026-10-19T10:00:00Z"
    keys = {1: {"one": b"1" * 32}, 2: {"two": b"2" * 32}}
    envelopes = [
        seal_owner_observation_v2(pre, owner1, captured_at_utc=t, key=b"1" * 32, key_id="one"),
        seal_owner_observation_v2(pre, owner2, captured_at_utc=t, key=b"2" * 32, key_id="two"),
    ]
    modeled = PlanetaryOrderAwareSlice(
        specs(), "transfer_before_planetary",
        tech_placement="tech_after_planetary", standard_tech_level_caps={1: 10},
    ).step(pre, orders)
    assert modeled.state is not None
    opts = dict(
        owner_keyrings=keys, claimed_host_start_utc="2026-10-19T10:01:00Z",
        asserted_full_snapshot_coverage=True, standard_tech_level_caps={1: 10},
    )
    return pre, modeled.state, envelopes, opts


def test_all_local_checks_do_not_promote_causality():
    before, after, captured, options = case()
    copy = deepcopy(before)
    result = assess_host_differential_evidence(
        before, after, captured, specs(), **options,
    )
    assert result.status == LOCAL_STATUS
    assert result.complete_owner_v2_signatures_admitted
    assert result.structurally_supported_adjacent_state_pair
    assert result.bounded_model_evaluated
    assert result.conditional_full_match_count > 0
    assert result.external_evidence_blockers == EXTERNAL_BLOCKERS
    assert not result.nuhost_execution_verified
    assert not result.diff_verified
    assert not result.raw_private_data_returned
    assert before == copy
    assert "research-slice" not in repr(result)
    assert "2026-10-19" not in repr(result)


def test_missing_coverage_caps_and_owner_abstain():
    pre, post, signed, options = case()
    for change, expected in (
        ("coverage", "ABSTAIN_FULL_SNAPSHOT_COVERAGE_NOT_ASSERTED"),
        ("caps", "ABSTAIN_TECH_LEVEL_ELIGIBILITY_NOT_ASSERTED"),
        ("owner", "ABSTAIN_LOCAL_OWNER_V2_ADMISSION"),
        ("time", "ABSTAIN_LOCAL_OWNER_V2_ADMISSION"),
    ):
        opts = options.copy()
        captures = signed[:]
        if change == "coverage":
            opts["asserted_full_snapshot_coverage"] = False
        elif change == "caps":
            opts["standard_tech_level_caps"] = None
        elif change == "owner":
            captures.pop()
        elif change == "time":
            opts["claimed_host_start_utc"] = None
        result = assess_host_differential_evidence(pre, post, captures, specs(), **opts)
        assert result.status == expected
        assert not result.diff_verified


def test_tampered_signature_and_unmodeled_observation_fail_closed():
    pre, post, signed, options = case()
    tampered = deepcopy(signed)
    tampered[0]["payload"]["player_orders"]["starbase_tech_orders"][0]["engine"] = 9
    result = assess_host_differential_evidence(pre, post, tampered, specs(), **options)
    assert result.status == "ABSTAIN_LOCAL_OWNER_V2_ADMISSION"
    assert result.bounded_model_status == "ABSTAIN_INVALID_ATTESTATION"
    changed = deepcopy(post)
    changed.starbases[10].fighters += 1
    result = assess_host_differential_evidence(pre, changed, signed, specs(), **options)
    assert result.status == "ABSTAIN_UNSUPPORTED_OR_INCOMPLETE_STATE_PAIR"
    changed = deepcopy(post)
    changed.planets[10].cargo.megacredits += 17
    result = assess_host_differential_evidence(pre, changed, signed, specs(), **options)
    assert result.status == "LOCAL_CONDITIONAL_MISMATCH_NOT_HOST_VERIFIED"
    assert result.conditional_full_match_count == 0
    assert not result.diff_verified
