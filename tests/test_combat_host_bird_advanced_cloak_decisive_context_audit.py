from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_advanced_cloak_decisive_context_audit import (  # noqa: E402
    _active_glory,
    _distance_to_site,
    _stable_same_ship,
)


def test_active_glory_recognizes_pop_and_trg_only_on_glory_hull() -> None:
    assert _active_glory({"friendlycode": "POP"}, "Glory Device") == (True, "pop")
    assert _active_glory({"friendlycode": "TrG"}, "Glory Device") == (True, "trg")
    assert _active_glory({"friendlycode": "abc"}, "Glory Device") == (False, "abc")
    assert _active_glory({"friendlycode": "POP"}, "Advanced Cloak") == (False, None)


def test_stable_same_ship_requires_owner_and_hull_identity() -> None:
    assert _stable_same_ship(
        before_owner=3,
        before_hull=31,
        after_owner=3,
        after_raw={"hullid": 31},
    ) is True
    assert _stable_same_ship(
        before_owner=3,
        before_hull=31,
        after_owner=4,
        after_raw={"hullid": 31},
    ) is False
    assert _stable_same_ship(
        before_owner=3,
        before_hull=31,
        after_owner=3,
        after_raw={"hullid": 47},
    ) is False


def test_distance_to_site() -> None:
    assert _distance_to_site((10, 10), (13, 14)) == 5.0
    assert _distance_to_site(None, (13, 14)) is None
