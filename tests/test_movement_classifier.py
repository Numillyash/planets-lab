from planets_lab.core import GameState, Player, Ship
from planets_lab.sim import MovementMissionConvention, classify_movement_intents


def _state(*ships: Ship) -> GameState:
    return GameState(
        game_id="classifier",
        turn=1,
        players={1: Player(id=1)},
        ships={ship.id: ship for ship in ships},
    )


def _ship(
    ship_id: int,
    *,
    mission: str | None = None,
    friendly_code: str = "",
) -> Ship:
    return Ship(
        id=ship_id,
        owner_id=1,
        hull_id=16,
        x=100,
        y=100,
        mission=mission,
        friendly_code=friendly_code,
    )


def test_partitions_standard_tow_move_most_and_intercept_intents() -> None:
    result = classify_movement_intents(
        _state(
            _ship(1, mission="6"),
            _ship(2, mission="4"),
            _ship(3, mission="7"),
            _ship(4, mission=None),
        )
    )

    assert result.tow_attempt_ship_ids == frozenset({1})
    assert result.move_most_candidate_ship_ids == frozenset({2, 4})
    assert result.intercept_ship_ids == frozenset({3})
    assert result.special_move_most_ship_ids == frozenset()
    assert result.all_ship_ids == frozenset({1, 2, 3, 4})


def test_hyp_is_isolated_from_ordinary_move_most() -> None:
    result = classify_movement_intents(
        _state(
            _ship(1, mission="4", friendly_code="HYP"),
            _ship(2, mission="4", friendly_code=" hyp "),
        )
    )

    assert result.move_most_candidate_ship_ids == frozenset()
    assert result.special_move_most_ship_ids == frozenset({1, 2})


def test_tow_and_intercept_missions_take_precedence_over_hyp_code() -> None:
    result = classify_movement_intents(
        _state(
            _ship(1, mission="6", friendly_code="HYP"),
            _ship(2, mission="7", friendly_code="HYP"),
        )
    )

    assert result.tow_attempt_ship_ids == frozenset({1})
    assert result.intercept_ship_ids == frozenset({2})
    assert result.special_move_most_ship_ids == frozenset()


def test_unknown_or_text_mission_remains_move_most_candidate() -> None:
    result = classify_movement_intents(
        _state(
            _ship(1, mission="99"),
            _ship(2, mission="Explore"),
        )
    )

    assert result.move_most_candidate_ship_ids == frozenset({1, 2})


def test_mission_numbering_is_injectable() -> None:
    convention = MovementMissionConvention(
        tow_mission_ids=frozenset({20}),
        intercept_mission_ids=frozenset({21}),
    )
    result = classify_movement_intents(
        _state(
            _ship(1, mission="20"),
            _ship(2, mission="21"),
            _ship(3, mission="6"),
        ),
        convention=convention,
    )

    assert result.tow_attempt_ship_ids == frozenset({1})
    assert result.intercept_ship_ids == frozenset({2})
    assert result.move_most_candidate_ship_ids == frozenset({3})
