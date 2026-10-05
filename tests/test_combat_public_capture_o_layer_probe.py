from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_o_layer_probe import (
    _appearance_mapping,
    _pseudo_seen_from_appearances,
    _capture_projection,
    _identity_anchor_factual_opponent,
    _targets_by_site,
)


def test_targets_by_site_groups_discovery_rows() -> None:
    rows = [
        {
            "game_id": 42,
            "turn": 7,
            "position": [100, 200],
            "captured_ship_id": 10,
        },
        {
            "game_id": 42,
            "turn": 7,
            "position": [100, 200],
            "captured_ship_id": 11,
        },
    ]
    grouped = _targets_by_site(rows)
    assert list(grouped) == [(42, 7, 100, 200)]
    assert [row["captured_ship_id"] for row in grouped[(42, 7, 100, 200)]] == [10, 11]


def test_appearance_mapping_uses_replay_identity() -> None:
    rows = [
        {
            "game_id": 42,
            "turn": 7,
            "vcr_id": 9,
            "ship_id": 11,
            "side": "left",
        }
    ]
    mapped = _appearance_mapping(rows)
    assert mapped[(42, 7, 9, 11)]["side"] == "left"


def test_capture_projection_keeps_only_probe_contract() -> None:
    row = {
        "captured_ship_id": 10,
        "captor_ship_id": 20,
        "captor_owner_id": 2,
        "next_opponent_ship_id": 30,
        "capture_vcr_id": 100,
        "next_vcr_id": 101,
        "captured_ship_side_next": "right",
    }
    assert _capture_projection(row) == {
        "ship_id": 10,
        "captor_ship_id": 20,
        "captor_owner_id": 2,
        "current_opponent_ship_id": 30,
        "from_vcr_id": 100,
        "to_vcr_id": 101,
        "current_side": "right",
    }


def test_o_layer_wrapper_is_main_guarded_and_discovery_only() -> None:
    root = Path(__file__).resolve().parents[1]
    wrapper = (
        root / "tools/run-public-capture-o-layer-discovery-with-evidence.sh"
    ).read_text(encoding="utf-8")
    runner = (
        root / "tools/run-public-capture-o-layer-discovery.sh"
    ).read_text(encoding="utf-8")

    assert 'PUBLIC_CAPTURE_O_LAYER_ALLOW_NON_MAIN="${PUBLIC_CAPTURE_O_LAYER_ALLOW_NON_MAIN:-0}"' in wrapper
    assert '"$SOURCE_BRANCH" != "main"' in wrapper
    assert "exit 64" in wrapper
    assert "discovery-capture-side.json" in runner
    assert "heldout" not in runner
    assert "--partition all" not in runner

def test_probe_supports_single_game_process_isolation() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = (
        root / "tools/diagnostics/combat_public_capture_o_layer_probe.py"
    ).read_text(encoding="utf-8")
    runner = (
        root / "tools/run-public-capture-o-layer-discovery.sh"
    ).read_text(encoding="utf-8")

    assert 'parser.add_argument("--game-id", type=int)' in probe
    assert "full_scan_ids" in probe
    assert "probe_game_ids" in probe
    assert '--game-id "$game_id"' in runner
    assert "o-layer-parts" in runner
    assert "combat_public_capture_o_layer_merge.py" in runner
    assert "compose.corpus-db.yaml" in runner
    assert "--corpus-db-root /corpus-db" in runner
    assert "--archive-dir" not in runner
    assert "--appearance-cache-dir" not in runner
    assert "_targeted_db_context" in probe
    assert "zipfile.ZipFile" not in probe

def test_pseudo_seen_from_appearances_reconstructs_compact_vcr() -> None:
    appearances = [
        {
            "game_id": 42,
            "turn": 7,
            "vcr_id": 9,
            "position": [100, 200],
            "side": "left",
            "ship_id": 11,
            "hull_id": 22,
            "owner_id": 1,
        },
        {
            "game_id": 42,
            "turn": 7,
            "vcr_id": 9,
            "position": [100, 200],
            "side": "right",
            "ship_id": 33,
            "hull_id": 44,
            "owner_id": 2,
        },
    ]
    seen = _pseudo_seen_from_appearances(
        appearances=appearances,
        game_id=42,
        battle_turns={7},
    )
    _digest, vcr = seen[(42, 7, 9)]
    assert vcr["left"]["objectid"] == 11
    assert vcr["right"]["objectid"] == 33
    assert vcr["leftownerid"] == 1
    assert vcr["rightownerid"] == 2
    assert (vcr["x"], vcr["y"]) == (100, 200)

def test_probe_reports_split_candidate_and_dependency_audit() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = (
        root / "tools/diagnostics/combat_public_capture_o_layer_probe.py"
    ).read_text(encoding="utf-8")

    assert '"active_dependency"' in probe
    assert '"factual_opponent_active"' in probe
    assert '"factual_opponent_strict_permission"' in probe
    assert '"split_candidate"' in probe
    assert '"o_reachable_sticky_capture_side"' in probe
    assert '"o_not_reachable_neutral_fresh_fc"' in probe

def test_probe_classifies_dependency_qualified_subset() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = (
        root / "tools/diagnostics/combat_public_capture_o_layer_probe.py"
    ).read_text(encoding="utf-8")

    assert '"resolved_dependency:qualified"' in probe
    assert '"resolved_dependency:blocked"' in probe
    assert '"split_candidate_exact:"' in probe
    assert '"qualified" if dependency_qualified else "blocked"' in probe
    assert '"factual_opponent_site_predicted"' in probe
    assert '"factual_opponent_history_anchored"' in probe
    assert '"factual_opponent_removed_before_next"' in probe
    assert '"factual_opponent_owner_changed_before_next"' in probe
    assert "blocked_dependency" in probe

def test_identity_anchor_injects_only_factual_opponent_eligibility() -> None:
    active = {
        "active_ship_ids": [10],
        "candidates": [
            {
                "ship_id": 10,
                "requests_new_owner": True,
                "strict_permission": True,
            }
        ],
        "status": "resolved",
    }
    anchored = _identity_anchor_factual_opponent(
        active_result=active,
        factual_opponent_id=20,
    )

    assert anchored["active_ship_ids"] == [10, 20]
    factual = next(
        row for row in anchored["candidates"] if row["ship_id"] == 20
    )
    assert factual["requests_new_owner"] is True
    assert factual["strict_permission"] is True
    assert factual["identity_anchored_from_factual_nplus1"] is True
    assert "side" not in factual
    assert active["active_ship_ids"] == [10]




def test_probe_has_separate_independent_postheldout_mode() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (
        root / "tools/diagnostics/combat_public_capture_o_layer_probe.py"
    ).read_text(encoding="utf-8")

    assert 'choices=("discovery", "heldout", "independent", "prospective")' in source
    assert 'capture_partition = "all" if partition == "independent"' in source
    assert '"INDEPENDENT_VALIDATION_POSTHELDOUT_CANDIDATE"' in source
    assert '"postheldout_candidate_validation"' in source
    assert '"postheldout_candidate_rows"' in source
    assert '"postheldout_candidate_exact"' in source
    assert '"postheldout_candidate_mismatch"' in source
    assert '"postheldout_candidate_unresolved"' in source
    assert "evaluate_frozen_postheldout_candidate" in source
