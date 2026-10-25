"""VCR source-only temporal/participant readiness, without Host combat oracle."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.m2_economy_coverage import Member, analyze_corpus_coverage, census_members
from planets_lab.corpus.vcr_archive_temporal_readiness import profile_vcr_archive_pair
from tools.diagnostics.validate_vcr_archive_temporal_readiness_v1 import (
    SCHEMA_FIELDS, validate_counts,
)

ROOT=Path(__file__).resolve().parents[1]

def row(vid, turn, left=10,right=20, owners=True):
    r={"id":vid,"turn":turn,"left":{"objectid":left},"right":{"objectid":right}}
    if owners:
        r.update(leftownerid=1,rightownerid=2)
    return r

def snap(turn,rows):
    return {"game":{"id":42,"turn":turn},"player":{"id":1},
            "planets":[],"ships":[],"starbases":[],"minefields":[],"ionstorms":[],
            "vcrs":rows}

def profile(b,a):
    return profile_vcr_archive_pair(b,a,before_turn=10,after_turn=11)

def test_exact_turn_and_participants_is_not_generic_cross_turn_identity():
    b=snap(10,[row(7,10),row(8,9,owners=False),row(9,12,left=None)])
    a=snap(11,[row(10,11),row(11,None,right=0),row(12,10)])
    c=profile(b,a)
    assert c["qualified_archive_pairs"]==1
    assert c["same_id_across_adjacent_archives_not_battle_link"]==0
    assert c["before_vcr_rows"]==3 and c["after_vcr_rows"]==3
    assert c["before_turn_exact"]==1
    assert c["before_turn_earlier"]==1
    assert c["before_turn_future"]==1
    assert c["after_turn_exact"]==1
    assert c["after_turn_earlier"]==1
    assert c["after_turn_missing_or_invalid"]==1
    assert c["before_exact_turn_and_full_typed_participants_owners"]==1
    assert c["after_exact_turn_and_full_typed_participants_owners"]==1

def test_same_vcr_id_across_archives_is_descriptive_not_continuity():
    b=snap(10,[row(17,10)])
    a=snap(11,[row(17,11)])
    c=profile(b,a)
    assert c["same_id_across_adjacent_archives_not_battle_link"]==1
    assert c["before_exact_turn_and_typed_participants"]==1
    assert c["after_exact_turn_and_typed_participants"]==1

@pytest.mark.parametrize("bad", [True,None,0,-1,1.1,"7"])
def test_malformed_id_atomic_abstain(bad):
    b=snap(10,[row(7,10)]);a=snap(11,[row(bad,11)])
    assert profile(b,a)=={"ABSTAIN_INVALID_OR_DUPLICATE_VCR_IDS":1}

def test_duplicates_and_arrays_atomic_abstain():
    b=snap(10,[row(7,10)]);a=snap(11,[row(8,11),row(8,11)])
    assert profile(b,a)=={"ABSTAIN_INVALID_OR_DUPLICATE_VCR_IDS":1}
    a["vcrs"]=None
    assert profile(b,a)=={"ABSTAIN_MISSING_VCR_ARRAY":1}

def test_typed_bool_owner_and_participant_never_promote_replay_input():
    b=snap(10,[row(7,10,left=True,right=20)])
    a=snap(11,[row(8,11,owners=False)])
    c=profile(b,a)
    assert c["before_two_participant_objectids_typed"]==0
    assert c["after_exact_turn_and_full_typed_participants_owners"]==0

def test_invalid_source_turn_pair_fails():
    with pytest.raises(ValueError):
        profile_vcr_archive_pair(snap(10,[]),snap(11,[]),before_turn=10,after_turn=12)

def fake_data():
    return {1:snap(10,[row(7,10)]),2:snap(11,[row(8,11)])}

class Conn:
    def __init__(self):self.calls=0
    def execute(self,sql):
        assert "FROM source_members" in sql
        return self
    def fetchmany(self,n):
        self.calls+=1
        return [(1,42,1,10,10),(2,42,1,11,11)] if self.calls==1 else []

def test_opt_in_m2_source_report_preserves_default_schema():
    data=fake_data()
    meta,pairs=census_members([Member(1,42,1,10,10),Member(2,42,1,11,11)],
        max_games=1,pairs_per_game=1,allowed_games={42})
    opts=dict(max_games=1,pairs_per_game=1,allowed_games={42},
      expected_frozen_selection_sha256=meta["metadata_frozen_selection_sha256"],
      reconstruct=lambda mid:copy.deepcopy(data[mid]))
    original=analyze_corpus_coverage(Conn(),**opts)
    assert "vcr_archive_temporal_input_readiness_not_host_phase" not in original["sample"]
    extra=analyze_corpus_coverage(Conn(),vcr_temporal_readiness=True,**opts)
    counts=extra["sample"]["vcr_archive_temporal_input_readiness_not_host_phase"]
    assert counts["qualified_archive_pairs"]==1
    assert counts["before_vcr_rows"]==1 and counts["after_vcr_rows"]==1
    assert counts["same_id_across_adjacent_archives_not_battle_link"]==0
    assert counts["before_exact_turn_and_full_typed_participants_owners"]==1
    assert counts["after_exact_turn_and_full_typed_participants_owners"]==1
    p=dict(extra["sample"]);p.pop("vcr_archive_temporal_input_readiness_not_host_phase")
    assert p==original["sample"]

def synthetic_counts():
    d={k:0 for k in SCHEMA_FIELDS}
    d.update(qualified_archive_pairs=8550,before_vcr_rows=21918,after_vcr_rows=22414,
      before_turn_exact=21918,after_turn_exact=22414,
      before_two_participant_objectids_typed=21918,after_two_participant_objectids_typed=22414,
      before_two_ownerids_typed=21918,after_two_ownerids_typed=22414,
      before_exact_turn_and_typed_participants=21918,
      after_exact_turn_and_typed_participants=22414,
      before_exact_turn_and_full_typed_participants_owners=21918,
      after_exact_turn_and_full_typed_participants_owners=22414)
    return d

def test_synthetic_full_partition_and_tampered_counts():
    d=synthetic_counts()
    assert validate_counts(d,pairs=8550,before_rows=21918,after_rows=22414,earlier_same_id=0)==d
    for key,val in [("before_turn_exact",21917),("before_two_ownerids_typed",True),
                    ("after_exact_turn_and_full_typed_participants_owners",22415)]:
        p=copy.deepcopy(d);p[key]=val
        with pytest.raises(ValueError):
            validate_counts(p,pairs=8550,before_rows=21918,after_rows=22414,earlier_same_id=0)
    p=copy.deepcopy(d);p["private_member_id"]=123456789
    with pytest.raises(ValueError):
        validate_counts(p,pairs=8550,before_rows=21918,after_rows=22414,earlier_same_id=0)

def test_isolated_system_python_validator_precheck(tmp_path):
    script=ROOT/"tools/diagnostics/validate_vcr_archive_temporal_readiness_v1.py"
    r=subprocess.run([sys.executable,"-I","-S",str(script),"--self-test"],
       cwd=tmp_path,capture_output=True,text=True,timeout=15)
    assert r.returncode==0,r.stdout+r.stderr
    assert "PASS_VCR_SYNTHETIC_PRECHECK_ONLY" in r.stdout
    r=subprocess.run([sys.executable,"-I","-S",str(script)],
       cwd=tmp_path,capture_output=True,text=True,timeout=15)
    assert r.returncode==2
    assert r.stdout.strip()=="ABSTAIN_VCR_SOURCE_INPUT_REQUIRED"

def test_exact_frozen_runner_and_generic_evidence_publication():
    runner=(ROOT/"tools/run-public100-baseline68-vcr-temporal-v1.sh").read_text()
    wrapper=(ROOT/"tools/run-public100-baseline68-vcr-temporal-v1-with-evidence.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in wrapper
    assert "private-local" not in wrapper
    assert "--pairs-per-game 128" in runner
    assert "--vcr-temporal-input-provenance" in runner
    assert "--expected-selection-sha256 4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    assert "validate_vcr_archive_temporal_readiness_v1.py" in runner
    for path in ("tools/run-public100-baseline68-vcr-temporal-v1.sh",
                 "tools/run-public100-baseline68-vcr-temporal-v1-with-evidence.sh"):
        assert subprocess.run(["bash","-n",str(ROOT/path)],capture_output=True).returncode==0
