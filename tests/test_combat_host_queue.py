from __future__ import annotations

from planets_lab.rules.combat.host_queue import (
    StandardQueueState,
    record_standard_queue_step,
    select_after_ship_mutation,
    select_next_plain_standard,
)
from planets_lab.rules.combat.mutable_queue import apply_ship_terminal_batch
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import (
    ShipCombatSideInput,
    decide_ship_combat_pair,
)


def _side(ship_id: int, owner_id: int, **overrides: object) -> ShipCombatSideInput:
    values: dict[str, object] = {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": owner_id,
        "hull_id": 20,
        "mission": 0,
        "mission_target_id": 0,
        "primary_enemy": 0,
        "friendly_code": f"q{owner_id:02d}",
        "hull_can_cloak": False,
        "has_fuel": True,
        "diplomacy_allows_attack": True,
        "harmonic_weapon_modulation_enabled": False,
        "cloak_and_intercept_enabled": False,
        "cloak_and_intercept_hull_eligible": True,
        "active_cloak_at_intercept": False,
        "intercept_interference_protected": False,
        "galactic_power_enabled": False,
        "standard_targetable_by_opponent": True,
    }
    values.update(overrides)
    return ShipCombatSideInput(**values)


def _pair(
    left: ShipCombatSideInput,
    right: ShipCombatSideInput,
) -> InitialStandardPairInput:
    return InitialStandardPairInput(
        left=left,
        right=right,
        decision=decide_ship_combat_pair(
            left=left,
            right=right,
            same_location=True,
        ),
    )


def _active_ship(ship_id: int) -> dict[str, object]:
    return {
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


def _terminal(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "shield": 50,
        "damage": 10,
        "crew": 80,
        "torpedoes": 12,
        "fighters": 0,
        "destroyed": False,
        "captured": False,
    }
    values.update(overrides)
    return values


def test_first_occurrence_records_anchor_and_second_occurrence_reverses() -> None:
    pair = _pair(
        _side(13, 5, mission=8, primary_enemy=6, friendly_code="HYP"),
        _side(14, 6, mission=1, friendly_code="jih"),
    )

    first = select_next_plain_standard(
        pair_inputs=[pair],
        active_ship_ids={13, 14},
    )

    assert first.engagement_available is True
    assert first.pair == (13, 14)
    assert first.occurrence_index == 1
    assert (first.left_ship_id, first.right_ship_id) == (14, 13)

    state = record_standard_queue_step(StandardQueueState(), first)
    second = select_next_plain_standard(
        pair_inputs=[pair],
        active_ship_ids={13, 14},
        state=state,
    )

    assert second.engagement_available is True
    assert second.occurrence_index == 2
    assert (second.left_ship_id, second.right_ship_id) == (13, 14)


def test_exhausted_pair_is_skipped_before_canonical_selection() -> None:
    exhausted = _pair(
        _side(10, 1, mission=3),
        _side(20, 2),
    )
    remaining = _pair(
        _side(30, 3, mission=3),
        _side(40, 4),
    )
    state = StandardQueueState(
        pair_occurrences={(10, 20): 2},
        first_pass_sides={(10, 20): (20, 10)},
    )

    selected = select_next_plain_standard(
        pair_inputs=[exhausted, remaining],
        active_ship_ids={10, 20, 30, 40},
        state=state,
    )

    assert selected.engagement_available is True
    assert selected.pair == (30, 40)
    assert selected.occurrence_index == 1
    assert selected.exhausted_pair_count == 1


def test_second_occurrence_without_first_pass_anchor_fails_closed() -> None:
    pair = _pair(
        _side(10, 1, mission=3),
        _side(20, 2),
    )
    state = StandardQueueState(pair_occurrences={(10, 20): 1})

    selected = select_next_plain_standard(
        pair_inputs=[pair],
        active_ship_ids={10, 20},
        state=state,
    )

    assert selected.engagement_available is None
    assert selected.occurrence_index == 2
    assert "10-20:first_pass_sides_missing" in selected.unresolved_reasons


def test_post_mutation_selection_filters_destroyed_ship_pairs() -> None:
    active = {
        10: _active_ship(10),
        20: _active_ship(20),
        30: _active_ship(30),
    }
    mutation = apply_ship_terminal_batch(
        active_ships=active,
        terminals_by_ship_id={
            10: _terminal(destroyed=True, shield=0, damage=100, crew=0),
            20: _terminal(),
        },
    )
    removed_pair = _pair(
        _side(10, 1, mission=3),
        _side(20, 2),
    )
    surviving_pair = _pair(
        _side(20, 2, mission=3),
        _side(30, 3),
    )

    selected = select_after_ship_mutation(
        mutation=mutation,
        pair_inputs=[removed_pair, surviving_pair],
    )

    assert mutation.resolved is True
    assert selected.engagement_available is True
    assert selected.pair == (20, 30)
    assert selected.inactive_pair_count == 1


def test_unresolved_mutation_stops_queue_selection() -> None:
    mutation = apply_ship_terminal_batch(
        active_ships={10: _active_ship(10), 20: _active_ship(20)},
        terminals_by_ship_id={
            10: _terminal(),
            20: _terminal(captured=True, crew=0),
        },
    )
    pair = _pair(
        _side(10, 1, mission=3),
        _side(20, 2),
    )

    selected = select_after_ship_mutation(
        mutation=mutation,
        pair_inputs=[pair],
    )

    assert mutation.resolved is None
    assert selected.engagement_available is None
    assert selected.selection is None
    assert selected.unresolved_reasons[0] == "ship_queue_mutation_unresolved"


def test_record_rejects_stale_occurrence_step() -> None:
    pair = _pair(
        _side(10, 1, mission=3),
        _side(20, 2),
    )
    first = select_next_plain_standard(
        pair_inputs=[pair],
        active_ship_ids={10, 20},
    )
    state = record_standard_queue_step(StandardQueueState(), first)

    try:
        record_standard_queue_step(state, first)
    except ValueError as exc:
        assert "occurrence is inconsistent" in str(exc)
    else:
        raise AssertionError("expected ValueError")
