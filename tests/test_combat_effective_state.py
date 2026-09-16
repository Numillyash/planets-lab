from planets_lab.rules.combat.effective_state import (
    EffectiveCloakState,
    bird_super_spy_ordinary_cloak_state,
    privateer_rob_ordinary_cloak_state,
    standard_targetability_from_effective_cloak,
)


def _privateer_state(**overrides):
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


def _bird_state(**overrides):
    values = {
        "race_id": 3,
        "mission": 9,
        "hull_can_cloak": True,
        "advanced_cloak": False,
        "damage": 0,
        "fuel_before": 37,
        "ordinary_cloak_reference_cost": 5,
        "reference_move_resolved": True,
        "reference_remaining_fuel": 29,
        "prior_iscloaked": True,
        "ion_start_inside": False,
        "planet_ion_pulse_possible": False,
        "loki_start_exposed": False,
        "active_glory_colocated": False,
    }
    values.update(overrides)
    return bird_super_spy_ordinary_cloak_state(**values)


def test_privateer_prior_false_is_not_effectively_cloaked() -> None:
    result = _privateer_state(prior_iscloaked=False, fuel=100)
    assert result.effective_cloak is False
    assert result.reason == "prior_false"


def test_privateer_ordinary_prior_true_requires_strictly_more_than_reference_cost() -> None:
    assert _privateer_state(fuel=6).effective_cloak is True
    assert _privateer_state(fuel=5).effective_cloak is False
    assert _privateer_state(fuel=4).effective_cloak is False


def test_privateer_advanced_cloak_fails_closed() -> None:
    result = _privateer_state(advanced_cloak=True)
    assert result.effective_cloak is None
    assert result.reason == "advanced_cloak_unresolved"


def test_privateer_out_of_scope_race_or_mission_fails_closed() -> None:
    assert _privateer_state(race_id=3).effective_cloak is None
    assert _privateer_state(mission=2).effective_cloak is None


def test_privateer_unresolved_inputs_fail_closed() -> None:
    assert _privateer_state(prior_iscloaked=None).effective_cloak is None
    assert _privateer_state(fuel=None).effective_cloak is None
    assert _privateer_state(ordinary_cloak_reference_cost=None).effective_cloak is None
    assert _privateer_state(advanced_cloak=None).effective_cloak is None


def test_bird_super_spy_positive_candidate() -> None:
    result = _bird_state()
    assert result.effective_cloak is True
    assert result.reason == "documented_super_spy_ordinary_cloak_supported"


def test_bird_damage_and_low_fuel_are_known_not_effectively_cloaked() -> None:
    damaged = _bird_state(damage=1)
    assert damaged.effective_cloak is False
    assert damaged.reason == "damage_blocks_cloak"

    low_fuel = _bird_state(fuel_before=5)
    assert low_fuel.effective_cloak is False
    assert low_fuel.reason == "fuel_not_safely_above_reference_cost"


def test_bird_visible_or_unresolved_decloak_context_fails_closed() -> None:
    assert _bird_state(loki_start_exposed=True).effective_cloak is None
    assert _bird_state(ion_start_inside=True).effective_cloak is None
    assert _bird_state(planet_ion_pulse_possible=True).effective_cloak is None
    assert _bird_state(planet_ion_pulse_possible=None).effective_cloak is None
    assert _bird_state(active_glory_colocated=True).effective_cloak is None


def test_bird_non_super_spy_and_advanced_cloak_remain_unresolved() -> None:
    assert _bird_state(mission=2).effective_cloak is None
    advanced = _bird_state(advanced_cloak=True)
    assert advanced.effective_cloak is None
    assert advanced.reason == "advanced_cloak_unresolved"


def test_bird_requires_positive_prior_cloak_and_resolved_post_move_fuel_margin() -> None:
    assert _bird_state(prior_iscloaked=False).effective_cloak is None
    assert _bird_state(reference_move_resolved=False).effective_cloak is None
    assert _bird_state(reference_remaining_fuel=5).effective_cloak is None


def test_effective_cloak_projects_directional_standard_targetability() -> None:
    blocked = standard_targetability_from_effective_cloak(
        EffectiveCloakState(True, "supported_cloak")
    )
    assert blocked.targetable_by_opponent is False

    eligible = standard_targetability_from_effective_cloak(
        EffectiveCloakState(False, "known_uncloaked")
    )
    assert eligible.targetable_by_opponent is True

    unresolved = standard_targetability_from_effective_cloak(
        EffectiveCloakState(None, "dynamic_state_unknown")
    )
    assert unresolved.targetable_by_opponent is None
