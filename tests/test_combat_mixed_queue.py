from __future__ import annotations

import pytest

from planets_lab.rules.combat.mixed_queue import (
    HostCombatQueuePhase,
    PlanetAttackCandidate,
    host_combat_phase,
    select_initial_plain_planet_attacker,
    ship_planet_sides,
)


def test_host_combat_phase_sequence_is_strict() -> None:
    assert host_combat_phase(
        ship_queue_exhausted=False,
        interphase_repair_mkt_applied=False,
        planet_queue_exhausted=False,
    ) is HostCombatQueuePhase.SHIP
    assert host_combat_phase(
        ship_queue_exhausted=True,
        interphase_repair_mkt_applied=False,
        planet_queue_exhausted=False,
    ) is HostCombatQueuePhase.INTERPHASE_REPAIR_MKT
    assert host_combat_phase(
        ship_queue_exhausted=True,
        interphase_repair_mkt_applied=True,
        planet_queue_exhausted=False,
    ) is HostCombatQueuePhase.PLANET
    assert host_combat_phase(
        ship_queue_exhausted=True,
        interphase_repair_mkt_applied=True,
        planet_queue_exhausted=True,
    ) is HostCombatQueuePhase.COMPLETE


def test_ship_planet_sides_put_ship_left_and_planet_right() -> None:
    assert ship_planet_sides(ship_id=25, planet_id=300) == (25, 300)


def test_planet_selector_uses_standard_priority() -> None:
    selection = select_initial_plain_planet_attacker(
        [
            PlanetAttackCandidate(
                ship_id=30,
                mission=0,
                primary_enemy=7,
                friendly_code="abc",
                engagement_eligible=True,
            ),
            PlanetAttackCandidate(
                ship_id=20,
                mission=3,
                primary_enemy=0,
                friendly_code="100",
                engagement_eligible=True,
            ),
        ]
    )

    assert selection.engagement_available is True
    assert selection.ship_id == 20
    assert selection.priority == (0, 100, 20)


def test_planet_selector_ignores_known_ineligible_candidate() -> None:
    selection = select_initial_plain_planet_attacker(
        [
            PlanetAttackCandidate(
                ship_id=10,
                mission=3,
                primary_enemy=7,
                friendly_code="001",
                engagement_eligible=False,
            ),
            PlanetAttackCandidate(
                ship_id=20,
                mission=0,
                primary_enemy=7,
                friendly_code="abc",
                engagement_eligible=True,
            ),
        ]
    )

    assert selection.engagement_available is True
    assert selection.ship_id == 20
    assert selection.eligible_candidate_count == 1


def test_planet_selector_fails_closed_on_unknown_eligibility() -> None:
    selection = select_initial_plain_planet_attacker(
        [
            PlanetAttackCandidate(
                ship_id=10,
                mission=3,
                primary_enemy=7,
                friendly_code="001",
                engagement_eligible=None,
            ),
            PlanetAttackCandidate(
                ship_id=20,
                mission=0,
                primary_enemy=7,
                friendly_code="abc",
                engagement_eligible=True,
            ),
        ]
    )

    assert selection.engagement_available is None
    assert selection.ship_id is None
    assert "10:planet_engagement_unresolved" in selection.unresolved_reasons


def test_planet_selector_fails_closed_on_post_capture_generated_order() -> None:
    selection = select_initial_plain_planet_attacker(
        [
            PlanetAttackCandidate(
                ship_id=20,
                mission=3,
                primary_enemy=7,
                friendly_code="100",
                engagement_eligible=True,
                post_capture_generated_order=True,
            )
        ]
    )

    assert selection.engagement_available is None
    assert selection.ship_id is None
    assert (
        "20:post_capture_generated_order_unresolved"
        in selection.unresolved_reasons
    )


def test_planet_selector_rejects_duplicate_ship_candidates() -> None:
    selection = select_initial_plain_planet_attacker(
        [
            PlanetAttackCandidate(
                ship_id=20,
                mission=3,
                primary_enemy=7,
                friendly_code="100",
                engagement_eligible=True,
            ),
            PlanetAttackCandidate(
                ship_id=20,
                mission=3,
                primary_enemy=7,
                friendly_code="100",
                engagement_eligible=True,
            ),
        ]
    )

    assert selection.engagement_available is None
    assert "duplicate_ship_candidate:20" in selection.unresolved_reasons


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ship_id": 0, "planet_id": 1},
        {"ship_id": 1, "planet_id": 0},
    ],
)
def test_ship_planet_sides_validate_ids(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        ship_planet_sides(**kwargs)
