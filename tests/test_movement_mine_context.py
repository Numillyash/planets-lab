from types import SimpleNamespace

from planets_lab.corpus.movement_mine_context import (
    NORMAL_MINE_CATEGORY,
    NORMAL_MINE_SCALED_FLOOR_CATEGORY,
    WEB_MINE_CATEGORY,
    _classify_scaled_floor_normal_mine,
    _exact_supply_repair_hit_count,
    classify_mine_evidence_values,
    nearest_damage_quantum,
    scaled_floor_normal_mine_endpoint,
)


def test_nearest_damage_quantum_matches_observed_nuhost_rounding() -> None:
    assert nearest_damage_quantum(120, web=True) == 8
    assert nearest_damage_quantum(250, web=True) == 4
    assert nearest_damage_quantum(180, web=False) == 55
    assert nearest_damage_quantum(120, web=False) == 83


def test_web_requires_reset_field_and_nearest_damage_multiple() -> None:
    evidence = classify_mine_evidence_values(
        hull_mass=120,
        hull_tech=6,
        damage_delta=8,
        lost_distance=8.061,
        post_reset=True,
        web_at_observed=True,
        normal_field_crossing=False,
    )
    assert evidence is not None
    assert evidence.category == WEB_MINE_CATEGORY
    assert evidence.damage_hits == 1
    assert evidence.slowdown_hits is None

    assert classify_mine_evidence_values(
        hull_mass=120,
        hull_tech=6,
        damage_delta=9,
        lost_distance=8.061,
        post_reset=True,
        web_at_observed=True,
        normal_field_crossing=False,
    ) is None
    assert classify_mine_evidence_values(
        hull_mass=120,
        hull_tech=6,
        damage_delta=8,
        lost_distance=8.061,
        post_reset=True,
        web_at_observed=False,
        normal_field_crossing=False,
    ) is None


def test_normal_mine_uses_nearest_damage_and_10ly_geometry() -> None:
    evidence = classify_mine_evidence_values(
        hull_mass=180,
        hull_tech=6,
        damage_delta=55,
        lost_distance=10.436,
        post_reset=False,
        web_at_observed=False,
        normal_field_crossing=True,
    )
    assert evidence is not None
    assert evidence.category == NORMAL_MINE_CATEGORY
    assert evidence.damage_hits == 1
    assert evidence.slowdown_hits == 1

    assert classify_mine_evidence_values(
        hull_mass=180,
        hull_tech=6,
        damage_delta=56,
        lost_distance=10.436,
        post_reset=False,
        web_at_observed=False,
        normal_field_crossing=True,
    ) is None


def test_normal_damage_hit_multiplicity_is_not_forced_to_slowdown_count() -> None:
    evidence = classify_mine_evidence_values(
        hull_mass=160,
        hull_tech=4,
        damage_delta=124,
        lost_distance=11.107,
        post_reset=False,
        web_at_observed=False,
        normal_field_crossing=True,
    )
    assert evidence is not None
    assert evidence.category == NORMAL_MINE_CATEGORY
    assert evidence.damage_hits == 2
    assert evidence.slowdown_hits == 1


def test_normal_mine_fails_closed_without_visible_after_field() -> None:
    assert classify_mine_evidence_values(
        hull_mass=115,
        hull_tech=4,
        damage_delta=86,
        lost_distance=10.439,
        post_reset=False,
        web_at_observed=False,
        normal_field_crossing=False,
    ) is None


def test_scaled_floor_endpoint_matches_short_waypoint_reference() -> None:
    endpoint, penalty = scaled_floor_normal_mine_endpoint(
        origin=(2560, 1801),
        target=(2523, 1778),
        nominal_distance=81.0,
        regular_distance=43.566042,
        slowdown_hits=1,
    )
    assert penalty == 18
    assert endpoint == (2541, 1789)


def test_scaled_floor_endpoint_reduces_to_ten_clicks_at_full_range() -> None:
    endpoint, penalty = scaled_floor_normal_mine_endpoint(
        origin=(0, 0),
        target=(81, 0),
        nominal_distance=81.0,
        regular_distance=81.0,
        slowdown_hits=1,
    )
    assert penalty == 10
    assert endpoint == (71, 0)


def test_exact_supply_repair_trace_recovers_target_hit_count() -> None:
    assert _exact_supply_repair_hit_count(
        before_damage=0,
        after_damage=66,
        before_supplies=53,
        after_supplies=3,
        quantum=76,
    ) == 1

    assert _exact_supply_repair_hit_count(
        before_damage=0,
        after_damage=66,
        before_supplies=53,
        after_supplies=4,
        quantum=76,
    ) is None


def test_scaled_floor_classifier_closes_exact_planar_repair_trace() -> None:
    context = SimpleNamespace(topology=SimpleNamespace(sphere=False))
    evidence = _classify_scaled_floor_normal_mine(
        context=context,
        hull_mass=130,
        hull_tech=6,
        before_raw={"damage": 0, "supplies": 53},
        after_raw={"damage": 66, "supplies": 3},
        origin=(2560, 1801),
        target=(2523, 1778),
        observed=(2541, 1789),
        nominal_distance=81.0,
        regular_distance=43.566042,
        normal_field_crossing=True,
    )
    assert evidence is not None
    assert evidence.category == NORMAL_MINE_SCALED_FLOOR_CATEGORY
    assert evidence.damage_hits == 1
    assert evidence.slowdown_hits == 1


def test_scaled_floor_classifier_fails_closed_for_sphere_or_missing_field() -> None:
    kwargs = {
        "hull_mass": 130,
        "hull_tech": 6,
        "before_raw": {"damage": 0, "supplies": 53},
        "after_raw": {"damage": 66, "supplies": 3},
        "origin": (2560, 1801),
        "target": (2523, 1778),
        "observed": (2541, 1789),
        "nominal_distance": 81.0,
        "regular_distance": 43.566042,
    }
    assert _classify_scaled_floor_normal_mine(
        context=SimpleNamespace(topology=SimpleNamespace(sphere=True)),
        normal_field_crossing=True,
        **kwargs,
    ) is None
    assert _classify_scaled_floor_normal_mine(
        context=SimpleNamespace(topology=SimpleNamespace(sphere=False)),
        normal_field_crossing=False,
        **kwargs,
    ) is None
