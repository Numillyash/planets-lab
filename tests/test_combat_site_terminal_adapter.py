from __future__ import annotations

from typing import Any, Mapping

from planets_lab.rules.combat.mutable_queue import apply_ship_terminal_batch
from planets_lab.rules.combat.site_state import SiteCombatState
from planets_lab.rules.combat.site_terminal_adapter import (
    build_site_terminal_replay_batch,
    compare_site_state_to_vcr_start,
)


def _ship(owner: int, race: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "owner_id": owner,
        "race_id": race,
        "hull_id": 5,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "torpedoes": 4,
        "fighters": 0,
        "beam_count": 2,
        "launcher_count": 1,
        "bay_count": 0,
        "physical_beam_count": 2,
        "physical_launcher_count": 1,
        "physical_bay_count": 0,
        "federation_crew_bonus": race == 1,
        "lizard_crew_bonus": race == 2,
    }
    row.update(overrides)
    return row


def _side(ship_id: int, race: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "objectid": ship_id,
        "hullid": 5,
        "raceid": race,
        "shield": 100,
        "damage": 0,
        "crew": 100,
        "torpedos": 4,
        "fighters": 0,
        "beamcount": 2,
        "launchercount": 1,
        "baycount": 0,
        "beamid": 1,
        "torpedoid": 1,
        "mass": 100,
        "beamkillbonus": 1,
        "beamchargerate": 1,
        "torpchargerate": 1,
        "torpmisspercent": 35,
        "crewdefensepercent": 0,
    }
    row.update(overrides)
    return row


def _vcr() -> dict[str, object]:
    return {
        "id": 7,
        "turn": 10,
        "seed": 3,
        "battletype": 1,
        "leftownerid": 1,
        "rightownerid": 3,
        "left": _side(100, 1),
        "right": _side(200, 3),
    }


def test_start_comparison_requires_carried_vector_exact() -> None:
    state = SiteCombatState(
        active_ships={
            100: _ship(1, 1),
            200: _ship(3, 3),
        }
    )
    comparison = compare_site_state_to_vcr_start(state, vcr_payload=_vcr())
    assert comparison.exact is True

    drifted = SiteCombatState(
        active_ships={
            100: _ship(1, 1, shield=99),
            200: _ship(3, 3),
        }
    )
    comparison = compare_site_state_to_vcr_start(drifted, vcr_payload=_vcr())
    assert comparison.exact is False
    assert any(
        row["field"] == "shield"
        and row["ship_id"] == 100
        and row["exact"] is False
        for row in comparison.comparisons
    )


def test_replay_payload_uses_carried_state_and_capture_transfer_from_captor() -> None:
    state = SiteCombatState(
        active_ships={
            100: _ship(1, 1),
            200: _ship(3, 3),
        }
    )
    observed: dict[str, Any] = {}

    def fake_replay(
        payload: Mapping[str, Any],
        *,
        beams: object,
        torpedoes: object,
        settings: object,
    ) -> Mapping[str, Any]:
        observed.update(payload)
        return {
            "left": {
                "object_id": 100,
                "shield": 0,
                "damage": 35,
                "crew": 0,
                "torpedoes": 2,
                "fighters": 0,
                "destroyed": False,
                "captured": True,
            },
            "right": {
                "object_id": 200,
                "shield": 70,
                "damage": 10,
                "crew": 80,
                "torpedoes": 3,
                "fighters": 0,
                "destroyed": False,
                "captured": False,
            },
        }

    result = build_site_terminal_replay_batch(
        state,
        vcr_payload=_vcr(),
        beams=[],
        torpedoes=[],
        settings={"combatrng": 0},
        replay_resolver=fake_replay,
    )

    assert result.resolved is True
    assert observed["leftownerid"] == 1
    left = observed["left"]
    assert isinstance(left, dict)
    assert left["shield"] == 100
    assert left["beamcount"] == 2

    transfer = result.capture_transfers_by_ship_id[100]
    assert transfer.new_owner_id == 3
    assert transfer.new_race_id == 3
    assert transfer.new_federation_crew_bonus is False
    assert transfer.new_lizard_crew_bonus is False

    mutation = apply_ship_terminal_batch(
        active_ships=state.active_ships,
        terminals_by_ship_id=result.terminals_by_ship_id,
        capture_transfers_by_ship_id=result.capture_transfers_by_ship_id,
    )
    assert mutation.resolved is True
    assert mutation.active_ships[100]["owner_id"] == 3
    assert mutation.active_ships[100]["crew"] == 10


def test_replay_fails_closed_when_carried_start_drifted() -> None:
    state = SiteCombatState(
        active_ships={
            100: _ship(1, 1, damage=1),
            200: _ship(3, 3),
        }
    )
    called = False

    def fake_replay(*args: object, **kwargs: object) -> Mapping[str, Any]:
        nonlocal called
        called = True
        return {}

    result = build_site_terminal_replay_batch(
        state,
        vcr_payload=_vcr(),
        beams=[],
        torpedoes=[],
        settings={"combatrng": 0},
        replay_resolver=fake_replay,
    )
    assert result.resolved is None
    assert result.reason == "carried_start_differs_from_current_vcr"
    assert called is False
