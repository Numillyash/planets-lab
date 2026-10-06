from __future__ import annotations

import pytest

from planets_lab.rules.combat.selection import ShipCombatSideInput
from planets_lab.rules.combat.site_input_adapter import (
    EvidenceInputUnresolved,
    build_parent_standard_pair_inputs,
    build_post_capture_candidate_states,
    filter_diplomacy_controls_through_vcr,
)
from planets_lab.rules.combat.site_state import (
    SiteCombatState,
    open_temporary_capture_order,
)


def _ship(owner_id: int) -> dict[str, int]:
    return {
        "owner_id": owner_id,
        "race_id": owner_id,
        "hull_id": 20,
    }


def _capture_state(*, candidate_owner: int = 2) -> SiteCombatState:
    base = SiteCombatState(
        active_ships={
            10: _ship(1),
            20: _ship(candidate_owner),
            30: _ship(1),
        },
        parent_queue_excluded_ship_ids=frozenset({10}),
    )
    return open_temporary_capture_order(
        base,
        prize_ship_id=10,
        captor_ship_id=30,
        order=(10, 20, 30),
    )


def _raw() -> dict[str, object]:
    return {
        "mission": 3,
        "mission1target": 0,
        "enemy": 0,
        "friendlycode": "abc",
        "neutronium": 10,
    }


def _capture_context(*, candidate_tminus1_owner: int = 2) -> dict[str, object]:
    return {
        "game_id": 400330,
        "battle_turn": 141,
        "before_turn": 140,
        "predictions": {
            10: {
                "owner_id": 9,
                "race_id": 9,
                "hull_id": 20,
                "hull_can_cloak": False,
                "raw": _raw(),
            },
            20: {
                "owner_id": candidate_tminus1_owner,
                "race_id": candidate_tminus1_owner,
                "hull_id": 20,
                "hull_can_cloak": False,
                "raw": _raw(),
            },
        },
        "relations": {140: {}},
        "controls": {
            ("sig", "dir"): {
                (140, 1, (1, 2)),
                (141, 593, (2, 3)),
                (141, 594, (3, 4)),
                (142, 1, (4, 5)),
            }
        },
        "start_stacks": {},
    }


def _candidate_input(**kwargs: object) -> ShipCombatSideInput:
    raw = kwargs["raw"]
    assert isinstance(raw, dict)
    return ShipCombatSideInput(
        ship_id=int(kwargs["ship_id"]),
        owner_id=int(kwargs["owner_id"]),
        race_id=int(kwargs["race_id"]),
        hull_id=int(kwargs["hull_id"]),
        mission=int(raw.get("mission", 0)),
        mission_target_id=int(raw.get("mission1target", 0)),
        primary_enemy=int(raw.get("enemy", 0)),
        friendly_code=raw.get("friendlycode"),
        hull_can_cloak=False,
        has_fuel=True,
        diplomacy_allows_attack=kwargs["diplomacy_allows_attack"],
        harmonic_weapon_modulation_enabled=False,
        cloak_and_intercept_enabled=False,
        cloak_and_intercept_hull_eligible=True,
        active_cloak_at_intercept=False,
        intercept_interference_protected=kwargs["interference_protected"],
        galactic_power_enabled=False,
        standard_targetable_by_opponent=True,
    )


def test_temporal_controls_drop_only_future_same_turn_rows() -> None:
    controls = {
        ("sig", "dir"): {
            (140, 1, (10, 20)),
            (141, 592, (20, 30)),
            (141, 593, (30, 40)),
            (141, 594, (40, 50)),
            (142, 1, (50, 60)),
        }
    }
    filtered = filter_diplomacy_controls_through_vcr(
        controls,
        target_battle_turn=141,
        through_vcr_id=593,
    )
    assert filtered[("sig", "dir")] == {
        (140, 1, (10, 20)),
        (141, 592, (20, 30)),
        (141, 593, (30, 40)),
        (142, 1, (50, 60)),
    }


def test_capture_adapter_uses_current_owner_and_bounded_diplomacy() -> None:
    observed_controls: list[dict[object, set[object]]] = []

    def permission(**kwargs: object) -> bool:
        controls = kwargs["controls"]
        assert isinstance(controls, dict)
        observed_controls.append(controls)
        return True

    result = build_post_capture_candidate_states(
        state=_capture_state(),
        context=_capture_context(),
        prize_ship_id=10,
        through_vcr_id=593,
        requests_combat=lambda raw, opponent: True,
        relation_signature=lambda rows, a, b: "sig",
        independent_permission=permission,
        pair_disposition=lambda **kwargs: ("eligible", None),
    )

    assert result.candidate_states[20].disposition == "eligible"
    assert result.candidate_states[30].disposition == "same_owner"
    assert observed_controls
    rows = observed_controls[0][("sig", "dir")]
    assert (141, 593, (2, 3)) in rows
    assert (141, 594, (3, 4)) not in rows
    assert result.diagnostics["diplomacy_controls_through_vcr_id"] == 593


def test_capture_adapter_fails_candidate_closed_on_owner_change() -> None:
    result = build_post_capture_candidate_states(
        state=_capture_state(candidate_owner=2),
        context=_capture_context(candidate_tminus1_owner=7),
        prize_ship_id=10,
        through_vcr_id=593,
        requests_combat=lambda raw, opponent: True,
        relation_signature=lambda rows, a, b: "sig",
        independent_permission=lambda **kwargs: True,
        pair_disposition=lambda **kwargs: ("eligible", None),
    )
    state = result.candidate_states[20]
    assert state.disposition == "unresolved"
    assert state.reason == "candidate_owner_changed_before_capture"


def test_parent_adapter_uses_parent_membership_and_tminus1_orders() -> None:
    state = SiteCombatState(
        active_ships={
            10: _ship(1),
            20: _ship(2),
            30: _ship(3),
        },
        parent_queue_excluded_ship_ids=frozenset({10}),
    )
    context = _capture_context()
    context["predictions"] = {
        20: {
            "owner_id": 2,
            "race_id": 2,
            "hull_id": 20,
            "hull_can_cloak": False,
            "raw": _raw(),
        },
        30: {
            "owner_id": 3,
            "race_id": 3,
            "hull_id": 20,
            "hull_can_cloak": False,
            "raw": _raw(),
        },
    }

    result = build_parent_standard_pair_inputs(
        state=state,
        context=context,
        target_battle_turn=141,
        through_vcr_id=593,
        requests_combat=lambda raw, opponent: True,
        relation_signature=lambda rows, a, b: "sig",
        independent_permission=lambda **kwargs: True,
        interference_state=lambda **kwargs: False,
        candidate_input=_candidate_input,
    )

    assert len(result.pair_inputs) == 1
    assert result.diagnostics["active_parent_ship_ids"] == [20, 30]
    assert "10" not in result.diagnostics["owner_order_context"]
    assert result.diagnostics["diplomacy_controls_through_vcr_id"] == 593


def test_parent_adapter_fails_closed_on_current_tminus1_owner_mismatch() -> None:
    state = SiteCombatState(
        active_ships={
            20: _ship(2),
            30: _ship(3),
        }
    )
    context = _capture_context()
    context["predictions"] = {
        20: {
            "owner_id": 7,
            "race_id": 7,
            "hull_id": 20,
            "hull_can_cloak": False,
            "raw": _raw(),
        },
        30: {
            "owner_id": 3,
            "race_id": 3,
            "hull_id": 20,
            "hull_can_cloak": False,
            "raw": _raw(),
        },
    }

    with pytest.raises(
        EvidenceInputUnresolved,
        match="current owner differs from T-1 owner",
    ):
        build_parent_standard_pair_inputs(
            state=state,
            context=context,
            target_battle_turn=141,
            through_vcr_id=593,
            requests_combat=lambda raw, opponent: True,
            relation_signature=lambda rows, a, b: "sig",
            independent_permission=lambda **kwargs: True,
            interference_state=lambda **kwargs: False,
            candidate_input=_candidate_input,
        )
