"""Frozen, traceable PPQ public observational research closure.

Only a privacy-minimal summary of separately published authentic runtime
evidence is committed. This test guards consistency of its **descriptive**
counts and permanent lack of independent Host causal verification; it does
not treat archived correlations as confirmed ship builds.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FILE = (
    Path(__file__).resolve().parents[1]
    / "validation/research/pq-public-control12-observational-closure.v1.json"
)


def test_frozen_public_ppq_observational_closure_is_internally_consistent():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    assert data["schema"] == "planets-lab.pq-public-control12-observational-closure.v1"
    assert data["evidence_level"] == "CORPUS_OBSERVED"
    assert data["status"] == "DESCRIPTIVE_PUBLIC_PPQ_OBSERVATION_CLOSED_NOT_HOST_CAUSAL"
    scope = data["scope"]
    assert scope["games"] == len(data["eligible_public_ppq_games"]) == 6
    assert data["eligible_public_ppq_games"] == [
        591478, 620917, 621253, 621896, 680435, 680910,
    ]
    assert scope["player_slot"] == 1
    assert scope["max_archive_pairs_per_game"] == 48
    assert scope["max_admitted_windows_per_game"] == 8
    assert scope["archive_adjacent_pairs_checked"] == (
        scope["embedded_consecutive_qualified_windows"]
        + scope["refused_repeated_embedded_turn"]
        + scope["refused_skipped_forward_embedded_turn"]
    )
    assert scope["embedded_consecutive_qualified_windows"] == 48

    appearances = data["appearance"]
    assert sum(appearances["by_game"].values()) == (
        appearances["newly_visible_owned_fresh_ship_identity_window_events"]
    ) == 22
    assert len(appearances["by_game"]) == scope["games"]
    assert set(map(int, appearances["by_game"])) == set(data["eligible_public_ppq_games"])
    assert (
        appearances["eligible_single_unique_prior_base"]
        + appearances["ambiguous_prior_base_abstentions"]
        == appearances["newly_visible_owned_fresh_ship_identity_window_events"]
    )
    assert appearances["prior_base_hull_engine_matches"] == (
        appearances["eligible_single_unique_prior_base"]
    ) == 17

    paired = data["paired_same_window"]
    assert (
        paired["new_ship_full_base_match_no_persistent_ship_matches"]
        + paired["new_ship_full_base_match_some_persistent_ships_match"]
        == appearances["eligible_single_unique_prior_base"]
    )
    assert paired["new_ship_or_prior_base_not_comparable"] == (
        appearances["ambiguous_prior_base_abstentions"]
    )
    assert paired["new_ship_full_base_template_mismatches_in_qualified_windows"] == 0

    old = data["persistent_ship_reference"]
    matched, compared = 0, 0
    for key in ("appearance_windows", "nonappearance_windows"):
        segment = old[key]
        assert segment["qualifying_windows"] <= segment["windows"]
        assert segment["ship_window_template_matches"] + segment[
            "ship_window_template_mismatches"
        ] == segment["typed_ship_window_comparisons"]
        matched += segment["ship_window_template_matches"]
        compared += segment["typed_ship_window_comparisons"]
    assert (
        old["appearance_windows"]["windows"]
        + old["nonappearance_windows"]["windows"]
        == scope["embedded_consecutive_qualified_windows"]
    )
    assert old["all_typed_ship_window_matches"] == matched == 12
    assert old["all_typed_ship_window_comparisons"] == compared == 97
    assert old["observations_not_independent"] is True
    assert old["distinct_ships_not_counted"] is True

    assert sum(
        data["prioritypoints_trend_in_appearance_windows"][k]
        for k in ("increased", "unchanged", "decreased")
    ) == appearances["newly_visible_owned_fresh_ship_identity_window_events"]
    assert data["prioritypoints_trend_in_appearance_windows"][
        "pp_spending_not_attributable"
    ] is True


def test_public_closure_cannot_upgrade_causal_or_private_host_evidence():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    provenance = data["evidence_provenance"]
    assert re.fullmatch("[0-9a-f]{40}", provenance["source_commit"])
    assert provenance["source_commit"] == "a0f7ca22ec0710a2c7fef030bf467ad2e1865ce5"
    assert provenance["evidence_branch"] == "runtime-logs"
    assert provenance["run_path"].startswith(
        "runtime-logs/pq-paired-template-specificity-control12-p1-first48-max8/"
    )
    assert provenance["report_relative_path"] == (
        "artifacts/pq/surveys/control12-ppq-p1-first48-max8.json"
    )
    assert provenance["metadata_exit_code"] == 0
    assert provenance["metadata_interrupted_signal"] is None
    assert provenance["metadata_missing_artifacts"] == []
    assert data["not_verified"] and all(
        flag is False for flag in data["not_verified"].values()
    )
    assert data["privacy"] and all(
        flag is False for flag in data["privacy"].values()
    )
    next_phase = data["next_phase"]
    assert next_phase["state"] == "PARKED_EXTERNAL_EVIDENCE_REQUIRED"
    assert next_phase["issue_url"] == (
        "https://github.com/Numillyash/planets-lab/issues/247"
    )
    assert next_phase["no_additional_archival_replay_required"] is True
    assert len(next_phase["reopen_requires"]) >= 5
    assert "heldout32" not in data["scoped_cohort"]
    assert "secret" not in FILE.read_text(encoding="utf-8").lower()
