from planets_lab.rules.population import cyborg_assimilation


def test_cyborg_population_conversion_rate() -> None:
    assert cyborg_assimilation(
        colonist_clans=500,
        native_clans=1_000,
        native_race_id=1,
    ) == 500


def test_native_race_five_is_not_converted() -> None:
    assert cyborg_assimilation(
        colonist_clans=500,
        native_clans=1_000,
        native_race_id=5,
    ) == 0
