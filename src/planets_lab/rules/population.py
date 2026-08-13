from __future__ import annotations

from math import ceil, floor, sin, sqrt, trunc


CRYSTAL_RACE_ID = 7
CYBORG_RACE_ID = 6
FURY_RACE_ID = 4
ROBOT_RACE_ID = 9
REBEL_RACE_ID = 10
COLONIES_RACE_ID = 11
AMORPHOUS_NATIVE_RACE_ID = 5


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


def colonist_base_temperature(race_id: int) -> int:
    return 100 if race_id == CRYSTAL_RACE_ID else 50


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


def colonist_max_population_for_race(
    race_id: int,
    temperature: int,
    *,
    crystal_desert_advantage: bool = True,
) -> int:
    if race_id == CRYSTAL_RACE_ID and crystal_desert_advantage:
        return max(0, temperature * 1_000)

    ordinary = ordinary_colonist_max_population(temperature)

    if race_id == REBEL_RACE_ID and temperature < 20:
        return 90_000

    if race_id in {FURY_RACE_ID, ROBOT_RACE_ID, REBEL_RACE_ID, COLONIES_RACE_ID}:
        if temperature > 84:
            return max(60, ordinary)

    return ordinary


def ordinary_colonist_growth(
    *,
    colonist_clans: int,
    tax_rate: int,
    happiness: int,
    temperature: int,
    maximum_population: int | None = None,
) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    if clans == 0 or happiness < 70:
        return 0
    capacity = (
        ordinary_colonist_max_population(temperature)
        if maximum_population is None
        else _nonnegative(maximum_population, "maximum population")
    )
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


def crystal_colonist_growth(
    *,
    colonist_clans: int,
    tax_rate: int,
    happiness: int,
    temperature: int,
    improved_desert_habitation: bool = False,
) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    if clans == 0 or happiness < 70 or temperature <= 0:
        return 0

    capacity = max(0, temperature * 1_000)
    if clans >= capacity:
        return 0

    if improved_desert_habitation:
        climate_factor = temperature * temperature / 4_000
    else:
        climate_factor = temperature / 100

    # The official Crystal formula does not state the integer projection.
    # Nearest-integer projection is retained as the explicit working rule,
    # matching the ROUND convention used by the adjacent population formulae.
    growth = _round_positive(climate_factor * clans / 20 * 5 / (rate + 5))
    if clans > 66_000:
        growth = trunc(growth / 2)
    return growth


def colonist_growth_for_race(
    *,
    race_id: int,
    colonist_clans: int,
    tax_rate: int,
    happiness: int,
    temperature: int,
    crystal_desert_advantage: bool = True,
    improved_desert_habitation: bool = False,
) -> int:
    if race_id == CRYSTAL_RACE_ID and crystal_desert_advantage:
        return crystal_colonist_growth(
            colonist_clans=colonist_clans,
            tax_rate=tax_rate,
            happiness=happiness,
            temperature=temperature,
            improved_desert_habitation=improved_desert_habitation,
        )

    maximum = colonist_max_population_for_race(
        race_id,
        temperature,
        crystal_desert_advantage=crystal_desert_advantage,
    )
    return ordinary_colonist_growth(
        colonist_clans=colonist_clans,
        tax_rate=tax_rate,
        happiness=happiness,
        temperature=temperature,
        maximum_population=maximum,
    )


def cyborg_assimilation(
    *,
    colonist_clans: int,
    native_clans: int,
    native_race_id: int,
    assimilation_rate_percent: int = 100,
) -> int:
    colonists = _nonnegative(colonist_clans, "colonist clans")
    natives = _nonnegative(native_clans, "native clans")
    if assimilation_rate_percent < 0:
        raise ValueError("assimilation rate must be non-negative")
    if native_race_id == AMORPHOUS_NATIVE_RACE_ID or colonists == 0 or natives == 0:
        return 0
    capacity = trunc(colonists * assimilation_rate_percent / 100)
    return min(natives, capacity)


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
