"""Adversarial review of already sanitized v5 aggregates: zero corpus access."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.nonplanet_v5_evidence_review import (
    EvidenceReviewAbstain,
    review_published_v5,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
SCORECARD = ROOT / "validation/research/public100-baseline68-nonplanet-v5-source-readiness.v1.json"


def load():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_real_published_aggregate_fixture_derives_exact_committed_review():
    assert review_published_v5(load()) == json.loads(
        SCORECARD.read_text(encoding="utf-8"))
    result = review_published_v5(load())
    assert result["status"] == "PASS_SOURCE_READINESS_CLASSIFICATION_NOT_HOST_CAUSAL"
    assert result["provenance"]["observational_archive_pairs"] == 8550
    assert result["provenance"]["sealed_games_entity_scope"] == 0
    assert not result["actual_host_phase_receipts_authenticated"]
    assert not result["accepted_host_orders_authenticated"]
    assert not result["host_diff_verified"]
    mine = result["sections"]["minefields"]
    assert mine["matching_observer_archive_id_occurrences"] == 887224
    assert mine["current_own_observer_archive_matches"] == 138864
    assert mine["stable_owner_center_and_changed_units_archive_occurrences"] == 536703
    assert mine["joint_fresh_and_stable_changed_lower_bound"] == 0
    assert mine["joint_fresh_and_stable_changed_upper_bound"] == 138864
    assert mine["exact_fresh_and_stable_changed_joint_observations_known"] is False
    assert result["sections"]["vcrs"]["source_state"] == "ABSTAIN_NO_CROSS_TURN_ID_CONTINUITY"
    assert result["sections"]["starbases"]["source_state"] == "ABSTAIN_OWNER_PROVENANCE_UNTYPED"
    assert result["sections"]["ionstorms"]["source_state"] == "ID_ONLY_STORM_NO_OWNER_CAUSALITY"
    assert all(not x["independent_host_mechanism_verified"]
               for x in result["sections"].values())


@pytest.mark.parametrize("tamper", [
    lambda p: p["generation"].update(read_only=False),
    lambda p: p["generation"].update(verified_sha256="0"*64),
    lambda p: p["baseline_sample_allowlist"].update(allowed_game_count=100),
    lambda p: p["baseline_sample_allowlist"].update(heldout_entity_sampling=True),
    lambda p: p["baseline_sample_allowlist"].update(manifest_sha256="0"*64),
    lambda p: p["metadata"].update(metadata_frozen_sample_pairs=8551),
    lambda p: p["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda p: p["metadata"].update(selection_frozen_before_entity_reconstruction=False),
    lambda p: p["sample"]["sample_status_counts"].update(SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID=8549),
    lambda p: p["evidence_limits"].update(archive_identity_or_mine_unit_changes_prove_host_phase=True),
])
def test_metadata_or_provenance_tampering_atomically_abstains(tamper):
    p = load()
    tamper(p)
    with pytest.raises(EvidenceReviewAbstain):
        review_published_v5(p)


def test_mine_counters_conservation_fail_closed_on_inflation():
    p = load()
    p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]["same_id_seen_in_both_archives"] += 1
    with pytest.raises(EvidenceReviewAbstain, match="CONSERVATION"):
        review_published_v5(p)


def test_changed_units_cannot_exceed_comparable_units():
    p = load()
    mine = p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
    mine["same_id_integer_units_changed_not_host_attribution"] = 999999
    with pytest.raises(EvidenceReviewAbstain, match="MINE_UNITS"):
        review_published_v5(p)


def test_injected_secret_id_and_bad_counts_never_become_public_summary():
    p = load()
    p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"]["private_player_id"] = 112233
    with pytest.raises(EvidenceReviewAbstain, match="UNEXPECTED_SOURCE_COUNTER"):
        review_published_v5(p)
    p = load()
    p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"]["same_id_owner_unchanged"] = True
    with pytest.raises(EvidenceReviewAbstain, match="INVALID_COUNTER"):
        review_published_v5(p)


def test_source_sections_missing_fails_atomically():
    p = load()
    del p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"]
    with pytest.raises(EvidenceReviewAbstain, match="UNEXPECTED_SOURCE_SECTIONS"):
        review_published_v5(p)


def test_cli_rebuilds_same_review_without_opening_corpus(tmp_path):
    output = tmp_path / "aggregate-review.json"
    script = ROOT / "tools/diagnostics/review_nonplanet_v5_evidence.py"
    command = [
        sys.executable, str(script), "--input", str(SOURCE), "--output", str(output)
    ]
    first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert first.returncode == 0, first.stdout + first.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        SCORECARD.read_text(encoding="utf-8"))
    # Never silently overwrite an existing report, especially when input changed.
    second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert second.returncode == 2
    assert "ABSTAIN_OUTPUT_EXISTS" in second.stdout


def test_private_values_in_unused_fields_do_not_leak_into_safe_scorecard():
    p = load()
    p["private_source"] = {"secret_game_id": 9876543}
    score = review_published_v5(p)
    assert "9876543" not in json.dumps(score)
    assert "secret_game_id" not in json.dumps(score)
