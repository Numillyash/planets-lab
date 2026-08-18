from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import hypot
from typing import Any

from .movement_differential import _intish
from .movement_residual_context import _owner_record
from .reconstruction import PerspectiveRecord


# The fallback-navigation reconstruction is currently corpus-verified only for
# historical game 591478. The raw game metadata reports 2150x2150, while the
# observed wrapped coordinate relationships used by the Red Mite study match
# period 2170. Keep this as explicit evidence-scoped context; never infer a
# general mapwidth+20 rule from it.
_SCOPED_WRAP_PERIODS: Mapping[int, tuple[int, int]] = {591478: (2170, 2170)}
ROUND_TOLERANCE_LY = 1.5
EPS = 1e-9


@dataclass(frozen=True, slots=True)
class MiteFallbackRun:
    ship_id: int
    identity: tuple[int, int, str | None, int]
    target_id: int
    tracking_start: int
    tracking_end: int
    anchor: tuple[int, int]


def _identity(owner_id: int | None, raw: Mapping[str, Any] | None) -> tuple[int, int, str | None, int] | None:
    if owner_id is None or owner_id <= 0 or raw is None:
        return None
    hull_id = _intish(raw.get("hullid"))
    raw_turn = _intish(raw.get("turn"))
    if hull_id is None or raw_turn is None:
        return None
    name_value = raw.get("name")
    name = str(name_value) if name_value is not None else None
    return owner_id, hull_id, name, raw_turn


def _xy(raw: Mapping[str, Any] | None) -> tuple[int, int] | None:
    if raw is None:
        return None
    x = _intish(raw.get("x"))
    y = _intish(raw.get("y"))
    if x is None or y is None:
        return None
    return x, y


def _wp(raw: Mapping[str, Any] | None) -> tuple[int, int] | None:
    if raw is None:
        return None
    x = _intish(raw.get("targetx"))
    y = _intish(raw.get("targety"))
    if x is None or y is None:
        return None
    return x, y


def _axis_delta(start: int, end: int, period: int) -> int:
    raw = end - start
    candidates = (raw - period, raw, raw + period)
    return min(candidates, key=lambda value: (abs(value), abs(value - raw)))


def _distance(
    left: tuple[int, int] | None,
    right: tuple[int, int] | None,
    *,
    periods: tuple[int, int],
) -> float | None:
    if left is None or right is None:
        return None
    dx = _axis_delta(left[0], right[0], periods[0])
    dy = _axis_delta(left[1], right[1], periods[1])
    return hypot(dx, dy)


def _same_point(
    left: tuple[int, int] | None,
    right: tuple[int, int] | None,
    *,
    periods: tuple[int, int],
) -> bool:
    value = _distance(left, right, periods=periods)
    return value is not None and value <= EPS


def _owner_records(
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
) -> dict[tuple[int, int], tuple[int, Mapping[str, Any]]]:
    result: dict[tuple[int, int], tuple[int, Mapping[str, Any]]] = {}
    for key, group in ship_groups.items():
        owner_id, record = _owner_record(group)
        if owner_id is None or owner_id <= 0 or record is None:
            continue
        result[key] = (owner_id, record.raw)
    return result


def discover_scoped_mite_fallback_runs(
    *,
    game_id: int,
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    mite_hulls: frozenset[int],
) -> Mapping[int, tuple[MiteFallbackRun, ...]]:
    """Recover clean Red Mite fallback origins for evidence-scoped games.

    A run is admitted only when the observed target identity is continuous from
    S-1 through S and across the last active tracking snapshot -> clear snapshot,
    while the Mite itself remains the same exact identity and clears to
    mission=0/mission1target=0. This mirrors the clean corpus population used by
    docs/rules/red-mite-tracking.md rather than generalizing from numeric ship ids.
    """

    if game_id not in _SCOPED_WRAP_PERIODS:
        return {}

    owner_records = _owner_records(ship_groups)
    tracking_turns: dict[tuple[int, tuple[int, int, str | None, int], int], list[int]] = defaultdict(list)

    for (turn, ship_id), (owner_id, raw) in sorted(owner_records.items()):
        hull_id = _intish(raw.get("hullid"))
        mission = _intish(raw.get("mission"))
        target_id = _intish(raw.get("mission1target"))
        ident = _identity(owner_id, raw)
        if hull_id not in mite_hulls or mission != 7 or target_id is None or target_id <= 0 or ident is None:
            continue
        tracking_turns[(ship_id, ident, target_id)].append(turn)

    by_ship: dict[int, list[MiteFallbackRun]] = defaultdict(list)
    for (ship_id, ident, target_id), turns in sorted(tracking_turns.items()):
        chunks: list[list[int]] = []
        current = [turns[0]]
        for turn in turns[1:]:
            if turn == current[-1] + 1:
                current.append(turn)
            else:
                chunks.append(current)
                current = [turn]
        chunks.append(current)

        for chunk in chunks:
            start = chunk[0]
            end = chunk[-1]
            mite_end_entry = owner_records.get((end, ship_id))
            mite_clear_entry = owner_records.get((end + 1, ship_id))
            target_anchor_entry = owner_records.get((start - 1, target_id))
            target_start_entry = owner_records.get((start, target_id))
            target_end_entry = owner_records.get((end, target_id))
            target_after_entry = owner_records.get((end + 1, target_id))
            if None in (
                mite_end_entry,
                mite_clear_entry,
                target_anchor_entry,
                target_start_entry,
                target_end_entry,
                target_after_entry,
            ):
                continue

            mite_end_owner, mite_end_raw = mite_end_entry
            mite_clear_owner, mite_clear_raw = mite_clear_entry
            if _identity(mite_end_owner, mite_end_raw) != ident:
                continue
            if _identity(mite_clear_owner, mite_clear_raw) != ident:
                continue
            if _intish(mite_clear_raw.get("mission")) != 0:
                continue
            if _intish(mite_clear_raw.get("mission1target")) not in (None, 0):
                continue

            anchor_owner, anchor_raw = target_anchor_entry
            start_owner, start_raw = target_start_entry
            end_owner, end_raw = target_end_entry
            after_owner, after_raw = target_after_entry
            target_identity = _identity(anchor_owner, anchor_raw)
            if target_identity is None or _identity(start_owner, start_raw) != target_identity:
                continue
            if _identity(end_owner, end_raw) != _identity(after_owner, after_raw):
                continue

            anchor = _xy(anchor_raw)
            if anchor is None:
                continue
            by_ship[ship_id].append(
                MiteFallbackRun(
                    ship_id=ship_id,
                    identity=ident,
                    target_id=target_id,
                    tracking_start=start,
                    tracking_end=end,
                    anchor=anchor,
                )
            )

    return {
        ship_id: tuple(sorted(runs, key=lambda item: (item.tracking_end, item.tracking_start)))
        for ship_id, runs in sorted(by_ship.items())
    }


def classify_scoped_mite_fallback_transition(
    *,
    game_id: int,
    before_turn: int,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any],
    origin: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    runs_by_ship: Mapping[int, tuple[MiteFallbackRun, ...]],
) -> tuple[str | None, bool]:
    """Classify one move as the game-591478 observed fallback-navigation law."""

    periods = _SCOPED_WRAP_PERIODS.get(game_id)
    if periods is None or warp <= 0:
        return None, False
    if _intish(raw.get("mission")) != 0 or _intish(raw.get("mission1target")) not in (None, 0):
        return None, False

    ident = _identity(owner_id, raw)
    if ident is None:
        return None, False

    candidates = [
        run
        for run in runs_by_ship.get(ship_id, ())
        if run.identity == ident and before_turn >= run.tracking_end + 1
    ]
    if not candidates:
        return None, False
    run = max(candidates, key=lambda item: (item.tracking_end, item.tracking_start))

    if not _same_point(_wp(raw), run.anchor, periods=periods):
        return None, False

    remaining = _distance(origin, run.anchor, periods=periods)
    after_remaining = _distance(observed, run.anchor, periods=periods)
    step = _distance(origin, observed, periods=periods)
    if remaining is None or after_remaining is None or step is None:
        return None, False

    expected_step = min(float(warp * warp), remaining)
    progress = remaining - after_remaining
    if progress < -ROUND_TOLERANCE_LY:
        return None, False
    if abs(step - progress) > ROUND_TOLERANCE_LY:
        return None, False
    if abs(step - expected_step) > ROUND_TOLERANCE_LY:
        return None, False

    return "mite_fallback_navigation_g591478", True
