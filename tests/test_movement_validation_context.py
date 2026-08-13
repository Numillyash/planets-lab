from planets_lab.validation.movement_geometry import (
    MovementSample,
    group_candidate_scores,
)


def test_context_metadata_does_not_change_projection_scoring() -> None:
    samples = [
        MovementSample(
            game_id=100,
            player_slot_id=3,
            turn=10,
            ship_id=1,
            hull_id=16,
            mission=0,
            damage=0,
            x=100,
            y=100,
            target_x=300,
            target_y=100,
            warp=9,
            next_x=181,
            next_y=100,
        ),
        MovementSample(
            game_id=100,
            player_slot_id=3,
            turn=11,
            ship_id=2,
            hull_id=17,
            mission=7,
            damage=0,
            x=100,
            y=100,
            target_x=300,
            target_y=300,
            warp=9,
            next_x=158,
            next_y=158,
        ),
    ]

    by_mission = group_candidate_scores(samples, attribute="mission")

    assert by_mission[0]["trunc"] == (1, 1)
    assert by_mission[7]["ceil"] == (1, 1)


def test_observed_distance_and_nominal_distance_are_exposed() -> None:
    sample = MovementSample(
        turn=3,
        ship_id=3,
        x=1836,
        y=2187,
        target_x=1851,
        target_y=2299,
        warp=9,
        next_x=1847,
        next_y=2267,
    )

    assert sample.nominal_max_distance == 81
    assert 80.7 < sample.observed_distance < 80.8
