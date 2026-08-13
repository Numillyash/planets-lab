from __future__ import annotations

from math import ceil, floor, sin, sqrt, trunc


def _nonnegative(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _tax_rate(value: int) -> int:
    if not 0 <= value <= 100:
        raise ValueError("tax rate must be between 0 and 100")
    return value


def _round_positive(value: float) -> int:
    if value < 0:
        raise ValueError("value must be non-negative")
    return floor(value + 0.5)


def colonist_happiness_after_turn(
    *,
    old_happiness: int,
    colonist_clans: int,
    tax_rate: int,
    temperature: int,
    factories: int,
    mines: int,
    base_temperature: int = 50,
) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    factories = _nonnegative(factories, "factories")
    mines = _nonnegative(mines, "mines")
    delta = trunc(
        (
            1000
            - sqrt(clans)
            - 80 * rate
            - abs(base_temperature - temperature) * 3
            - (factories + mines) / 3
        )
        / 100
    )
    return min(100, old_happiness + delta)


def ordinary_colonist_max_population(temperature: int) -> int:
    if temperature > 84:
        return max(0, trunc((20099.9 - 200 * temperature) / 10))
    if temperature < 15:
        return max(0, trunc((299.9 + 200 * temperature) / 10))
    return _round_positive(sin(3.14 * (100 - temperature) / 100) * 100_000)


def ordinary_colonist_growth(
    *,
    colonist_clans: int,
    tax_rate: int,
    happiness: int,
    temperature: int,
) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    if clans == 0 or happiness < 70:
        return 0
    capacity = ordinary_colonist_max_population(temperature)
    if clans >= capacity or not 15 <= temperature <= 84:
        return 0
    growth = _round_positive(
        sin(3.14 * (100 - temperature) / 100)
        * clans
        / 20
        * 5
        / (rate + 5)
    )
    if clans > 66_000:
        growth = trunc(growth / 2)
    return growth


def overpopulation_loss(
    *,
    colonist_clans: int,
    maximum_population: int,
    supplies: int,
    climate_death_rate_percent: int = 10,
) -> tuple[int, int]:
    clans = _nonnegative(colonist_clans, "colonist clans")
    maximum = _nonnegative(maximum_population, "maximum population")
    available_supplies = _nonnegative(supplies, "supplies")
    if not 0 <= climate_death_rate_percent <= 100:
        raise ValueError("climate death rate must be between 0 and 100")

    excess = max(0, clans - maximum)
    if excess == 0:
        return 0, 0

    supported_by_supplies = _round_positive(available_supplies / 4)
    unsupported = max(0, excess - supported_by_supplies)
    if unsupported == 0:
        return 0, 0

    killed = ceil(unsupported * climate_death_rate_percent / 100)
    supplies_consumed = min(available_supplies, 1 + trunc(excess / 400))
    return killed, supplies_consumed
