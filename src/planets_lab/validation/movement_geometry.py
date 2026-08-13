from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, hypot, trunc
from typing import Iterable

from planets_lab.rules.movement import max_nominal_distance


ROUNDING_MODES = ("trunc", "floor", "ceil", "nearest", "host_major_minor")


@dataclass(frozen=True, slots=True)
class MovementSample:
    turn: int
    ship_id: int
    x: int
    y: int
    target_x: int
    target_y: int
    warp: int
    next_x: int
    next_y: int
    gravitonic: bool = False

    # Optional provenance / rule-classification metadata. These fields are not
    # used by the projection candidates themselves; they let the differential
    # CLI split real observations by context instead of silently mixing normal
    # movement with tow/intercept/damage/special cases.
    game_id: int | str | None = None
    player_slot_id: int | None = None
    hull_id: int | None = None
    mission: int | None = None
    damage: int | None = None
    friendly_code: str = ""

    @property
    def observed_destination(self) -> tuple[int, int]:
        return self.next_x, self.next_y

    @property
    def observed_distance(self) -> float:
        return hypot(self.next_x - self.x, self.next_y - self.y)

    @property
    def nominal_max_distance(self) -> int:
        return max_nominal_distance(
            self.warp,
            gravitonic=self.gravitonic,
        )


def _round_coordinate(value: float, mode: str) -> int:
    if mode == "trunc":
        return trunc(value)
    if mode == "floor":
        return floor(value)
    if mode == "ceil":
        return ceil(value)
    if mode == "nearest":
        # Coordinates in the standard map are positive. Keep the original
        # half-up diagnostic candidate explicit rather than relying on Python's
        # bankers-rounding semantics.
        return floor(value + 0.5)
    raise ValueError(f"unknown rounding mode {mode!r}")


def continuous_partial_destination(sample: MovementSample) -> tuple[float, float]:
    dx = sample.target_x - sample.x
    dy = sample.target_y - sample.y
    distance = hypot(dx, dy)

    if distance == 0:
        return float(sample.x), float(sample.y)

    max_distance = sample.nominal_max_distance

    if distance <= max_distance:
        return float(sample.target_x), float(sample.target_y)

    scale = max_distance / distance
    return sample.x + dx * scale, sample.y + dy * scale


def host_major_minor_destination(sample: MovementSample) -> tuple[int, int]:
    """Return the Host-style integer partial-movement destination.

    Differential samples from NuHost show the classic HOST behavior: round the
    movement on the major axis first, then derive the minor-axis movement from
    that integer major-axis result.
    """

    dx = sample.target_x - sample.x
    dy = sample.target_y - sample.y
    waypoint_distance = hypot(dx, dy)
    max_distance = sample.nominal_max_distance

    if waypoint_distance == 0:
        return sample.x, sample.y
    if waypoint_distance <= max_distance:
        return sample.target_x, sample.target_y

    abs_dx = abs(dx)
    abs_dy = abs(dy)

    if abs_dx >= abs_dy:
        major = abs_dx
        minor = abs_dy
        major_move = floor(max_distance * major / waypoint_distance + 0.5)
        minor_move = floor(major_move * minor / major + 0.5) if major else 0
        move_x = major_move if dx >= 0 else -major_move
        move_y = minor_move if dy >= 0 else -minor_move
    else:
        major = abs_dy
        minor = abs_dx
        major_move = floor(max_distance * major / waypoint_distance + 0.5)
        minor_move = floor(major_move * minor / major + 0.5) if major else 0
        move_y = major_move if dy >= 0 else -major_move
        move_x = minor_move if dx >= 0 else -minor_move

    return sample.x + move_x, sample.y + move_y


def projection_candidates(sample: MovementSample) -> dict[str, tuple[int, int]]:
    raw_x, raw_y = continuous_partial_destination(sample)
    candidates = {
        mode: (
            _round_coordinate(raw_x, mode),
            _round_coordinate(raw_y, mode),
        )
        for mode in ("trunc", "floor", "ceil", "nearest")
    }
    candidates["host_major_minor"] = host_major_minor_destination(sample)
    return candidates


def candidate_scores(samples: Iterable[MovementSample]) -> dict[str, tuple[int, int]]:
    scores = {mode: [0, 0] for mode in ROUNDING_MODES}

    for sample in samples:
        observed = sample.observed_destination
        candidates = projection_candidates(sample)

        for mode, candidate in candidates.items():
            scores[mode][1] += 1
            if candidate == observed:
                scores[mode][0] += 1

    return {
        mode: (values[0], values[1])
        for mode, values in scores.items()
    }


def group_candidate_scores(
    samples: Iterable[MovementSample],
    *,
    attribute: str,
) -> dict[object, dict[str, tuple[int, int]]]:
    """Score rounding candidates independently for one metadata attribute."""

    groups: dict[object, list[MovementSample]] = {}

    for sample in samples:
        key = getattr(sample, attribute)
        groups.setdefault(key, []).append(sample)

    return {
        key: candidate_scores(group)
        for key, group in groups.items()
    }
