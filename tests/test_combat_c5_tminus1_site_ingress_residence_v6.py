from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_tminus1_site_ingress_residence_v6.py"
S=importlib.util.spec_from_file_location("c5_ingress_residence_v6",SCRIPT)
assert S is not None and S.loader is not None
M=importlib.util.module_from_spec(S)
sys.modules[S.name]=M
S.loader.exec_module(M)


def witness(ship, *, start=False, waypoint=True, owner=3, source="normal_mine_route_risk"):
    return {"ship_id":ship,"owner_id":owner,"position_source":source,
            "start_at_site":start,"waypoint_at_site":waypoint}


def pair(*ws, n=10, prior=None, status="ABSTAIN_PARENT_STANDARD_NO_PAIR"):
    prior={} if prior is None else prior
    a={
        "from_vcr_id":n,"original_conditional_v2_status":status,
        "risk_status":"ABSTAIN_PLAUSIBLE_UNRESOLVED_TMINUS1_ARRIVALS",
        "future_Nplus1_used":False,"original_next_pair_or_side_changed":False,
        "independent_Tminus1_plausible_arrival_count":len(ws),
        "Tminus1_plausible_arrivals":list(ws),
    }
    v5=[]
    for w in ws:
        p=prior.get(w["ship_id"])
        v5.append({
            "ship_id":w["ship_id"],"owner_id":w["owner_id"],
            "position_source":w["position_source"],
            "first_prior_site_vcr_id":p,
            "class":M.PRIOR if p is not None else M.UNSEEN,
            "site_history_not_terminal_survival_evidence":True,
        })
    b={
        "from_vcr_id":n,"original_v2_status":status,
        "original_v4_risk_status":a["risk_status"],
        "Nplus1_ship_identity_used":False,"new_battle_prediction":False,
        "terminal_outcome_or_survival_inferred":False,
        "V4_potential_arrival_count":len(ws),"witnesses":v5,
        "prior_site_VCR_participant_count":len(prior),
        "not_seen_in_prior_site_VCR_count":len(ws)-len(prior),
        "partition_status":"ABSTAIN_UNSEEN_TMINUS1_SITE_ARRIVAL_REMAINS",
    }
    return a,b


def test_spatial_class_does_not_infer_trajectory():
    assert M.spatial_classification(witness(2,start=True,waypoint=False),None,through_n=10)==(
        "UNSEEN_TMINUS1_START_AT_SITE_ONLY")
    assert M.spatial_classification(witness(2,start=False,waypoint=True),None,through_n=10)==(
        "UNSEEN_TMINUS1_WAYPOINT_AT_SITE_ONLY")
    assert M.spatial_classification(witness(2,start=True,waypoint=True),None,through_n=10)==(
        "UNSEEN_TMINUS1_START_AND_WAYPOINT_AT_SITE")
    assert M.spatial_classification(witness(2,start=True,waypoint=False),7,through_n=10)==(
        "PRIOR_SITE_VCR_CARRY_UNRESOLVED")


def test_prior_site_carry_and_absence_remain_fail_closed():
    a,b=pair(witness(22,start=True,waypoint=False),prior={22:9})
    out=M.merge_transition(a,b)
    assert out["spatial_guard_status"]=="ABSTAIN_ONLY_PRIOR_SITE_CARRY_UNRESOLVED"
    a,b=pair(witness(22,start=True,waypoint=False))
    assert M.merge_transition(a,b)["spatial_guard_status"]=="ABSTAIN_TMINUS1_START_RESIDENCE_UNRESOLVED"
    a,b=pair(witness(22,start=False,waypoint=True))
    assert M.merge_transition(a,b)["spatial_guard_status"]=="ABSTAIN_WAYPOINT_ONLY_INGRESS_UNRESOLVED"
    a,b=pair()
    assert M.merge_transition(a,b)["spatial_guard_status"]=="NO_PAIR_NOT_PROVEN_NO_INDEXED_WITNESS"
    a,b=pair(witness(22),status="CONDITIONAL_PARENT_STANDARD_N_TO_NPLUS1")
    assert M.merge_transition(a,b)["spatial_guard_status"]=="ORIGINAL_NON_NO_PAIR_VERDICT_UNCHANGED"


def test_mixed_source_priors_and_exact_cohort_multiplicity():
    a,b=pair(witness(12,start=True,waypoint=True),
             witness(13,start=False,waypoint=True),prior={12:8})
    out=M.merge_transition(a,b)
    assert out["spatial_guard_status"]=="ABSTAIN_WAYPOINT_ONLY_INGRESS_UNRESOLVED"
    assert [x["class"] for x in out["Tminus1_witnesses"]]==[
        "PRIOR_SITE_VCR_CARRY_UNRESOLVED","UNSEEN_TMINUS1_WAYPOINT_AT_SITE_ONLY"
    ]
    assert out["Nplus1_used"] is False


def test_bad_provenance_mutations_are_rejected_not_explained_away():
    a,b=pair(witness(31))
    dirty=copy.deepcopy(a)
    dirty["future_Nplus1_used"]=True
    with pytest.raises(ValueError,match="nonleakage"):
        M.merge_transition(dirty,b)
    dirty=copy.deepcopy(a)
    dirty["Tminus1_plausible_arrivals"][0]["start_at_site"]=False
    dirty["Tminus1_plausible_arrivals"][0]["waypoint_at_site"]=False
    with pytest.raises(ValueError,match="invalid T-1 site"):
        M.merge_transition(dirty,b)
    dirty=copy.deepcopy(b)
    dirty["witnesses"][0]["position_source"]="unapproved"
    with pytest.raises(ValueError,match="owner/source drift"):
        M.merge_transition(a,dirty)
    dirty=copy.deepcopy(b)
    dirty["witnesses"][0]["first_prior_site_vcr_id"]=10
    dirty["witnesses"][0]["class"]=M.PRIOR
    dirty["prior_site_VCR_participant_count"]=1
    dirty["not_seen_in_prior_site_VCR_count"]=0
    with pytest.raises(ValueError,match="strictly earlier"):
        M.merge_transition(a,dirty)
    dirty=copy.deepcopy(a)
    dirty["Tminus1_plausible_arrivals"].append(dirty["Tminus1_plausible_arrivals"][0])
    dirty["independent_Tminus1_plausible_arrival_count"]=2
    with pytest.raises(ValueError,match="denominator"):
        M.merge_transition(dirty,b)


def test_runner_is_source_pinned_and_no_db_mutation():
    run=ROOT/"tools/run-combat-c5-tminus1-site-ingress-residence-v6.sh"
    wrap=ROOT/"tools/run-combat-c5-tminus1-site-ingress-residence-v6-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    src=run.read_text(encoding="utf-8")
    assert M.V4_BLOB in src
    assert M.V5_BLOB in src
    assert "/CURRENT" not in src
    assert "run-with-runtime-evidence.sh" in wrap.read_text(encoding="utf-8")
