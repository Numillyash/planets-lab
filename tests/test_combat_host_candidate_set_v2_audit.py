from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from planets_lab.corpus.movement_mine_context import ObservedMineField

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_candidate_set_v2_audit import (  # noqa: E402
    _factual_position_status,
    _foreign_mine_route_risk,
    _pair_position_status,
)


class _MineContext:
    def __init__(self, fields: tuple[ObservedMineField, ...]) -> None:
        self.topology = SimpleNamespace(sphere=False, mapwidth=None, mapheight=None)
        self._fields = fields

    def fields(self, _turn: int) -> tuple[ObservedMineField, ...]:
        return self._fields


def _raw(**changes: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "x": 100,
        "y": 100,
        "targetx": 181,
        "targety": 100,
        "warp": 9,
        "damage": 0,
        "supplies": 0,
    }
    raw.update(changes)
    return raw


def _field(*, owner_id: int, web: bool = False, x: float = 140.0) -> ObservedMineField:
    return ObservedMineField(
        field_id=1,
        owner_id=owner_id,
        x=x,
        y=100.0,
        radius=8.0,
        is_web=web,
    )


def test_foreign_normal_mine_crossing_fails_closed() -> None:
    risk = _foreign_mine_route_risk(
        context=_MineContext((_field(owner_id=6),)),
        before_turn=10,
        owner_id=5,
        raw=_raw(),
        race_id=1,
        hull_id=16,
    )
    assert risk == "normal_mine_route_risk"


def test_foreign_web_crossing_fails_closed() -> None:
    risk = _foreign_mine_route_risk(
        context=_MineContext((_field(owner_id=6, web=True),)),
        before_turn=10,
        owner_id=5,
        raw=_raw(),
        race_id=1,
        hull_id=16,
    )
    assert risk == "web_mine_route_risk"


def test_own_field_does_not_make_position_unresolved() -> None:
    risk = _foreign_mine_route_risk(
        context=_MineContext((_field(owner_id=5),)),
        before_turn=10,
        owner_id=5,
        raw=_raw(),
        race_id=1,
        hull_id=16,
    )
    assert risk is None


def test_field_off_route_does_not_make_position_unresolved() -> None:
    risk = _foreign_mine_route_risk(
        context=_MineContext((_field(owner_id=6, x=260.0),)),
        before_turn=10,
        owner_id=5,
        raw=_raw(),
        race_id=1,
        hull_id=16,
    )
    assert risk is None


def test_factual_position_status_distinguishes_exact_mismatch_and_unresolved() -> None:
    assert _factual_position_status(
        prediction={"position": (10, 20), "source": "normal_move"},
        site=(10, 20),
    ) == ("exact", "normal_move")
    assert _factual_position_status(
        prediction={"position": (11, 20), "source": "normal_move"},
        site=(10, 20),
    ) == ("mismatch", "normal_move")
    assert _factual_position_status(
        prediction={"position": None, "source": "tow_target"},
        site=(10, 20),
    ) == ("unresolved", "tow_target")
    assert _factual_position_status(prediction=None, site=(10, 20)) == (
        "unresolved",
        "owner_current_missing",
    )


def test_pair_position_status_prefers_mismatch_over_unresolved() -> None:
    pair = (10, 20)
    assert _pair_position_status(pair, {10: "exact", 20: "exact"}) == "exact"
    assert _pair_position_status(pair, {10: "exact", 20: "unresolved"}) == "unresolved"
    assert _pair_position_status(pair, {10: "mismatch", 20: "unresolved"}) == "mismatch"
