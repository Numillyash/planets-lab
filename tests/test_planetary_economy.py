from planets_lab.rules.economy import (
    MAX_PLANET_TAX_INCOME,
    colonist_tax_income,
    combined_planet_tax_income,
    factory_supply_output,
    max_defense_posts,
    max_factories,
    max_mines,
    native_government_tax_efficiency,
    native_tax_income,
)


def test_structure_caps_follow_documented_population_formulae() -> None:
    assert max_mines(200) == 200
    assert max_mines(300) == 210
    assert max_factories(100) == 100
    assert max_factories(200) == 110
    assert max_defense_posts(50) == 50
    assert max_defense_posts(150) == 60


def test_factories_produce_one_supply_each() -> None:
    assert factory_supply_output(137) == 137


def test_native_government_efficiency_runs_from_anarchy_to_unity() -> None:
    assert native_government_tax_efficiency(0) == 0.20
    assert native_government_tax_efficiency(4) == 1.00
    assert native_government_tax_efficiency(8) == 1.80


def test_colonist_taxes_honor_happiness_and_racial_modifier() -> None:
    assert colonist_tax_income(colonist_clans=100, tax_rate=10, happiness=100) == 100
    assert colonist_tax_income(colonist_clans=100, tax_rate=10, happiness=100, racial_tax_modifier=2.0) == 200
    assert colonist_tax_income(colonist_clans=100, tax_rate=10, happiness=30) == 0


def test_native_taxes_are_limited_by_colonist_collectors() -> None:
    ordinary = native_tax_income(native_clans=10_000, tax_rate=10, happiness=100, government_id=4, colonist_clans=500)
    insectoid = native_tax_income(native_clans=10_000, tax_rate=10, happiness=100, government_id=4, colonist_clans=500, income_per_colonist_cap=2)
    assert ordinary == 500
    assert insectoid == 1_000


def test_native_tax_can_be_disabled_or_rate_capped() -> None:
    assert native_tax_income(native_clans=10_000, tax_rate=50, happiness=100, government_id=4, colonist_clans=5_000, taxable=False) == 0
    assert native_tax_income(native_clans=10_000, tax_rate=50, happiness=100, government_id=4, colonist_clans=5_000, effective_tax_rate_cap=20) == 2_000


def test_combined_tax_income_has_planet_cap() -> None:
    assert combined_planet_tax_income(4_000, 4_000) == MAX_PLANET_TAX_INCOME
