from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_frozen_candidate import (
    DISCOVERY_EXACT,
    DISCOVERY_MISMATCH,
    DISCOVERY_UNRESOLVED,
    predict_frozen_capture_side,
)


def test_frozen_capture_side_candidate() -> None:
    assert DISCOVERY_EXACT == 31
    assert DISCOVERY_MISMATCH == 0
    assert DISCOVERY_UNRESOLVED == 0

    assert (
        predict_frozen_capture_side(
            identity_anchored_o_pair_reachable=True,
            capture_side="right",
            neutral_fresh_fc_side="left",
        )
        == "right"
    )
    assert (
        predict_frozen_capture_side(
            identity_anchored_o_pair_reachable=False,
            capture_side="right",
            neutral_fresh_fc_side="left",
        )
        == "left"
    )
    assert (
        predict_frozen_capture_side(
            identity_anchored_o_pair_reachable=None,
            capture_side="right",
            neutral_fresh_fc_side="left",
        )
        is None
    )
