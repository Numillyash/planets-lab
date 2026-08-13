from planets_lab.validation import MovementSample, candidate_scores, projection_candidates


def test_cardinal_partial_move_has_unanimous_candidate() -> None:
    sample = MovementSample(
        turn=10,
        ship_id=1,
        x=100,
        y=100,
        target_x=300,
        target_y=100,
        warp=9,
        next_x=181,
        next_y=100,
    )

    candidates = projection_candidates(sample)

    assert set(candidates.values()) == {(181, 100)}


def test_diagonal_partial_move_exposes_rounding_candidates() -> None:
    sample = MovementSample(
        turn=10,
        ship_id=1,
        x=100,
        y=100,
        target_x=300,
        target_y=300,
        warp=9,
        next_x=157,
        next_y=157,
    )

    candidates = projection_candidates(sample)

    assert candidates["trunc"] == (157, 157)
    assert candidates["floor"] == (157, 157)
    assert candidates["ceil"] == (158, 158)
    assert candidates["nearest"] == (157, 157)


def test_candidate_scores_count_matches_without_declaring_a_rule() -> None:
    samples = [
        MovementSample(
            turn=10,
            ship_id=1,
            x=100,
            y=100,
            target_x=300,
            target_y=100,
            warp=9,
            next_x=181,
            next_y=100,
        ),
        MovementSample(
            turn=11,
            ship_id=2,
            x=100,
            y=100,
            target_x=300,
            target_y=300,
            warp=9,
            next_x=158,
            next_y=158,
        ),
    ]

    scores = candidate_scores(samples)

    assert scores["ceil"] == (2, 2)
    assert scores["trunc"] == (1, 2)
