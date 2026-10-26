"""Actual sanitized same-turn source replay; adversarial tamper and isolation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.vcr_same_turn_v1_observation_readout import (
    EvidenceReviewAbstain, FIELDS, readout_vcr_same_turn,
)

ROOT=Path(__file__).resolve().parents[1]
V5=ROOT/"tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
V6=ROOT/"tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json"
SAME=ROOT/"tests/fixtures/public100_baseline68_vcr_same_turn_v1_safe_projection.json"
SCORE=ROOT/"validation/research/public100-baseline68-vcr-same-turn-v1-source-scorecard.json"
CLI=ROOT/"tools/diagnostics/review_vcr_same_turn_v1_observations.py"

def sources():
    return [json.loads(path.read_text(encoding="utf-8")) for path in (V5,V6,SAME)]

def new_counts(v):
    return v["source"]["sample"]["vcr_same_turn_perspective_consensus_not_host_phase"]

def test_true_successful_runtime_is_replayable_and_not_host_causal():
    outcome=readout_vcr_same_turn(*sources())
    assert outcome==json.loads(SCORE.read_text(encoding="utf-8"))
    c=outcome["selected_same_turn_source_groups_not_host_battles"]
    assert c["distinct_archive_members"]==17100
    assert c["source_vcr_observation_rows"]==44332
    assert c["same_turn_group_count"]==38226
    assert c["single_observer_groups"]==32120
    assert c["multi_observer_groups"]==6106
    assert c["multi_observer_source_occurrences"]==12212
    assert c["strict_complete_equal"]==6047
    assert c["strict_inputs_incomplete"]==59
    assert c["strict_complete_different"]==0
    assert c["source_rows_missing_explicit_rng"]==323
    assert c["source_rows_missing_owner_pair"]==1
    assert c["source_rows_missing_typed_weapon_catalog"]==0
    assert c["full_adapter_signature_equal_even_if_incomplete"]==6106
    assert all(not value for key,value in outcome["inference_gates"].items()
               if key!="same_turn_multi_perspective_source_consensus_observed")


@pytest.mark.parametrize("mutator", [
    lambda x:x["runtime"].update(source_commit="0"*40),
    lambda x:x["runtime"].update(run_id="historical-unverified"),
    lambda x:x["runtime"].update(exit_code=125),
    lambda x:x["runtime"].update(build_status="ABSTAIN_BUILD_FAILED"),
    lambda x:x["runtime"].update(pytest_cases=0),
    lambda x:x["runtime"].update(pytest_skipped=0),
    lambda x:x["runtime"].update(heldout32_entities_read=True),
    lambda x:x["runtime"].update(host_diff_verified=True),
    lambda x:x["runtime"].update(generation_read_only=False),
    lambda x:x["source"]["generation"].update(read_only=False),
    lambda x:x["source"]["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda x:x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"].update(before_id_rows=21919),
    lambda x:x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"].update(same_id_seen_in_both_archives=916903),
    lambda x:new_counts(x).update(multi_perspective_groups=6107),
    lambda x:new_counts(x).update(multi_perspective_strict_complete_inputs_equal=6106),
    lambda x:new_counts(x).update(multi_perspective_complete_adapter_signature_equal=6105),
    lambda x:new_counts(x).update(multi_perspective_strict_inputs_incomplete=58),
    lambda x:new_counts(x).update(unique_frozen_archive_members_examined=17101),
    lambda x:new_counts(x).update(vcr_rows_missing_explicit_combat_rng=True),
    lambda x:new_counts(x).update(vcr_rows_missing_typed_owner_pair="1"),
    lambda x:new_counts(x).update(raw_private_game_id=923),
    lambda x:new_counts(x).pop(FIELDS[0]),
    lambda x:x.update(unknown_raw_host_orders="sensitive"),
])
def test_strict_frozen_full_history_runtime_partition_and_privacy_tamper(mutator):
    v5,v6,same=sources()
    mutator(same)
    with pytest.raises(EvidenceReviewAbstain):
        readout_vcr_same_turn(v5,v6,same)


def test_old_v6_invalid_even_if_new_source_unchanged():
    v5,v6,same=sources()
    v6["runtime"]["exit_code"]=3
    with pytest.raises(EvidenceReviewAbstain):
        readout_vcr_same_turn(v5,v6,same)


def test_isolated_stdlib_cli_exact_reference_no_overwrite(tmp_path):
    target=tmp_path/"result.json"
    args=[sys.executable,"-I","-S",str(CLI),
          "--v5",str(V5),"--v6",str(V6),"--same-turn",str(SAME),
          "--output",str(target)]
    r=subprocess.run(args,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert r.returncode==0, r.stdout+r.stderr
    assert json.loads(target.read_text())==json.loads(SCORE.read_text())
    assert "multi_observer_groups=6106" in r.stdout
    assert "strict_complete_equal=6047" in r.stdout
    assert "host_diff_verified=false" in r.stdout
    again=subprocess.run(args,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert again.returncode==2
    assert again.stdout.strip()=="ABSTAIN_OUTPUT_ALREADY_EXISTS_OR_SOURCE_OVERWRITE"


def test_cli_cannot_export_private_source_id_or_create_scorecard(tmp_path):
    v5,v6,source=sources()
    new_counts(source)["private_secret_4904799"]=123
    local=tmp_path/"private.json";local.write_text(json.dumps(source),encoding="utf-8")
    dest=tmp_path/"not-created.json"
    args=[sys.executable,"-I","-S",str(CLI),"--v5",str(V5),
          "--v6",str(V6),"--same-turn",str(local),"--output",str(dest)]
    r=subprocess.run(args,cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert r.returncode==2
    assert r.stdout.strip()=="ABSTAIN_VCR_SAME_TURN_READOUT"
    assert "4904799" not in r.stdout+r.stderr
    assert not dest.exists()


def test_fixture_only_allows_fixed_keys_no_raw_vcr_or_hash():
    v5,v6,source=sources()
    c=new_counts(source)
    assert set(c)==set(FIELDS)
    assert len(c)==31
    assert all(type(value) is int and value>=0 for value in c.values())
    assert all("hash" not in key and "seed" not in key
               and "game_id" not in key for key in c)
    assert source["source"]["baseline_sample_allowlist"]["heldout_entity_sampling"] is False
    assert not any("source_member_name" in str(key) for key in source["source"])
