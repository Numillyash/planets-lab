from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, hypot, trunc
from typing import Iterable

from planets_lab.rules.movement import max_nominal_distance


ROUNDING_MODES = ("trunc", "floor", "ceil", "nearest")


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

    @property
    def observed_destination(self) -> tuple[int, int]:
        return self.next_x, self.next_y


def _round_coordinate(value: float, mode: str) -> int:
    if mode == "trunc":
        return trunc(value)
    if mode == "floor":
        return floor(value)
    if mode == "ceil":
        return ceil(value)
    if mode == "nearest":
        return floor(value + 0.5)
    raise ValueError(f"unknown rounding mode {mode!r}")


def continuous_partial_destination(sample: MovementSample) -> tuple[float, float]:
    dx = sample.target_x - sample.x
    dy = sample.target_y - sample.y
    distance = hypot(dx, dy)

    if distance == 0:
        return float(sample.x), float(sample.y)

    max_distance = max_nominal_distance(
        sample.warp,
        gravitonic=sample.gravitonic,
    )

    if distance <= max_distance:
        return float(sample.target_x), float(sample.target_y)

    scale = max_distance / distance
    return sample.x + dx * scale, sample.y + dy * scale


def projection_candidates(sample: MovementSample) -> dict[str, tuple[int, int]]:
    raw_x, raw_y = continuous_partial_destination(sample)
    return {
        mode: (
            _round_coordinate(raw_x, mode),
            _round_coordinate(raw_y, mode),
        )
        for mode in ROUNDING_MODES
    }


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
