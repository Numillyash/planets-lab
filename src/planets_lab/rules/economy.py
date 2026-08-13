from __future__ import annotations

from math import sqrt, trunc


MAX_PLANET_TAX_INCOME = 5_000


def _nonnegative(value: int, label: str) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _tax_rate(value: int) -> int:
    if not 0 <= value <= 100:
        raise ValueError("tax rate must be between 0 and 100")
    return value


def max_mines(colonist_clans: int) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    if clans <= 200:
        return clans
    return trunc(200 + sqrt(clans - 200))


def max_factories(colonist_clans: int) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    if clans <= 100:
        return clans
    return trunc(100 + sqrt(clans - 100))


def max_defense_posts(colonist_clans: int) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    if clans <= 50:
        return clans
    return trunc(50 + sqrt(clans - 50))


def factory_supply_output(factories: int) -> int:
    return _nonnegative(factories, "factories")


def native_government_tax_efficiency(government_id: int) -> float:
    """Return the documented 20%..180% government tax-efficiency multiplier."""
    if not 0 <= government_id <= 8:
        raise ValueError("native government id must be between 0 and 8")
    return (government_id + 1) * 0.20


def colonist_tax_income(*, colonist_clans: int, tax_rate: int, happiness: int, racial_tax_modifier: float = 1.0, max_income: int = MAX_PLANET_TAX_INCOME) -> int:
    clans = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    if racial_tax_modifier < 0:
        raise ValueError("racial tax modifier must be non-negative")
    if max_income < 0:
        raise ValueError("max income must be non-negative")
    if happiness <= 30 or clans == 0 or rate == 0:
        return 0
    income = trunc(clans * rate * racial_tax_modifier / 10)
    return min(max_income, income)


def native_tax_income(*, native_clans: int, tax_rate: int, happiness: int, government_id: int, colonist_clans: int, racial_tax_modifier: float = 1.0, income_per_colonist_cap: int = 1, taxable: bool = True, effective_tax_rate_cap: int | None = None, max_income: int = MAX_PLANET_TAX_INCOME) -> int:
    natives = _nonnegative(native_clans, "native clans")
    colonists = _nonnegative(colonist_clans, "colonist clans")
    rate = _tax_rate(tax_rate)
    if effective_tax_rate_cap is not None:
        rate = min(rate, _tax_rate(effective_tax_rate_cap))
    if racial_tax_modifier < 0:
        raise ValueError("racial tax modifier must be non-negative")
    if income_per_colonist_cap < 0:
        raise ValueError("income-per-colonist cap must be non-negative")
    if max_income < 0:
        raise ValueError("max income must be non-negative")
    if not taxable or happiness <= 30 or natives == 0 or colonists == 0 or rate == 0:
        return 0
    efficiency = native_government_tax_efficiency(government_id)
    raw_income = trunc(natives * rate * efficiency * racial_tax_modifier / 10)
    collector_cap = colonists * income_per_colonist_cap
    return min(max_income, collector_cap, raw_income)


def combined_planet_tax_income(colonist_income: int, native_income: int, *, max_income: int = MAX_PLANET_TAX_INCOME) -> int:
    colonist = _nonnegative(colonist_income, "colonist income")
    native = _nonnegative(native_income, "native income")
    maximum = _nonnegative(max_income, "max income")
    return min(maximum, colonist + native)
