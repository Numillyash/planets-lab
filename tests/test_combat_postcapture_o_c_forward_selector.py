from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = REPO_ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

from combat_postcapture_o_c_forward_selector import (
    CandidateState,
    select_o_then_c_forward,
)


FIXTURE = (
    REPO_ROOT
    / "validation"
    / "combat"
    / "postcapture-o-c-forward-independent-fixture.json"
)


def test_imported_selector_replays_all_independent_c_cases_exactly() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["runtime_status"] == "PASS_PARTIAL_BRANCH_COVERAGE"
    assert provenance["qualified_rows"] == 6
    assert provenance["exact"] == 6
    assert provenance["mismatch"] == 0
    assert provenance["unresolved"] == 0
    assert provenance["branch_counts"] == {"O": 0, "C": 6}

    cases = payload["cases"]
    assert len(cases) == 6

    for row in cases:
        states = {
            int(ship_id): CandidateState(
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
        assert result.predicted_ship_id == row["primary"]["predicted_ship_id"]
        assert row["primary"]["exact"] is True


def test_fixture_preserves_game400330_chain_anchors() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = {
        row["capture_vcr_id"]: row
        for row in payload["cases"]
        if row["game_id"] == 400330 and row["turn"] == 141
    }
    assert sorted(rows) == [592, 594]
    assert rows[592]["captured_ship_id"] == 140
    assert rows[592]["captor_ship_id"] == 184
    assert rows[592]["factual_opponent_ship_id"] == 170
    assert rows[594]["captured_ship_id"] == 170
    assert rows[594]["captor_ship_id"] == 184
    assert rows[594]["factual_opponent_ship_id"] == 382
