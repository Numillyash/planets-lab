from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_priority_intercept_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_priority_intercept_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_pia_side_classification_requires_target_pe_and_cloak() -> None:
    assert audit._pia_side_classification(
        raw={"mission": 7, "mission1target": 50, "enemy": 4},
        opponent_ship_id=50,
        target_owner_id=4,
        hull_can_cloak=True,
    ) == "targets_factual_opponent"
    assert audit._pia_side_classification(
        raw={"mission": 7, "mission1target": 50, "enemy": 5},
        opponent_ship_id=50,
        target_owner_id=4,
        hull_can_cloak=True,
    ) == "nonqualifying_intercept"
    assert audit._pia_side_classification(
        raw={"mission": 7, "mission1target": 50, "enemy": 4},
        opponent_ship_id=50,
        target_owner_id=4,
        hull_can_cloak=False,
    ) == "nonqualifying_intercept"


def test_pia_side_classification_distinguishes_other_target_and_unknown() -> None:
    assert audit._pia_side_classification(
        raw={"mission": 7, "mission1target": 99, "enemy": 4},
        opponent_ship_id=50,
        target_owner_id=4,
        hull_can_cloak=True,
    ) == "targets_other_ship"
    assert audit._pia_side_classification(
        raw={"mission": 7, "mission1target": 50, "enemy": 4},
        opponent_ship_id=50,
        target_owner_id=None,
        hull_can_cloak=True,
    ) == "signature_unknown"


def test_pia_pair_and_retaliation_form_prefix() -> None:
    queue = [
        {
            "vcr_id": 10,
            "pair": (20, 90),
            "pia_attackers": (90,),
            "left_ship_id": 20,
            "right_ship_id": 90,
        },
        {
            "vcr_id": 11,
            "pair": (20, 90),
            "pia_attackers": (90,),
            "left_ship_id": 90,
            "right_ship_id": 20,
        },
        {
            "vcr_id": 12,
            "pair": (20, 30),
            "pia_attackers": (),
            "left_ship_id": 30,
            "right_ship_id": 20,
        },
    ]
    summary = audit._site_pia_summary(queue)
    assert summary["pia_linked_pairs"] == 1
    assert summary["prefix_violation"] is False
    assert summary["attacker_sides"] == {"attacker_right": 1}


def test_regular_combat_before_pia_is_prefix_violation() -> None:
    queue = [
        {
            "vcr_id": 1,
            "pair": (10, 20),
            "pia_attackers": (),
            "left_ship_id": 10,
            "right_ship_id": 20,
        },
        {
            "vcr_id": 2,
            "pair": (30, 90),
            "pia_attackers": (90,),
            "left_ship_id": 30,
            "right_ship_id": 90,
        },
    ]
    assert audit._site_pia_summary(queue)["prefix_violation"] is True


def test_multiple_pia_attackers_expect_reverse_ship_id_first_occurrence() -> None:
    exact = audit._site_pia_summary(
        [
            {
                "vcr_id": 1,
                "pair": (10, 90),
                "pia_attackers": (90,),
                "left_ship_id": 10,
                "right_ship_id": 90,
            },
            {
                "vcr_id": 2,
                "pair": (20, 50),
                "pia_attackers": (50,),
                "left_ship_id": 20,
                "right_ship_id": 50,
            },
        ]
    )
    assert exact["reverse_id_comparable"] is True
    assert exact["reverse_id_exact"] is True
    assert exact["factual_first_attacker_order"] == [90, 50]

    mismatch = audit._site_pia_summary(
        [
            {
                "vcr_id": 1,
                "pair": (20, 50),
                "pia_attackers": (50,),
                "left_ship_id": 20,
                "right_ship_id": 50,
            },
            {
                "vcr_id": 2,
                "pair": (10, 90),
                "pia_attackers": (90,),
                "left_ship_id": 10,
                "right_ship_id": 90,
            },
        ]
    )
    assert mismatch["reverse_id_comparable"] is True
    assert mismatch["reverse_id_exact"] is False


def test_mutual_pia_pair_is_not_reverse_id_comparable() -> None:
    summary = audit._site_pia_summary(
        [
            {
                "vcr_id": 1,
                "pair": (20, 90),
                "pia_attackers": (20, 90),
                "left_ship_id": 20,
                "right_ship_id": 90,
            }
        ]
    )
    assert summary["pia_ambiguous_pairs"] == 1
    assert summary["reverse_id_comparable"] is False
