from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_pre_n_site_presence_partition_v5.py"
SPEC=importlib.util.spec_from_file_location("combat_c5_site_history_v5",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def case(a,b):
    return SimpleNamespace(payload={"left":{"objectid":a},
                                    "right":{"objectid":b}})


def risk(*ships,status="ABSTAIN_PARENT_STANDARD_NO_PAIR",n=6):
    return {
        "from_vcr_id":n,"original_conditional_v2_status":status,
        "risk_status":"ABSTAIN_PLAUSIBLE_UNRESOLVED_TMINUS1_ARRIVALS",
        "future_Nplus1_used":False,"original_next_pair_or_side_changed":False,
        "Tminus1_plausible_arrivals":[
            {"ship_id":ship,"owner_id":3,"position_source":"tow_target"}
            for ship in ships
        ],
    }


def test_current_vcr_prefix_never_reads_future_case_body():
    class ForbiddenFuture:
        @property
        def payload(self):
            raise AssertionError("future VCR N+1 accessed")
    cases={(33,2):case(12,21),(33,4):case(23,22),
           (33,6):case(1,2),(33,7):ForbiddenFuture()}
    prior,current=M.pre_n_site_history(
        cases=cases,turn=33,frozen_vcr_ids=[2,4,6,7],
        through_vcr_id=6)
    assert prior=={12:2,21:2,23:4,22:4}
    assert current==frozenset({1,2})
    evaluated=M.partition_transition(risk(12,99),prior=prior,current_ids=current)
    assert evaluated["prior_site_VCR_participant_count"]==1
    assert evaluated["not_seen_in_prior_site_VCR_count"]==1
    assert evaluated["partition_status"]=="ABSTAIN_UNSEEN_TMINUS1_SITE_ARRIVAL_REMAINS"
    assert evaluated["witnesses"][0]["first_prior_site_vcr_id"]==2
    assert evaluated["witnesses"][1]["first_prior_site_vcr_id"] is None
    assert evaluated["Nplus1_ship_identity_used"] is False


def test_prior_only_and_empty_index_still_fail_closed():
    prior={12:1}
    current=frozenset({1,2})
    previously=M.partition_transition(risk(12),prior=prior,current_ids=current)
    assert previously["partition_status"]=="ABSTAIN_ONLY_PRIOR_SITE_PARTICIPANTS_CARRY_UNRESOLVED"
    assert previously["terminal_outcome_or_survival_inferred"] is False
    absent=M.partition_transition(risk(),prior=prior,current_ids=current)
    assert absent["partition_status"]=="NO_PAIR_NOT_PROVEN_SITE_EXHAUSTED_WITH_NO_INDEXED_WITNESS"
    assert absent["new_battle_prediction"] is False
    non_pair=M.partition_transition(
        risk(12,status="CONDITIONAL_PARENT_STANDARD_N_TO_NPLUS1"),
        prior=prior,current_ids=current)
    assert non_pair["partition_status"]=="ORIGINAL_V2_NON_NO_PAIR_VERDICT_UNCHANGED"


def test_previous_ship_appearance_is_time_relative_not_global():
    cases={(9,1):case(7,8),(9,3):case(12,13),(9,4):case(1,2)}
    prior_n3,now_n3=M.pre_n_site_history(
        cases=cases,turn=9,frozen_vcr_ids=[1,3,4],
        through_vcr_id=3)
    first=M.partition_transition(
        risk(1,n=3),prior=prior_n3,current_ids=now_n3)
    assert first["not_seen_in_prior_site_VCR_count"]==1
    prior_n4,now_n4=M.pre_n_site_history(
        cases=cases,turn=9,frozen_vcr_ids=[1,3,4],
        through_vcr_id=4)
    second=M.partition_transition(
        risk(12,n=4),prior=prior_n4,current_ids=now_n4)
    assert second["prior_site_VCR_participant_count"]==1


def test_duplicates_future_flags_and_current_participants_are_rejected():
    with pytest.raises(ValueError,match="duplicate V4"):
        M.partition_transition(risk(12,12),prior={},current_ids=frozenset({1,2}))
    with pytest.raises(ValueError,match="already in current"):
        M.partition_transition(risk(1),prior={},current_ids=frozenset({1,2}))
    broken=risk(12)
    broken["future_Nplus1_used"]=True
    with pytest.raises(ValueError,match="nonleakage"):
        M.partition_transition(broken,prior={},current_ids=frozenset({1,2}))
    with pytest.raises(ValueError,match="historical case missing"):
        M.pre_n_site_history(
            cases={},turn=1,frozen_vcr_ids=[1,2],through_vcr_id=1)
    with pytest.raises(ValueError,match="invalid frozen VCR site prefix"):
        M.pre_n_site_history(
            cases={},turn=1,frozen_vcr_ids=[2,1],through_vcr_id=1)


def test_runner_evidence_and_no_current_db_mutation():
    run=ROOT/"tools/run-combat-c5-pre-n-site-presence-partition-v5.sh"
    wrapper=ROOT/"tools/run-combat-c5-pre-n-site-presence-partition-v5-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    source=run.read_text(encoding="utf-8")
    assert M.V4_BLOB in source
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
    assert "/CURRENT" not in source
    assert M.NO_PAIR=="ABSTAIN_PARENT_STANDARD_NO_PAIR"
