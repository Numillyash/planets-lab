from __future__ import annotations

import json
from pathlib import Path

from planets_lab.rules.combat.capture_queue import (
    CaptureCandidateState,
    select_o_then_c_forward,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    REPO_ROOT
    / "validation"
    / "combat"
    / "postcapture-o-c-forward-independent-fixture.json"
)


def test_capture_queue_replays_independent_c_fixture_exactly() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert len(cases) == 6

    for row in cases:
        states = {
            int(ship_id): CaptureCandidateState(
                ship_id=int(ship_id),
                disposition=details["disposition"],
                reason=details.get("reason"),
            )
            for ship_id, details in row["primary"]["candidate_states"].items()
        }
        result = select_o_then_c_forward(
            order=tuple(row["external_order"]),
            prize_ship_id=row["captured_ship_id"],
            captor_ship_id=row["captor_ship_id"],
            states=states,
        )
        assert result.status == "resolved"
        assert result.branch == "C"
        assert result.predicted_ship_id == row["factual_opponent_ship_id"]


def test_capture_queue_fails_closed_on_missing_candidate_state() -> None:
    result = select_o_then_c_forward(
        order=(10, 20, 30),
        prize_ship_id=10,
        captor_ship_id=30,
        states={},
    )
    assert result.status == "unresolved"
    assert result.branch == "C"
    assert result.unresolved_ship_id == 20
    assert result.reason == "candidate_state_missing"


def test_capture_queue_reports_clean_exhaustion() -> None:
    result = select_o_then_c_forward(
        order=(10, 20, 30),
        prize_ship_id=10,
        captor_ship_id=30,
        states={
            20: CaptureCandidateState(20, "same_owner"),
        },
    )
    assert result.status == "no_pair"
    assert result.reason == "o_and_c_forward_exhausted"
