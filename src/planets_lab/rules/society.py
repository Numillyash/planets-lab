from __future__ import annotations

from math import floor, sin, sqrt, trunc


# Classic Nu native-race IDs. The help documentation gives the standard race
# ordering but does not expose a dedicated API ID table; keep these isolated so
# they can be replaced centrally if differential/static data proves otherwise.
BOVINOID_NATIVE_RACE_ID = 2
AVIAN_NATIVE_RACE_ID = 4
AMORPHOUS_NATIVE_RACE_ID = 5
SILICONOID_NATIVE_RACE_ID = 9


def _nonnegative(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _round_positive(value: float) -> int:
    if value < 0:
        raise ValueError("value must be non-negative")
    return floor(value + 0.5)


def decay_structure_count(*, current: int, supported_maximum: int, decay_rate: int = 3) -> int:
    current = _nonnegative(current, "current structures")
    supported = _nonnegative(supported_maximum, "supported maximum")
    rate = _nonnegative(decay_rate, "decay rate")
    if current <= supported or rate == 0:
        return current
    return max(supported, current - rate)


def native_happiness_after_turn(
    *,
    old_happiness: int,
    native_clans: int,
    tax_rate: int,
    factories: int,
    mines: int,
    government_id: int,
    avian_bonus: int = 0,
    nebula_bonus: int = 0,
) -> int:
    clans = _nonnegative(native_clans, "native clans")
    if not 0 <= tax_rate <= 100:
        raise ValueError("native tax rate must be between 0 and 100")
    factories = _nonnegative(factories, "factories")
    mines = _nonnegative(mines, "mines")
    if not 0 <= government_id <= 8:
        raise ValueError("native government id must be between 0 and 8")

    government_level = government_id + 1
    delta = trunc(
        (
            1000
            - sqrt(clans)
            - tax_rate * 85
            - trunc((factories + mines) / 2)
            - 50 * (10 - government_level)
        )
        / 100
    )
    return min(100, old_happiness + delta + avian_bonus + nebula_bonus)


def native_max_population(*, temperature: int, siliconoid: bool = False) -> int:
    if siliconoid:
        return max(0, temperature * 1000)
    return _round_positive(sin(3.14 * (100 - temperature) / 100) * 150_000)


def native_population_growth(
    *,
    native_clans: int,
    tax_rate: int,
    happiness: int,
    temperature: int,
    colonized: bool,
    siliconoid: bool = False,
) -> int:
    clans = _nonnegative(native_clans, "native clans")
    if not 0 <= tax_rate <= 100:
        raise ValueError("native tax rate must be between 0 and 100")
    if clans == 0 or happiness < 70 or not colonized:
        return 0

    capacity = native_max_population(temperature=temperature, siliconoid=siliconoid)
    if clans >= capacity:
        return 0

    climate_factor = temperature / 100 if siliconoid else sin(3.14 * (100 - temperature) / 100)
    growth = _round_positive(climate_factor * clans / 25 * 5 / (tax_rate + 5))
    if clans > 66_000:
        growth = trunc(growth / 2)
    return growth


def bovinoid_supply_output(*, native_clans: int, colonist_clans: int) -> int:
    natives = _nonnegative(native_clans, "native clans")
    colonists = _nonnegative(colonist_clans, "colonist clans")
    # One supply per 10,000 Bovinoids = per 100 native clans; collection is
    # limited to one supply per colonist clan.
    return min(natives // 100, colonists)


def amorphous_clans_eaten(*, colonist_clans: int, native_happiness: int) -> int:
    colonists = _nonnegative(colonist_clans, "colonist clans")
    if colonists == 0:
        return 0
    eaten = 5 + max(0, 90 - native_happiness)
    return min(colonists, eaten)


def civil_war_population_after(*, clans: int) -> int:
    clans = _nonnegative(clans, "clans")
    if clans == 0:
        return 0
    killed = trunc(clans * 0.30) + 100
    return max(0, clans - killed)
