from __future__ import annotations

from planets_lab.rules.combat.capture_queue import CaptureCandidateState
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import (
    ShipCombatSideInput,
    decide_ship_combat_pair,
)
from planets_lab.rules.combat.site_executor import (
    select_parent_resume,
    select_temporary_capture_continuation,
)
from planets_lab.rules.combat.site_state import (
    SiteCombatState,
    open_temporary_capture_order,
)


def _ship(ship_id: int, owner_id: int) -> dict[str, object]:
    return {
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


def _side(ship_id: int, owner_id: int, mission: int = 0):
    return ShipCombatSideInput(
        ship_id=ship_id,
        owner_id=owner_id,
        race_id=owner_id,
        hull_id=20,
        mission=mission,
        mission_target_id=0,
        primary_enemy=0,
        friendly_code=f"q{owner_id}",
        hull_can_cloak=False,
        has_fuel=True,
        diplomacy_allows_attack=True,
        harmonic_weapon_modulation_enabled=False,
        cloak_and_intercept_enabled=False,
        cloak_and_intercept_hull_eligible=True,
        active_cloak_at_intercept=False,
        intercept_interference_protected=False,
        galactic_power_enabled=False,
        standard_targetable_by_opponent=True,
    )


def _pair(a: ShipCombatSideInput, b: ShipCombatSideInput):
    return InitialStandardPairInput(
        left=a,
        right=b,
        decision=decide_ship_combat_pair(
            left=a,
            right=b,
            same_location=True,
        ),
    )


def _capture_state() -> SiteCombatState:
    base = SiteCombatState(
        active_ships={
            10: _ship(10, 1),
            20: _ship(20, 2),
            30: _ship(30, 1),
            40: _ship(40, 4),
        },
        parent_queue_excluded_ship_ids=frozenset({10}),
    )
    return open_temporary_capture_order(
        base,
        prize_ship_id=10,
        captor_ship_id=30,
        order=(10, 20, 30, 40),
    )


def test_temporary_c_continuation_resolves_and_keeps_order_open() -> None:
    state = _capture_state()
    result = select_temporary_capture_continuation(
        state,
        candidate_states={
            20: CaptureCandidateState(20, "eligible"),
            40: CaptureCandidateState(40, "inactive"),
        },
    )
    assert result.status == "resolved"
    assert result.branch == "C"
    assert result.pair == (10, 20)
    assert result.opponent_ship_id == 20
    assert result.state.temporary_capture_order is not None


def test_temporary_exhaustion_clears_order_and_requires_parent_resume() -> None:
    state = _capture_state()
    result = select_temporary_capture_continuation(
        state,
        candidate_states={
            20: CaptureCandidateState(20, "same_owner"),
            40: CaptureCandidateState(40, "inactive"),
        },
    )
    assert result.status == "parent_resume_required"
    assert result.reason == "o_and_c_forward_exhausted"
    assert result.state.temporary_capture_order is None
    assert 10 in result.state.active_ships
    assert 10 in result.state.parent_queue_excluded_ship_ids


def test_uncovered_o_branch_fails_closed_by_default() -> None:
    state = _capture_state()
    result = select_temporary_capture_continuation(
        state,
        candidate_states={
            20: CaptureCandidateState(20, "same_owner"),
            40: CaptureCandidateState(40, "eligible"),
        },
    )
    assert result.status == "unresolved"
    assert result.branch == "O"
    assert result.reason == "o_branch_not_independently_covered"
    assert result.state.temporary_capture_order is not None


def test_parent_resume_uses_parent_membership_and_carried_history() -> None:
    state = SiteCombatState(
        active_ships={
            10: _ship(10, 1),
            20: _ship(20, 2),
            30: _ship(30, 3),
        },
        parent_queue_excluded_ship_ids=frozenset({10}),
    )
    result = select_parent_resume(
        state,
        pair_inputs=[
            _pair(_side(10, 1, mission=3), _side(20, 2)),
            _pair(_side(20, 2, mission=3), _side(30, 3)),
        ],
    )
    assert result.status == "resolved"
    assert result.pair == (20, 30)
    assert result.left_ship_id == 30
    assert result.right_ship_id == 20
    assert result.selection.inactive_pair_count == 1


def test_parent_resume_propagates_unresolved_selection() -> None:
    state = SiteCombatState(
        active_ships={
            20: _ship(20, 2),
            30: _ship(30, 3),
        }
    )
    unresolved = InitialStandardPairInput(
        left=_side(20, 2, mission=3),
        right=_side(30, 3),
        decision=decide_ship_combat_pair(
            left=_side(20, 2, mission=3),
            right=_side(
                30,
                3,
            ),
            same_location=None,
        ),
    )
    result = select_parent_resume(
        state,
        pair_inputs=[unresolved],
    )
    assert result.status == "unresolved"
    assert result.reason is not None
