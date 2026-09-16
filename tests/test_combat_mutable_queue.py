from __future__ import annotations

from planets_lab.rules.combat.mutable_queue import apply_ship_terminal_batch


def _ship(ship_id: int, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": ship_id,
        "hull_id": 20,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "beam_count": 4,
        "tube_count": 2,
        "torpedoes": 20,
        "fighters": 0,
        "federation_crew_bonus": False,
    }
    values.update(overrides)
    return values


def _terminal(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "shield": 40,
        "damage": 10,
        "crew": 80,
        "torpedoes": 12,
        "fighters": 0,
        "destroyed": False,
        "captured": False,
    }
    values.update(overrides)
    return values


def test_destroyed_ship_removed_survivor_carried_and_unrelated_preserved() -> None:
    active = {
        10: _ship(10),
        20: _ship(20),
        30: _ship(30, shield=77),
    }
    result = apply_ship_terminal_batch(
        active_ships=active,
        terminals_by_ship_id={
            10: _terminal(destroyed=True, shield=0, damage=100, crew=0),
            20: _terminal(shield=30, damage=15, crew=70, torpedoes=11),
        },
    )
    assert result.resolved is True
    assert result.removed_ship_ids == (10,)
    assert result.carried_ship_ids == (20,)
    assert 10 not in result.active_ships
    assert result.active_ships[20]["shield"] == 30
    assert result.active_ships[20]["damage"] == 15
    assert result.active_ships[20]["crew"] == 70
    assert result.active_ships[20]["torpedoes"] == 11
    assert result.active_ships[30] == active[30]


def test_two_survivors_are_carried_atomically() -> None:
    result = apply_ship_terminal_batch(
        active_ships={10: _ship(10), 20: _ship(20)},
        terminals_by_ship_id={
            10: _terminal(shield=60, damage=5),
            20: _terminal(shield=20, damage=25),
        },
    )
    assert result.resolved is True
    assert result.removed_ship_ids == ()
    assert result.carried_ship_ids == (10, 20)
    assert result.active_ships[10]["shield"] == 60
    assert result.active_ships[20]["shield"] == 20


def test_federation_between_combat_recharge_is_reused_from_c3() -> None:
    result = apply_ship_terminal_batch(
        active_ships={10: _ship(10, federation_crew_bonus=True)},
        terminals_by_ship_id={10: _terminal(shield=40, damage=0)},
    )
    assert result.resolved is True
    assert result.active_ships[10]["shield"] == 65


def test_capture_fails_closed_without_partial_sibling_deletion() -> None:
    active = {10: _ship(10), 20: _ship(20)}
    result = apply_ship_terminal_batch(
        active_ships=active,
        terminals_by_ship_id={
            10: _terminal(destroyed=True, shield=0, damage=100),
            20: _terminal(captured=True, crew=0),
        },
    )
    assert result.resolved is None
    assert result.active_ships == active
    assert result.removed_ship_ids == ()
    assert result.carried_ship_ids == ()
    assert "20:capture_branch_unresolved" in result.unresolved_reasons


def test_unknown_terminal_flags_fail_closed_atomically() -> None:
    active = {10: _ship(10), 20: _ship(20)}
    terminal = _terminal()
    terminal.pop("destroyed")
    result = apply_ship_terminal_batch(
        active_ships=active,
        terminals_by_ship_id={10: terminal, 20: _terminal(destroyed=True)},
    )
    assert result.resolved is None
    assert result.active_ships == active
    assert "10:destroyed_state_unresolved" in result.unresolved_reasons


def test_incomplete_survivor_does_not_partially_commit_prior_deletion() -> None:
    active = {10: _ship(10), 20: _ship(20)}
    malformed_survivor = _terminal()
    malformed_survivor.pop("damage")
    result = apply_ship_terminal_batch(
        active_ships=active,
        terminals_by_ship_id={
            10: _terminal(destroyed=True),
            20: malformed_survivor,
        },
    )
    assert result.resolved is None
    assert result.active_ships == active
    assert result.removed_ship_ids == ()
    assert result.carried_ship_ids == ()
    assert "20:survivor_damage_unresolved" in result.unresolved_reasons


def test_terminal_for_inactive_ship_is_programming_error() -> None:
    try:
        apply_ship_terminal_batch(
            active_ships={10: _ship(10)},
            terminals_by_ship_id={20: _terminal()},
        )
    except ValueError as exc:
        assert "not active" in str(exc)
    else:
        raise AssertionError("expected ValueError")
