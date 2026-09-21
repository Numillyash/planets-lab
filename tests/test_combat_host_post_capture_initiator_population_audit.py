from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_post_capture_initiator_population_audit import (  # noqa: E402
    _planet_attack_projection,
    _required_unresolved_total,
    _ship_request_projection,
)


def test_ship_opponent_independently_requests_new_owner() -> None:
    result = _ship_request_projection(
        {
            "mission": 3,
            "enemy": 0,
            "friendlycode": "800",
        },
        target_owner_id=3,
    )

    assert result["requests_target_owner"] is True


def test_ship_opponent_without_kill_or_pe_does_not_request_new_owner() -> None:
    result = _ship_request_projection(
        {
            "mission": 0,
            "enemy": 8,
            "friendlycode": "abc",
        },
        target_owner_id=3,
    )

    assert result["requests_target_owner"] is False


def test_planet_nuk_and_att_are_independent_attack_codes() -> None:
    assert _planet_attack_projection(
        {"friendlycode": "NUK"}
    )["independent_attack_code"] is True
    assert _planet_attack_projection(
        {"friendlycode": "att"}
    )["independent_attack_code"] is True


def test_planet_ordinary_friendly_code_is_not_attack_candidate() -> None:
    result = _planet_attack_projection({"friendlycode": "abc"})

    assert result["independent_attack_code"] is False



def test_optional_captured_ship_history_does_not_block_required_adapter_gate() -> None:
    counts = {
        "unresolved:captured_ship_tminus1": 2,
        "unresolved:next_vcr_missing": 0,
        "unresolved:opponent_projection": 0,
        "unresolved:opponent_object_id": 0,
        "unresolved:opponent_ship_tminus1": 0,
        "unresolved:opponent_planet_tminus1": 0,
    }

    assert _required_unresolved_total(counts) == 0


def test_required_opponent_state_still_blocks_adapter_gate() -> None:
    counts = {
        "unresolved:captured_ship_tminus1": 2,
        "unresolved:opponent_ship_tminus1": 1,
    }

    assert _required_unresolved_total(counts) == 1
