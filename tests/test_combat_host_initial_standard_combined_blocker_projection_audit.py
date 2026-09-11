from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_combined_blocker_projection_audit import (  # noqa: E402
    _project_single_rank1_removal,
)


def test_rank1_block_projects_fix_for_same_active_rank2_factual_target() -> None:
    assert _project_single_rank1_removal(
        predicted_target=202,
        predicted_active=496,
        factual_target_rank=2,
        factual_right=496,
        blocked_target_ship_id=202,
    ) is True


def test_projection_rejects_different_active_ship() -> None:
    assert _project_single_rank1_removal(
        predicted_target=202,
        predicted_active=496,
        factual_target_rank=2,
        factual_right=123,
        blocked_target_ship_id=202,
    ) is False


def test_projection_rejects_non_rank2_factual_target() -> None:
    assert _project_single_rank1_removal(
        predicted_target=202,
        predicted_active=496,
        factual_target_rank=3,
        factual_right=496,
        blocked_target_ship_id=202,
    ) is False


def test_projection_rejects_wrong_blocked_target() -> None:
    assert _project_single_rank1_removal(
        predicted_target=202,
        predicted_active=496,
        factual_target_rank=2,
        factual_right=496,
        blocked_target_ship_id=98,
    ) is False
