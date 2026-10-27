"""Real published VCR missingness joint frozen projection and hostile inputs."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.vcr_missingness_joint_v2_real_readout import (
    EvidenceReviewAbstain, readout_real_vcr_missingness,
)

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
V6 = ROOT / "tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json"
V1 = ROOT / "tests/fixtures/public100_baseline68_vcr_same_turn_v1_safe_projection.json"
JOINT = ROOT / "tests/fixtures/public100_baseline68_vcr_missingness_joint_v2_real_safe_projection.json"
SCORE = ROOT / "validation/research/public100-baseline68-vcr-missingness-joint-v2-real-source-scorecard.json"
CLI = ROOT / "tools/diagnostics/review_vcr_missingness_joint_v2_real.py"


def inputs():
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in (V5,V6,V1,JOINT)]


def counts(d):
    return d["source"]["sample"]["vcr_same_turn_missingness_joint_not_host_phase"]


def test_exact_real_successful_2026_10_27_joint_source_replay():
    result = readout_real_vcr_missingness(*inputs())
    assert result == json.loads(SCORE.read_text(encoding="utf-8"))
    c = result["selected_archive_group_and_row_missingness_not_host_battles"]
    assert c["multi_rng_only_groups"] == 59
    assert c["multi_rng_missing_archive_rows"] == 118
    assert c["singleton_rng_only_groups"] == 205
    assert c["singleton_rng_missing_archive_rows"] == 205
    assert c["singleton_owner_only_groups"] == 1
    assert c["multi_owner_pair_untyped_archive_rows"] == 0
    assert c["singleton_complete_groups"] == 31914
    assert c["multi_complete_groups"] == 6047
    assert c["all_rng_missing_archive_rows"] == 323
    assert c["catalog_missing_archive_rows"] == 0
    assert all(value is False for key,value in result["inference_gates"].items()
               if key != "selected_source_missingness_intersection_known")


@pytest.mark.parametrize("mutate", [
    lambda x: x["runtime"].update(source_commit="0"*40),
    lambda x: x["runtime"].update(run_id="untrusted"),
    lambda x: x["runtime"].update(exit_code=125),
    lambda x: x["runtime"].update(source_dirty=True),
    lambda x: x["runtime"].update(build_status="ABSTAIN_BUILD_FAILED"),
    lambda x: x["runtime"].update(pytest_cases=3883),
    lambda x: x["runtime"].update(pytest_skipped=0),
    lambda x: x["runtime"].update(heldout32_entities_read=True),
    lambda x: x["runtime"].update(host_diff_verified=True),
    lambda x: x["runtime"].update(generation_read_only=False),
    lambda x: x["source"]["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda x: x["source"]["sample"]["vcr_same_turn_perspective_consensus_not_host_phase"].update(multi_perspective_groups=6105),
    lambda x: x["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["vcrs"].update(before_id_rows=21919),
    lambda x: counts(x).update(multi_rng_only_groups=58),
    lambda x: counts(x).update(multi_missing_rng_rows=117),
    lambda x: counts(x).update(single_rng_only_groups=206),
    lambda x: counts(x).update(single_missing_rng_rows=206),
    lambda x: counts(x).update(single_owner_only_groups=0),
    lambda x: counts(x).update(multi_complete_groups=6048),
    lambda x: counts(x).update(single_missing_catalog_rows=True),
    lambda x: counts(x).update(private_game_or_player_ID=8248),
    lambda x: counts(x).pop("multi_complete_groups"),
    lambda x: x.update(raw_untrusted_orders="do not echo"),
])
def test_freeze_source_runtime_joint_tamper_abstains(mutate):
    v5,v6,v1,j=inputs()
    mutate(j)
    with pytest.raises(EvidenceReviewAbstain):
        readout_real_vcr_missingness(v5,v6,v1,j)


def test_prior_v1_projection_tamper_fails_even_if_new_report_remains():
    v5,v6,v1,j=inputs()
    v1["runtime"]["exit_code"]=2
    with pytest.raises(EvidenceReviewAbstain):
        readout_real_vcr_missingness(v5,v6,v1,j)


def test_isolated_stdlib_exact_scorecard_and_overwrite_refusal(tmp_path):
    dest=tmp_path/"safe.json"
    call=[sys.executable,"-I","-S",str(CLI),
          "--v5",str(V5),"--v6",str(V6),
          "--v1",str(V1),"--joint",str(JOINT),
          "--output",str(dest)]
    out=subprocess.run(call,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert out.returncode==0,out.stdout+out.stderr
    assert json.loads(dest.read_text())==json.loads(SCORE.read_text())
    assert "multi_rng_only_groups=59" in out.stdout
    assert "multi_rng_missing_archive_rows=118" in out.stdout
    assert "host_diff_verified=false" in out.stdout
    repeat=subprocess.run(call,cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert repeat.returncode==2
    assert repeat.stdout.strip()=="ABSTAIN_OUTPUT_EXISTS_OR_INPUT_OVERWRITE"


def test_poisoned_input_never_echoed_or_exported(tmp_path):
    v5,v6,v1,j=inputs()
    counts(j)["secret_host_identity_711179223"]=55
    bad=tmp_path/"bad.json"
    bad.write_text(json.dumps(j),encoding="utf-8")
    out=tmp_path/"never.json"
    call=[sys.executable,"-I","-S",str(CLI),"--v5",str(V5),
          "--v6",str(V6),"--v1",str(V1),"--joint",str(bad),"--output",str(out)]
    result=subprocess.run(call,text=True,capture_output=True,timeout=20,cwd=tmp_path)
    assert result.returncode==2
    assert result.stdout.strip()=="ABSTAIN_REAL_VCR_MISSINGNESS_SOURCE"
    assert "711179223" not in result.stdout+result.stderr
    assert not out.exists()


def test_real_fixture_contains_strict_32_numeric_counters_and_only_known_sources():
    v5,v6,v1,j=inputs()
    d=counts(j)
    assert len(d)==32
    assert all(type(n) is int and n>=0 for n in d.values())
    assert sum(d[f"multi_{reason}_groups"] for reason in (
        "complete","rng_only","owner_only","catalog_only",
        "rng_owner","rng_catalog","owner_catalog","rng_owner_catalog"))==6106
    assert d["multi_rng_only_groups"]==59
    assert d["multi_missing_rng_rows"]==118
    assert not any("hash" in key or "game_id" in key for key in d)
    assert j["source"]["baseline_sample_allowlist"]["heldout_entity_sampling"] is False
