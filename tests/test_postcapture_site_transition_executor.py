from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from planets_lab.rules.combat.host_queue import StandardQueueState
from planets_lab.rules.combat.mutable_queue import ShipQueueMutationResult
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import (
    ShipCombatSideInput,
    decide_ship_combat_pair,
)


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "research"
for path in (TOOLS_DIR,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

MODULE_PATH = TOOLS_DIR / "postcapture_site_transition_executor.py"
SPEC = importlib.util.spec_from_file_location(
    "postcapture_site_transition_executor",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SELECTOR_PATH = TOOLS_DIR / "postcapture_o_c_forward_selector.py"
SELECTOR_SPEC = importlib.util.spec_from_file_location(
    "postcapture_o_c_forward_selector_for_test",
    SELECTOR_PATH,
)
assert SELECTOR_SPEC is not None and SELECTOR_SPEC.loader is not None
SELECTOR = importlib.util.module_from_spec(SELECTOR_SPEC)
sys.modules[SELECTOR_SPEC.name] = SELECTOR
SELECTOR_SPEC.loader.exec_module(SELECTOR)


def _side(ship_id: int, owner_id: int, *, mission: int = 0):
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


def _mutation(*ship_ids: int) -> ShipQueueMutationResult:
    return ShipQueueMutationResult(
        resolved=True,
        active_ships={ship_id: {"id": ship_id} for ship_id in ship_ids},
    )


def test_elapsed_pair_history_anchors_then_requires_reversal() -> None:
    state = StandardQueueState()
    first = MODULE.record_elapsed_factual_pair(
        state,
        left_ship_id=20,
        right_ship_id=10,
    )
    assert first.state is not None
    assert first.state.pair_occurrences[(10, 20)] == 1
    assert first.state.first_pass_sides[(10, 20)] == (20, 10)

    second = MODULE.record_elapsed_factual_pair(
        first.state,
        left_ship_id=10,
        right_ship_id=20,
    )
    assert second.state is not None
    assert second.state.pair_occurrences[(10, 20)] == 2

    bad = MODULE.record_elapsed_factual_pair(
        first.state,
        left_ship_id=20,
        right_ship_id=10,
    )
    assert bad.state is None
    assert bad.reason == "10-20:second_pass_not_reversed"


def test_capture_transition_uses_frozen_c_cursor() -> None:
    states = {
        20: SELECTOR.CandidateState(20, "eligible"),
        30: SELECTOR.CandidateState(30, "same_owner"),
        40: SELECTOR.CandidateState(40, "inactive"),
    }
    context = MODULE.CaptureContinuationContext(
        order=(10, 20, 30, 40),
        prize_ship_id=10,
        captor_ship_id=30,
        states=states,
    )
    result = MODULE.select_after_resolved_vcr(
        mutation=_mutation(10, 20, 30),
        queue_state=StandardQueueState(),
        ordinary_pair_inputs=[],
        capture_context=context,
    )
    assert result.status == "resolved"
    assert result.source == "capture_cursor"
    assert result.branch == "C"
    assert result.pair == (10, 20)
    assert result.predicted_opponent_ship_id == 20


def test_capture_transition_uses_o_before_c() -> None:
    states = {
        20: SELECTOR.CandidateState(20, "eligible"),
        40: SELECTOR.CandidateState(40, "eligible"),
    }
    context = MODULE.CaptureContinuationContext(
        order=(10, 20, 30, 40),
        prize_ship_id=10,
        captor_ship_id=30,
        states=states,
    )
    result = MODULE.select_after_resolved_vcr(
        mutation=_mutation(10, 20, 30, 40),
        queue_state=StandardQueueState(),
        ordinary_pair_inputs=[],
        capture_context=context,
    )
    assert result.status == "resolved"
    assert result.branch == "O"
    assert result.pair == (10, 40)


def test_capture_cursor_exhaustion_does_not_guess_global_resume() -> None:
    states = {
        20: SELECTOR.CandidateState(20, "pair_blocked"),
        40: SELECTOR.CandidateState(40, "inactive"),
    }
    context = MODULE.CaptureContinuationContext(
        order=(10, 20, 30, 40),
        prize_ship_id=10,
        captor_ship_id=30,
        states=states,
    )
    result = MODULE.select_after_resolved_vcr(
        mutation=_mutation(10, 20, 30),
        queue_state=StandardQueueState(),
        ordinary_pair_inputs=[
            _pair(_side(30, 3, mission=3), _side(50, 5)),
        ],
        capture_context=context,
    )
    assert result.status == "no_pair"
    assert result.source == "capture_cursor"
    assert result.pair is None


def test_ordinary_transition_reuses_production_queue() -> None:
    ordinary = _pair(
        _side(20, 2, mission=3),
        _side(30, 3),
    )
    result = MODULE.select_after_resolved_vcr(
        mutation=_mutation(20, 30),
        queue_state=StandardQueueState(),
        ordinary_pair_inputs=[ordinary],
    )
    assert result.status == "resolved"
    assert result.source == "ordinary_queue"
    assert result.pair == (20, 30)
    assert result.predicted_left_ship_id == 30
    assert result.predicted_right_ship_id == 20


def test_unresolved_mutation_stops_both_paths() -> None:
    mutation = ShipQueueMutationResult(
        resolved=None,
        active_ships={10: {"id": 10}},
        unresolved_reasons=("capture_branch_unresolved",),
    )
    result = MODULE.select_after_resolved_vcr(
        mutation=mutation,
        queue_state=StandardQueueState(),
        ordinary_pair_inputs=[],
    )
    assert result.status == "unresolved"
    assert result.source is None
    assert result.reason == "ship_queue_mutation_unresolved"
