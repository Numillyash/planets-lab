"""Joint categorical missingness of VCR RNG, owner pair and catalog."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.vcr_same_turn_missingness_joint import (
    FIELDS, REASONS, FrozenSameTurnMissingnessJoint,
)
from planets_lab.corpus.m2_economy_coverage import Member, census_members, analyze_corpus_coverage
from tools.diagnostics.validate_vcr_same_turn_missingness_joint_v2 import validate_joint

ROOT=Path(__file__).resolve().parents[1]

def payload(player=1, turn=10, *, seed=2, rng=True, owner=True, catalog=True):
    row={"id":7,"turn":turn,"seed":seed,
         "left":{"objectid":11},"right":{"objectid":22}}
    if owner:
        row.update(leftownerid=1,rightownerid=2)
    p={"game":{"id":42,"turn":turn},"player":{"id":player},
       "vcrs":[row],"settings":{"combatrng":0} if rng else {},
       "beams":[{"id":1,"damage":5,"crewkill":3}],
       "torpedos":[{"id":1,"damage":8,"crewkill":2,"combatrange":300}],
       "ships":[],"planets":[],"starbases":[],"minefields":[],"ionstorms":[]}
    if not catalog:
        del p["torpedos"]
    return p

def add(a,mid,p):
    a.observe(member_id=mid,game=42,turn=p["game"]["turn"],
              observer=p["player"]["id"],payload=p)

def test_exact_two_perspective_group_with_no_missing_source_fields():
    a=FrozenSameTurnMissingnessJoint()
    add(a,1,payload(player=1))
    add(a,2,payload(player=2))
    d=a.joint_result(qualified_archive_pairs=8550)
    assert set(d)==set(FIELDS)
    assert d["multi_complete_groups"]==1
    assert d["multi_complete_signature_equal"]==1
    assert d["multi_missing_rng_rows"]==0
    assert d["single_perspective_groups"]==0
    assert d["multi_perspective_groups"]==1

def test_mixed_absence_rng_and_owner_on_different_observers_same_group():
    a=FrozenSameTurnMissingnessJoint()
    add(a,1,payload(player=1,rng=False))
    add(a,2,payload(player=2,owner=False))
    q=a.joint_result(qualified_archive_pairs=8550)
    assert q["multi_rng_owner_groups"]==1
    assert q["multi_missing_rng_rows"]==1
    assert q["multi_missing_owner_rows"]==1
    assert q["multi_complete_groups"]==0
    assert q["multi_incomplete_signature_different"]==1
    assert q["multi_incomplete_signature_equal"]==0

def test_absence_on_both_observers_counts_group_once_but_rows_twice():
    a=FrozenSameTurnMissingnessJoint()
    add(a,1,payload(player=1,rng=False))
    add(a,2,payload(player=2,rng=False))
    q=a.joint_result(qualified_archive_pairs=8550)
    assert q["multi_rng_only_groups"]==1
    assert q["multi_missing_rng_rows"]==2
    assert q["multi_incomplete_signature_equal"]==1

def test_singleton_margins_do_not_inflate_multi_incomplete_groups():
    a=FrozenSameTurnMissingnessJoint()
    add(a,1,payload(player=1,rng=False,owner=False,catalog=False))
    add(a,2,payload(player=2,turn=11))
    q=a.joint_result(qualified_archive_pairs=8550)
    assert q["single_rng_owner_catalog_groups"]==1
    assert q["single_complete_groups"]==1
    assert q["multi_perspective_groups"]==0
    assert q["single_missing_rng_rows"]==1
    assert q["single_missing_owner_rows"]==1
    assert q["single_missing_catalog_rows"]==1

def test_full_signature_disagreement_distinguished_from_missingness():
    a=FrozenSameTurnMissingnessJoint()
    add(a,1,payload(player=1,seed=9))
    add(a,2,payload(player=2,seed=10))
    q=a.joint_result(qualified_archive_pairs=8550)
    assert q["multi_complete_groups"]==1
    assert q["multi_complete_signature_different"]==1


class Conn:
    def __init__(self):self.calls=0
    def execute(self,sql):
        assert "FROM source_members" in sql
        return self
    def fetchmany(self,n):
        self.calls+=1
        return [(1,42,1,10,10),(2,42,1,11,11),(3,42,1,12,12),
                (4,42,2,10,10),(5,42,2,11,11),(6,42,2,12,12)] if self.calls==1 else []


def test_opt_in_joint_preserves_unmodified_v1_and_default_m2_report():
    members=[Member(1,42,1,10,10),Member(2,42,1,11,11),Member(3,42,1,12,12),
             Member(4,42,2,10,10),Member(5,42,2,11,11),Member(6,42,2,12,12)]
    meta,pairs=census_members(members,max_games=1,pairs_per_game=2,allowed_games={42})
    assert [(p.player,p.after_turn) for p in pairs]==[(1,11),(2,12)]
    data={1:payload(player=1,turn=10),2:payload(player=1,turn=11,rng=False),
          3:payload(player=1,turn=12),4:payload(player=2,turn=10),
          5:payload(player=2,turn=11,owner=False),6:payload(player=2,turn=12)}
    opts=dict(max_games=1,pairs_per_game=2,allowed_games={42},
       expected_frozen_selection_sha256=meta["metadata_frozen_selection_sha256"],
       reconstruct=lambda mid:copy.deepcopy(data[mid]))
    default=analyze_corpus_coverage(Conn(),**opts)
    only_v1=analyze_corpus_coverage(Conn(),vcr_same_turn_consensus_readiness=True,**opts)
    joint=analyze_corpus_coverage(Conn(),vcr_same_turn_consensus_readiness=True,
                                  vcr_same_turn_missingness_joint=True,**opts)
    k="vcr_same_turn_perspective_consensus_not_host_phase"
    new="vcr_same_turn_missingness_joint_not_host_phase"
    assert new not in only_v1["sample"] and new not in default["sample"]
    assert joint["sample"][k]==only_v1["sample"][k]
    assert joint["sample"][new]["multi_rng_owner_groups"]==1
    assert joint["sample"][new]["multi_incomplete_signature_different"]==1
    del joint["sample"][k]
    del joint["sample"][new]
    assert joint==default

def synthetic_valid_pair():
    old=dict(
        qualified_original_frozen_adjacent_pairs=8550,
        vcr_rows_qualified_same_turn_typed_participants=44332,
        single_perspective_groups=32120,
        multi_perspective_groups=6106,
        multi_perspective_observer_occurrences=12212,
        multi_perspective_strict_complete_inputs_equal=6047,
        multi_perspective_strict_complete_inputs_different=0,
        multi_perspective_strict_inputs_incomplete=59,
        vcr_rows_missing_explicit_combat_rng=323,
        vcr_rows_missing_typed_owner_pair=1,
        vcr_rows_missing_typed_weapon_catalog=0,
        multi_perspective_complete_adapter_signature_equal=6106,
        multi_perspective_complete_adapter_signature_different=0,
    )
    d=dict.fromkeys(FIELDS,0)
    d.update(
        qualified_original_frozen_adjacent_pairs=8550,
        source_observation_rows_qualified=44332,
        single_perspective_groups=32120,multi_perspective_groups=6106,
        single_source_observation_rows=32120,multi_source_observation_rows=12212,
        single_missing_rng_rows=264,multi_missing_rng_rows=59,
        single_missing_owner_rows=1,
        single_complete_groups=31855,single_rng_only_groups=264,
        single_owner_only_groups=1,
        multi_complete_groups=6047,multi_rng_only_groups=59,
        multi_complete_signature_equal=6047,multi_incomplete_signature_equal=59,
    )
    return old,d

def test_standalone_validator_rejects_strict_counts_leak_and_partitions():
    old,d=synthetic_valid_pair()
    assert validate_joint(d,old)==d
    for key,value in [
        ("multi_rng_only_groups",60),
        ("single_missing_rng_rows",263),
        ("single_missing_owner_rows",True),
        ("source_observation_rows_qualified",44333),
        ("multi_complete_signature_equal",6048),
        ("private_vcr_seed_999999",7),
    ]:
        x=dict(d);x[key]=value
        with pytest.raises(ValueError):
            validate_joint(x,old)

def test_host_stdlib_isolation_exact_frozen_runner_contract(tmp_path):
    val=ROOT/"tools/diagnostics/validate_vcr_same_turn_missingness_joint_v2.py"
    q=subprocess.run([sys.executable,"-I","-S",str(val),"--self-test"],
                     cwd=tmp_path,text=True,capture_output=True,timeout=20)
    assert q.returncode==0,q.stdout+q.stderr
    runner=(ROOT/"tools/run-public100-baseline68-vcr-missingness-joint-v2.sh").read_text()
    wrapper=(ROOT/"tools/run-public100-baseline68-vcr-missingness-joint-v2-with-evidence.sh").read_text()
    assert "--vcr-same-turn-consensus" in runner
    assert "--vcr-same-turn-missingness-joint" in runner
    assert "--pairs-per-game 128" in runner
    assert "4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    assert "validate_vcr_same_turn_missingness_joint_v2.py" in runner
    assert "tools/run-with-runtime-evidence.sh" in wrapper
    assert "private-local" not in wrapper
    for script in (runner,wrapper):
        assert subprocess.run(["bash","-n"],input=script,
                              capture_output=True,text=True).returncode==0
