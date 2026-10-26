"""Synthetic same-turn multi-perspective source gate and frozen runtime contracts."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest

from planets_lab.corpus.vcr_same_turn_consensus_readiness import FrozenSameTurnVcrConsensus
from planets_lab.corpus.m2_economy_coverage import Member, census_members, analyze_corpus_coverage
from tools.diagnostics.validate_vcr_same_turn_consensus_v1 import (
    FIELDS, validate_counts,
)

ROOT = Path(__file__).resolve().parents[1]


def source(*, player=1, turn=10, vid=7, damage=4, seed=1,
           combat_rng=0, owner_pair=True):
    vcr={"id":vid,"turn":turn,"seed":seed,
         "left":{"objectid":20},"right":{"objectid":30}}
    if owner_pair:
        vcr.update(leftownerid=1,rightownerid=2)
    return {"game":{"id":42,"turn":turn},"player":{"id":player},
            "settings":{"combatrng":combat_rng},"beams":[{"id":1,"damage":damage,"crewkill":5}],
            "torpedos":[{"id":1,"damage":5,"crewkill":2,"combatrange":100}],
            "vcrs":[vcr],"ships":[],"minefields":[],"ionstorms":[],
            "starbases":[],"planets":[]}


def observe(audit, member_id, s):
    audit.observe(member_id=member_id, game=42, turn=s["game"]["turn"],
                  observer=s["player"]["id"], payload=s)


def test_consensus_two_observers_same_turn_deduplicates_same_source_member():
    a=FrozenSameTurnVcrConsensus()
    observe(a,1,source(player=1))
    observe(a,1,source(player=1,damage=9000))  # duplicate source ignored
    observe(a,2,source(player=2))
    q=a.result(qualified_archive_pairs=8550)
    assert q["unique_frozen_archive_members_examined"]==2
    assert q["vcr_rows_qualified_same_turn_typed_participants"]==2
    assert q["same_turn_observation_groups"]==1
    assert q["multi_perspective_groups"]==1
    assert q["multi_perspective_strict_complete_inputs_equal"]==1
    assert q["multi_perspective_complete_adapter_signature_equal"]==1
    assert q["multi_perspective_vcr_payload_equal"]==1
    assert q["source_observation_rows_in_qualified_groups"]==2
    assert not any("game_id" in k or "battle_id" in k or "signature_hash" in k for k in q)


@pytest.mark.parametrize(("field","expected"),[
    ("damage","multi_perspective_weapon_catalog_different"),
    ("seed","multi_perspective_vcr_payload_different"),
    ("combat_rng","multi_perspective_combat_rng_settings_different"),
])
def test_component_specific_replay_input_mismatch(field,expected):
    a=FrozenSameTurnVcrConsensus()
    observe(a,1,source(player=1))
    other={"player":2,field:99}
    observe(a,2,source(**other))
    q=a.result(qualified_archive_pairs=8550)
    assert q[expected]==1
    assert q["multi_perspective_complete_adapter_signature_different"]==1
    assert q["multi_perspective_strict_complete_inputs_different"]==1


def test_missing_catalog_or_rng_and_missing_owner_abstain_from_strict_full_readiness():
    a=FrozenSameTurnVcrConsensus()
    observe(a,1,source())
    other=source(player=2,owner_pair=False)
    other.pop("torpedos")
    other["settings"]={}
    observe(a,2,other)
    q=a.result(qualified_archive_pairs=8550)
    assert q["multi_perspective_groups"]==1
    assert q["multi_perspective_strict_inputs_incomplete"]==1
    assert q["multi_perspective_strict_complete_inputs_equal"]==0
    assert q["vcr_rows_missing_typed_weapon_catalog"]==1
    assert q["vcr_rows_missing_explicit_combat_rng"]==1
    assert q["vcr_rows_missing_typed_owner_pair"]==1


def test_strictly_same_turn_does_not_cross_qualify_the_same_id_next_turn():
    a=FrozenSameTurnVcrConsensus()
    observe(a,1,source(turn=10,player=1))
    observe(a,2,source(turn=11,player=2))
    q=a.result(qualified_archive_pairs=8550)
    assert q["same_turn_observation_groups"]==2
    assert q["multi_perspective_groups"]==0


@pytest.mark.parametrize("malform", [
    lambda s:s["vcrs"][0].update(id=True),
    lambda s:s["vcrs"][0].update(id="7"),
    lambda s:s["vcrs"].append(copy.deepcopy(s["vcrs"][0])),
    lambda s:s["vcrs"].append("raw-untrusted"),
])
def test_atomic_rejection_for_bad_member_vcr_ids(malform):
    a=FrozenSameTurnVcrConsensus()
    s=source()
    malform(s)
    observe(a,1,s)
    q=a.result(qualified_archive_pairs=8550)
    assert q["ABSTAIN_MEMBER_VCR_IDS_INVALID_OR_DUPLICATE"]==1
    assert q["same_turn_observation_groups"]==0
    assert q["vcr_rows_unqualified_atomic_member_abstain"]==len(s["vcrs"])


def test_untyped_battle_turn_participants_and_nan_are_not_exported():
    a=FrozenSameTurnVcrConsensus()
    bad=source()
    bad["vcrs"][0]["turn"]=11
    observe(a,1,bad)
    bad2=source(player=2)
    bad2["vcrs"][0]["left"]["objectid"]=True
    observe(a,2,bad2)
    bad3=source(player=3)
    bad3["vcrs"][0]["seed"]=float("nan")
    observe(a,3,bad3)
    result=a.result(qualified_archive_pairs=8550)
    assert result["vcr_rows_unqualified_turn_or_participant"]==2
    assert result["vcr_rows_unqualified_unserializable_input"]==1
    assert result["same_turn_observation_groups"]==0


class Conn:
    def __init__(self): self.calls=0
    def execute(self,sql):
        assert "FROM source_members" in sql
        return self
    def fetchmany(self,n):
        self.calls+=1
        return [(1,42,1,10,10),(2,42,1,11,11),
                (3,42,2,10,10),(4,42,2,11,11)] if self.calls==1 else []


def test_opt_in_frozen_two_player_adjacent_pair_integration_preserves_old_report():
    members=[Member(1,42,1,10,10),Member(2,42,1,11,11),
             Member(3,42,2,10,10),Member(4,42,2,11,11)]
    meta,pairs=census_members(members,max_games=1,pairs_per_game=2,allowed_games={42})
    assert len(pairs)==2
    data={1:source(turn=10,player=1),2:source(turn=11,player=1,vid=8),
          3:source(turn=10,player=2),4:source(turn=11,player=2,vid=8)}
    opts=dict(max_games=1,pairs_per_game=2,allowed_games={42},
              expected_frozen_selection_sha256=meta["metadata_frozen_selection_sha256"],
              reconstruct=lambda mid:copy.deepcopy(data[mid]))
    old=analyze_corpus_coverage(Conn(),**opts)
    new=analyze_corpus_coverage(Conn(),vcr_same_turn_consensus_readiness=True,**opts)
    label="vcr_same_turn_perspective_consensus_not_host_phase"
    assert label not in old["sample"]
    q=new["sample"][label]
    assert q["qualified_original_frozen_adjacent_pairs"]==2
    assert q["unique_frozen_archive_members_examined"]==4
    assert q["same_turn_observation_groups"]==2
    assert q["multi_perspective_groups"]==2
    assert q["multi_perspective_strict_complete_inputs_equal"]==2
    del new["sample"][label]
    assert new==old


def fake_valid_count():
    d=dict.fromkeys(FIELDS,0)
    d.update(qualified_original_frozen_adjacent_pairs=8550,
             unique_frozen_archive_members_examined=2,
             qualified_member_vcr_lists=2,
             vcr_rows_in_unique_member_archives=2,
             vcr_rows_qualified_same_turn_typed_participants=2,
             source_observation_rows_in_qualified_groups=2,
             same_turn_observation_groups=1,multi_perspective_groups=1,
             multi_perspective_groups_two_observers=1,
             multi_perspective_observer_occurrences=2,
             multi_perspective_vcr_payload_equal=1,
             multi_perspective_weapon_catalog_equal=1,
             multi_perspective_combat_rng_settings_equal=1,
             multi_perspective_complete_adapter_signature_equal=1,
             multi_perspective_strict_complete_inputs_equal=1)
    return d


def test_strict_host_validator_rejects_privacy_and_partition_tamper():
    src=fake_valid_count()
    assert validate_counts(src,original_pairs=8550)==src
    for key,value in [
        ("multi_perspective_strict_complete_inputs_equal",True),
        ("source_observation_rows_in_qualified_groups",999),
        ("qualified_original_frozen_adjacent_pairs",8551),
        ("multi_perspective_vcr_payload_equal",0),
        ("raw_private_game_id",99999),
    ]:
        d=dict(src);d[key]=value
        with pytest.raises(ValueError):
            validate_counts(d,original_pairs=8550)


def test_isolated_host_self_test_and_dedicated_runner_contract(tmp_path):
    validator=ROOT/"tools/diagnostics/validate_vcr_same_turn_consensus_v1.py"
    r=subprocess.run([sys.executable,"-I","-S",str(validator),"--self-test"],
                     cwd=tmp_path,capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stdout+r.stderr
    runner=(ROOT/"tools/run-public100-baseline68-vcr-same-turn-v1.sh").read_text()
    wrapper=(ROOT/"tools/run-public100-baseline68-vcr-same-turn-v1-with-evidence.sh").read_text()
    assert "tools/run-with-runtime-evidence.sh" in wrapper
    assert "private-local" not in wrapper
    assert "--vcr-same-turn-consensus" in runner
    assert "--pairs-per-game 128" in runner
    assert "--expected-selection-sha256 4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659" in runner
    assert "validate_vcr_same_turn_consensus_v1.py" in runner
    assert "public100_baseline68_cohort_guard_v3.py" in runner
    for script in (runner,wrapper):
        assert subprocess.run(["bash","-n"],input=script,
                              capture_output=True,text=True).returncode==0
