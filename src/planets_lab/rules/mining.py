from __future__ import annotations

from math import ceil, floor


FEDERATION_RACE_ID = 1
LIZARD_RACE_ID = 2
DEFAULT_MINING_RATE_PERCENT = 100
FEDERATION_MINING_RATE_PERCENT = 70
LIZARD_MINING_RATE_PERCENT = 200
DEFAULT_TRANS_URANIUM_RATE = 5


def _nonnegative(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _percent(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def mining_rate_for_race(race_id: int | None) -> int:
    if race_id == FEDERATION_RACE_ID:
        return FEDERATION_MINING_RATE_PERCENT
    if race_id == LIZARD_RACE_ID:
        return LIZARD_MINING_RATE_PERCENT
    return DEFAULT_MINING_RATE_PERCENT


def _nearest_positive(value: float) -> int:
    if value < 0:
        raise ValueError("value must be non-negative")
    return floor(value + 0.5)


def mined_amount(
    *,
    mines: int,
    density: int,
    ground_amount: int,
    mining_rate_percent: int = DEFAULT_MINING_RATE_PERCENT,
    output_modifier_percent: int = 100,
) -> int:
    """Return KT extracted from one mineral deposit this turn.

    Planets.nu documents mines * density with racial/output modifiers, but the
    ordinary-host integer projection is not specified. Nearest-integer
    projection is therefore an explicit INFERRED working rule until NuHost
    differential data resolves the rounding boundary.
    """

    mine_count = _nonnegative(mines, "mines")
    density_percent = _percent(density, "density")
    available = _nonnegative(ground_amount, "ground amount")
    rate = _percent(mining_rate_percent, "mining rate")
    modifier = _percent(output_modifier_percent, "output modifier")

    raw = mine_count * density_percent * rate * modifier / 1_000_000
    return min(available, _nearest_positive(raw))


def trans_uranium_mutation_amount(
    *,
    density: int,
    mutation_rate: int = DEFAULT_TRANS_URANIUM_RATE,
) -> int:
    """Return KT added to one ground deposit by trans-uranium mutation.

    For the documented default mutation rate of 5 this exactly reproduces the
    published 10-20 -> 1, 21-40 -> 2, ..., 81-100 -> 5 density table. The same
    ceiling expression is exposed for custom host rates as the natural
    generalization of the documented rate*density rule.
    """

    density_percent = _percent(density, "density")
    rate = _nonnegative(mutation_rate, "mutation rate")
    if density_percent == 0 or rate == 0:
        return 0
    return ceil(rate * density_percent / 100)
