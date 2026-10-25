"""Replay authentic sanitized starbase observations; adversarial provenance tests."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.starbase_link_v1_observation_readout import (
    EvidenceReviewAbstain, LINK_FIELDS, readout_starbase_link,
)

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
V6 = ROOT / "tests/fixtures/public100_baseline68_v6_mine_joint_safe_projection.json"
BASE = ROOT / "tests/fixtures/public100_baseline68_starbase_link_v1_safe_projection.json"
SCORE = ROOT / "validation/research/public100-baseline68-starbase-link-v1-source-scorecard.json"
CLI = ROOT / "tools/diagnostics/review_starbase_link_v1_observations.py"


def payloads():
    return [json.loads(path.read_text(encoding="utf-8")) for path in (V5,V6,BASE)]


def test_real_starbase_public_runtime_replays_exact_scorecard():
    report=readout_starbase_link(*payloads())
    assert report==json.loads(SCORE.read_text(encoding="utf-8"))
    c=report["starbase_observer_archive_occurrences_not_unique_events"]
    assert c["same_id_both_archives"]==346222
    assert c["planet_link_own_current_both_archives"]==138711
    assert c["base_info_current_both_archives"]==138708
    assert c["linked_planet_but_base_infoturn_stale_or_invalid_any"]==3
    assert c["linked_planet_but_base_infoturn_missing_any"]==0
    assert c["own_current_planet_link_unqualified"]==207511
    assert c["other_ambiguous_anchor_or_conflicting_owner"]==0
    assert all(v is False for k,v in report["inference_gates"].items()
               if k != "fresh_own_planet_linked_base_observed")


@pytest.mark.parametrize("mutate",[
    lambda v:v["runtime"].update(source_commit="0"*40),
    lambda v:v["runtime"].update(exit_code=2),
    lambda v:v["runtime"].update(host_diff_verified=True),
    lambda v:v["runtime"].update(heldout32_entities_read=True),
    lambda v:v["runtime"].update(economy_status="FAILED_OR_UNVALIDATED"),
    lambda v:v["runtime"].update( pytest_cases=0),
    lambda v:v["source"]["metadata"].update(metadata_frozen_selection_sha256="0"*64),
    lambda v:v["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["ships"].update(
        same_id_owner_changed_not_host_capture=6892),
    lambda v:v["source"]["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"].update(
        same_id_fresh_own_center_stable_units_decreased_joint_not_causal=134694),
    lambda v:v["source"]["generation"].update(read_only=False),
    lambda v:v["source"]["sample"]["starbase_planet_archive_link_not_host_phase"].update(
        same_id_planet_linked_base_current_both_archives=138709),
    lambda v:v["source"]["sample"]["starbase_planet_archive_link_not_host_phase"].update(
        same_id_planet_linked_current_own_both_archives=138712),
    lambda v:v["source"]["sample"]["starbase_planet_archive_link_not_host_phase"].update(
        same_id_planet_linked_base_infoturn_missing_any=True),
    lambda v:v["source"]["sample"]["starbase_planet_archive_link_not_host_phase"].update(
        private_planet_id=55555),
    lambda v:v.update(private_order="sensitive"),
    lambda v:v["source"]["sample"].pop("starbase_planet_archive_link_not_host_phase"),
])
def test_malformed_or_mutated_source_rejected(mutate):
    v5,v6,base=payloads()
    mutate(base)
    with pytest.raises(EvidenceReviewAbstain):
        readout_starbase_link(v5,v6,base)


def test_mutated_earlier_frozen_reference_is_not_accepted():
    v5,v6,base=payloads()
    v6["runtime"]["exit_code"]=2
    with pytest.raises(EvidenceReviewAbstain):
        readout_starbase_link(v5,v6,base)


def test_offline_python_stdlib_cli_exact_and_no_overwrite(tmp_path):
    out=tmp_path/"safe-scorecard.json"
    command=[sys.executable,"-I","-S",str(CLI),
             "--v5",str(V5),"--v6",str(V6),"--starbase",str(BASE),
             "--output",str(out)]
    r=subprocess.run(command,cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert r.returncode==0,r.stdout+r.stderr
    assert json.loads(out.read_text())==json.loads(SCORE.read_text())
    assert "host_diff_verified=false" in r.stdout
    r=subprocess.run(command,cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert r.returncode==2
    assert r.stdout.strip()=="ABSTAIN_OUTPUT_EXISTS_OR_SOURCE_OVERWRITE"


def test_untrusted_raw_counter_cli_abstains_without_echoing_or_artifact(tmp_path):
    v5,v6,base=payloads()
    base["source"]["sample"]["starbase_planet_archive_link_not_host_phase"]["raw_private_planet_id"]=888889
    path=tmp_path/"malicious.json";path.write_text(json.dumps(base))
    output=tmp_path/"unsafe.json"
    r=subprocess.run([sys.executable,"-I","-S",str(CLI),
        "--v5",str(V5),"--v6",str(V6),"--starbase",str(path),"--output",str(output)],
        cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert r.returncode==2
    assert r.stdout.strip()=="ABSTAIN_STARBASE_SOURCE_READOUT"
    assert "888889" not in r.stdout+r.stderr
    assert not output.exists()
