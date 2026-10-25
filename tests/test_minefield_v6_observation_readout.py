"""Real sanitized v6 counts and synthetic adversarial replay; never DB/Host."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.minefield_v6_observation_readout import (
    EvidenceReviewAbstain, JOINT, RUNTIME, readout_v6_joint,
)

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
V6 = ROOT / "tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json"
SCORECARD = ROOT / "validation/research/public100-baseline68-minefield-v6-joint-observations.v1.json"
CLI = ROOT / "tools/diagnostics/review_minefield_v6_observations.py"

def load():
    return json.loads(V5.read_text()), json.loads(V6.read_text())

def test_exact_actual_v6_runtime_source_result_replays_committed_scorecard():
    prior, newer = load()
    scorecard = readout_v6_joint(prior, newer)
    assert scorecard == json.loads(SCORECARD.read_text())
    assert scorecard["status"] == "PASS_FROZEN_COHORT_JOINT_OBSERVATION_NOT_CAUSAL"
    summary = scorecard["minefield_observation_occurrences_not_unique_events"]
    assert summary["same_id_across_archives"] == 887224
    assert summary["fresh_owned_both_archives"] == 138864
    assert summary["fresh_owned_stable_center_numeric_units_joint"] == 138833
    assert summary["fresh_owned_excluded_from_stable_numeric_joint"] == 31
    assert summary["joint_units_decreased"] == 134693
    assert summary["joint_units_increased"] == 3746
    assert summary["joint_units_unchanged"] == 394
    assert summary["joint_units_changed"] == 138439
    assert summary["previously_unknown_fresh_and_stable_changed_intersection_exact"] == 138439
    assert summary["v5_marginal_intersection_lower_bound"] == 0
    assert summary["v5_marginal_intersection_upper_bound"] == 138864
    assert scorecard["provenance"]["v5_marginals_replayed_identically"] is True
    assert all(v is False for k,v in scorecard["inference_gates"].items()
               if k != "same_row_fresh_owned_and_units_joint_observed")

@pytest.mark.parametrize("action", [
    lambda p: p["runtime"].update(exit_code=2),
    lambda p: p["runtime"].update(source_commit="0"*40),
    lambda p: p["runtime"].update(stage_economy_status="FAILED_OR_UNVALIDATED"),
    lambda p: p["runtime"].update(heldout32_entities_read=True),
    lambda p: p["runtime"].update(host_diff_verified=True),
    lambda p: p["source"]["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda p: p["source"]["generation"].update(read_only=False),
    lambda p: p["source"]["evidence_limits"].update(archive_identity_or_mine_unit_changes_prove_host_phase=True),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_seen_in_both_archives=887225),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"].update(same_id_owner_changed_not_host_capture=6892),
    lambda p: p["source"]["sample"]["sample_status_counts"].update(SAMPLED_PAIR_PAYLOAD_IDENTITY_VALID=8549),
])
def test_run_attestation_and_every_earlier_marginal_are_pinned(action):
    old, current = load()
    action(current)
    with pytest.raises(EvidenceReviewAbstain):
        readout_v6_joint(old,current)

@pytest.mark.parametrize("action", [
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_fresh_own_center_stable_numeric_units_joint=138834),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_fresh_own_center_stable_units_changed_joint_not_causal=138440),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_fresh_own_center_stable_units_increased_joint_not_causal=True),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(same_id_fresh_own_center_stable_units_decreased_joint_not_causal=-1),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].pop(JOINT[0]),
    lambda p: p["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(private_mine_id=9876543),
    lambda p: p.update(secret_raw_mine_record={"id":9876543}),
])
def test_joint_conservation_missing_or_injected_raw_counter_abstains(action):
    old, current = load()
    action(current)
    with pytest.raises(EvidenceReviewAbstain):
        readout_v6_joint(old,current)

def test_poisoned_original_v5_reference_is_rejected_not_used_as_authority():
    old,current=load()
    old["generation"]["verified_sha256"]="0"*64
    with pytest.raises(EvidenceReviewAbstain):
        readout_v6_joint(old,current)

def test_offline_stdlib_cli_replays_without_site_packages_and_never_overwrites(tmp_path):
    output=tmp_path/"review.json"
    cmd=[sys.executable,"-I","-S",str(CLI),"--v5",str(V5),"--v6",str(V6),"--output",str(output)]
    first=subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert first.returncode==0, first.stdout+first.stderr
    assert json.loads(output.read_text())==json.loads(SCORECARD.read_text())
    assert "host_diff_verified=false" in first.stdout
    second=subprocess.run(cmd,cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert second.returncode==2
    assert "ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE" in second.stdout

def test_cli_malicious_input_never_echoes_private_payload_or_produces_scorecard(tmp_path):
    old,current=load()
    current["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]["sensitive_game_id"]=123456789
    path=tmp_path/"bad.json"
    path.write_text(json.dumps(current))
    output=tmp_path/"not-created.json"
    cmd=[sys.executable,"-I","-S",str(CLI),"--v5",str(V5),"--v6",str(path),"--output",str(output)]
    r=subprocess.run(cmd,cwd=tmp_path,capture_output=True,text=True,timeout=30)
    assert r.returncode==2
    assert r.stdout.strip()=="ABSTAIN_V6_SOURCE_READOUT"
    assert "123456789" not in r.stdout+r.stderr
    assert not output.exists()
