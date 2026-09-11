from planets_lab.rules.combat.effective_state import privateer_rob_ordinary_cloak_state


def _state(**overrides):
    values = {
        "race_id": 5,
        "mission": 9,
        "hull_can_cloak": True,
        "prior_iscloaked": True,
        "fuel": 6,
        "ordinary_cloak_reference_cost": 5,
        "advanced_cloak": False,
    }
    values.update(overrides)
    return privateer_rob_ordinary_cloak_state(**values)


def test_prior_false_is_not_effectively_cloaked() -> None:
    result = _state(prior_iscloaked=False, fuel=100)
    assert result.effective_cloak is False
    assert result.reason == "prior_false"


def test_ordinary_prior_true_requires_strictly_more_than_reference_cost() -> None:
    assert _state(fuel=6).effective_cloak is True
    assert _state(fuel=5).effective_cloak is False
    assert _state(fuel=4).effective_cloak is False


def test_advanced_cloak_fails_closed() -> None:
    result = _state(advanced_cloak=True)
    assert result.effective_cloak is None
    assert result.reason == "advanced_cloak_unresolved"


def test_out_of_scope_race_or_mission_fails_closed() -> None:
    assert _state(race_id=3).effective_cloak is None
    assert _state(mission=2).effective_cloak is None


def test_unresolved_inputs_fail_closed() -> None:
    assert _state(prior_iscloaked=None).effective_cloak is None
    assert _state(fuel=None).effective_cloak is None
    assert _state(ordinary_cloak_reference_cost=None).effective_cloak is None
    assert _state(advanced_cloak=None).effective_cloak is None
