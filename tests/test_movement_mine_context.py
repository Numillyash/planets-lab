from planets_lab.corpus.movement_mine_context import (
    NORMAL_MINE_CATEGORY,
    WEB_MINE_CATEGORY,
    classify_mine_evidence_values,
    nearest_damage_quantum,
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
