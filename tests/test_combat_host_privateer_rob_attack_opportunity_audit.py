from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_privateer_rob_attack_opportunity_audit import (  # noqa: E402
    _cloak_label,
    _factual_outcome,
    _rob_pe_zero_target,
)


def _rob_ship(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "mission": 9,
        "enemy": 0,
        "iscloaked": True,
    }
    raw.update(overrides)
    return raw


def test_rob_pe_zero_target_requires_privateer_mission9_cloak_hull_and_no_pe() -> None:
    raw = _rob_ship()
    assert _rob_pe_zero_target(race_id=5, raw=raw, hull_can_cloak=True) is True
    assert _rob_pe_zero_target(race_id=3, raw=raw, hull_can_cloak=True) is False
    assert _rob_pe_zero_target(race_id=5, raw=_rob_ship(mission=3), hull_can_cloak=True) is False
    assert _rob_pe_zero_target(race_id=5, raw=raw, hull_can_cloak=False) is False
    assert _rob_pe_zero_target(race_id=5, raw=_rob_ship(enemy=6), hull_can_cloak=True) is False


def test_rob_pe_zero_target_treats_missing_or_zero_pe_as_no_request() -> None:
    assert _rob_pe_zero_target(race_id=5, raw=_rob_ship(enemy=None), hull_can_cloak=True) is True
    assert _rob_pe_zero_target(race_id=5, raw=_rob_ship(enemy=0), hull_can_cloak=True) is True


def test_factual_outcome_distinguishes_pair_and_skip_shapes() -> None:
    pairs = {(190, 264)}
    assert _factual_outcome(factual_pairs=pairs, target_ship_id=190, attacker_ship_id=264) == "pair_vcr"
    assert _factual_outcome(factual_pairs=pairs, target_ship_id=98, attacker_ship_id=264) == "attacker_fought_other"
    assert _factual_outcome(factual_pairs=pairs, target_ship_id=190, attacker_ship_id=99) == "target_fought_other"
    assert _factual_outcome(factual_pairs=pairs, target_ship_id=98, attacker_ship_id=99) == "neither_vcr"


def test_factual_outcome_detects_both_fought_other() -> None:
    pairs = {(10, 20), (30, 40)}
    assert _factual_outcome(factual_pairs=pairs, target_ship_id=10, attacker_ship_id=30) == "both_fought_other"


def test_cloak_label_is_tri_state() -> None:
    assert _cloak_label(True) == "true"
    assert _cloak_label(False) == "false"
    assert _cloak_label(None) == "unknown"
