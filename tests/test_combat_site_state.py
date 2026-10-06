from __future__ import annotations

from planets_lab.rules.combat.mutable_queue import ShipCaptureTransfer
from planets_lab.rules.combat.site_state import (
    SiteCombatState,
    clear_temporary_capture_order,
    apply_site_terminal_batch,
    open_temporary_capture_order,
    parent_queue_active_ship_ids,
    record_factual_site_pair,
)


def _ship(ship_id: int, owner_id: int, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": ship_id,
        "owner_id": owner_id,
        "race_id": owner_id,
        "hull_id": 20,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "beam_count": 4,
        "tube_count": 2,
        "torpedoes": 20,
        "fighters": 0,
        "federation_crew_bonus": False,
        "lizard_crew_bonus": False,
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


def _transfer(owner_id: int) -> ShipCaptureTransfer:
    return ShipCaptureTransfer(
        new_owner_id=owner_id,
        new_race_id=owner_id,
        new_federation_crew_bonus=owner_id == 1,
        new_lizard_crew_bonus=owner_id == 2,
    )


def test_capture_keeps_prize_active_but_removes_it_from_parent_queue() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 10),
            170: _ship(170, 10),
            184: _ship(184, 5),
        }
    )
    transition = apply_site_terminal_batch(
        state,
        terminals_by_ship_id={
            140: _terminal(captured=True, shield=0, crew=0),
            184: _terminal(),
        },
        capture_transfers_by_ship_id={140: _transfer(5)},
    )

    assert transition.resolved is True
    assert 140 in transition.state.active_ships
    assert transition.state.active_ships[140]["owner_id"] == 5
    assert transition.state.parent_queue_excluded_ship_ids == frozenset({140})
    assert parent_queue_active_ship_ids(transition.state) == frozenset({170, 184})


def test_temporary_capture_order_clear_does_not_reinsert_prize() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            170: _ship(170, 10),
            184: _ship(184, 5),
        },
        parent_queue_excluded_ship_ids=frozenset({140}),
    )
    state = open_temporary_capture_order(
        state,
        prize_ship_id=140,
        captor_ship_id=184,
        order=(140, 170, 184),
    )
    assert state.temporary_capture_order is not None

    cleared = clear_temporary_capture_order(
        state,
        expected_prize_ship_id=140,
    )
    assert cleared.temporary_capture_order is None
    assert 140 in cleared.active_ships
    assert 140 in cleared.parent_queue_excluded_ship_ids
    assert 140 not in parent_queue_active_ship_ids(cleared)


def test_new_capture_order_replaces_previous_prize_order() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            170: _ship(170, 10),
            184: _ship(184, 5),
        },
        parent_queue_excluded_ship_ids=frozenset({140}),
    )
    state = open_temporary_capture_order(
        state,
        prize_ship_id=140,
        captor_ship_id=184,
        order=(140, 170, 184),
    )

    transition = apply_site_terminal_batch(
        state,
        terminals_by_ship_id={
            140: _terminal(captured=True, shield=0, crew=0),
            170: _terminal(),
        },
        capture_transfers_by_ship_id={140: _transfer(10)},
    )
    assert transition.resolved is True

    replaced = open_temporary_capture_order(
        transition.state,
        prize_ship_id=140,
        captor_ship_id=170,
        order=(140, 170, 184),
    )
    assert replaced.temporary_capture_order is not None
    assert replaced.temporary_capture_order.prize_ship_id == 140
    assert replaced.temporary_capture_order.captor_ship_id == 170
    assert replaced.parent_queue_excluded_ship_ids == frozenset({140})


def test_second_captured_prize_accumulates_parent_exclusion() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 10),
            170: _ship(170, 10),
            184: _ship(184, 5),
            382: _ship(382, 10),
        },
        parent_queue_excluded_ship_ids=frozenset({140}),
    )

    transition = apply_site_terminal_batch(
        state,
        terminals_by_ship_id={
            170: _terminal(captured=True, shield=0, crew=0),
            184: _terminal(),
        },
        capture_transfers_by_ship_id={170: _transfer(5)},
    )
    assert transition.resolved is True
    assert transition.state.parent_queue_excluded_ship_ids == frozenset(
        {140, 170}
    )
    assert parent_queue_active_ship_ids(transition.state) == frozenset({184, 382})


def test_destroyed_excluded_ship_is_removed_from_exclusion_set() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            184: _ship(184, 5),
        },
        parent_queue_excluded_ship_ids=frozenset({140}),
    )
    transition = apply_site_terminal_batch(
        state,
        terminals_by_ship_id={
            140: _terminal(destroyed=True, shield=0, damage=100, crew=0),
            184: _terminal(),
        },
    )
    assert transition.resolved is True
    assert 140 not in transition.state.active_ships
    assert transition.state.parent_queue_excluded_ship_ids == frozenset()


def test_factual_pair_history_carries_and_requires_second_pass_reversal() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            170: _ship(170, 10),
        }
    )
    first = record_factual_site_pair(
        state,
        left_ship_id=140,
        right_ship_id=170,
    )
    assert first.standard_queue_state.pair_occurrences[(140, 170)] == 1
    assert first.standard_queue_state.first_pass_sides[(140, 170)] == (140, 170)

    second = record_factual_site_pair(
        first,
        left_ship_id=170,
        right_ship_id=140,
    )
    assert second.standard_queue_state.pair_occurrences[(140, 170)] == 2

    try:
        record_factual_site_pair(
            first,
            left_ship_id=140,
            right_ship_id=170,
        )
    except ValueError as exc:
        assert "second_pass_not_reversed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_unresolved_terminal_mutation_keeps_entire_site_state_atomic() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            170: _ship(170, 10),
        },
        parent_queue_excluded_ship_ids=frozenset({140}),
    )
    transition = apply_site_terminal_batch(
        state,
        terminals_by_ship_id={
            140: _terminal(captured=True, shield=0, crew=0),
            170: _terminal(),
        },
    )
    assert transition.resolved is None
    assert transition.state == state
    assert transition.mutation.unresolved_reasons == (
        "140:capture_branch_unresolved",
    )


def test_temporary_order_requires_parent_excluded_prize() -> None:
    state = SiteCombatState(
        active_ships={
            140: _ship(140, 5),
            184: _ship(184, 5),
        }
    )
    try:
        open_temporary_capture_order(
            state,
            prize_ship_id=140,
            captor_ship_id=184,
            order=(140, 184),
        )
    except ValueError as exc:
        assert "excluded from parent queue" in str(exc)
    else:
        raise AssertionError("expected ValueError")
