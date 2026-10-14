from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_ordinary_parent_forward_v1.py"
SPEC=importlib.util.spec_from_file_location("c5_parent_forward_v1",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def site(ids=(10,11,12),game=555,turn=30):
    return {"game_id":game,"turn":turn,"x":110,"y":220,
            "cohort":"EARLY_QUINTILE","vcr_ids":list(ids),
            "adjacent_pairs":[(a,b) for a,b in zip(ids,ids[1:]) if b==a+1]}


def queue(ids=(10,11,12)):
    return [
        {"vcr_id":n,"left_ship_id":1,"right_ship_id":n+2,
         "pair":(1,n+2)}
        for n in ids
    ]


def setup(monkeypatch,*,capture=False,next_pair=(1,14),match_start=True):
    seen=[]
    def initial(*,context,appearances,start_vcr_id):
        assert all(x["vcr_id"]<start_vcr_id for x in context["factual_queue"])
        seen.append(("initial",start_vcr_id))
        return SimpleNamespace(dummy=1)
    monkeypatch.setattr(M.differential,"_initial_state_before_window",initial)
    monkeypatch.setattr(M,"record_factual_site_pair",lambda state,**kw:state)
    def current(*a,**kw):
        return SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),
                               settings={})
    def terminal(state,*,vcr_payload,beams,torpedoes,settings):
        seen.append(("replay",vcr_payload["id"]))
        return SimpleNamespace(resolved=match_start,
                               reason=None if match_start else "start mismatch",
                               terminals_by_ship_id={},
                               capture_transfers_by_ship_id={1:"transfer"} if capture else {})
    monkeypatch.setattr(M.differential,"build_site_terminal_replay_batch",terminal)
    monkeypatch.setattr(M,"apply_site_terminal_batch",
                        lambda state,**kw:SimpleNamespace(resolved=True,state=state))
    def adapter(*,state,context,target_battle_turn,through_vcr_id,**kw):
        assert max(x["vcr_id"] for x in context["factual_queue"])==through_vcr_id
        seen.append(("adapter",through_vcr_id))
        return SimpleNamespace(pair_inputs=(11,12))
    monkeypatch.setattr(M,"build_parent_standard_pair_inputs",adapter)
    monkeypatch.setattr(M,"select_parent_resume",
        lambda state,*,pair_inputs:SimpleNamespace(
            status="resolved",pair=next_pair,left_ship_id=next_pair[0],
            right_ship_id=next_pair[1],occurrence_index=1))
    return seen


def test_context_censors_future_factually_before_parent_adapter():
    c={"factual_queue":queue()}
    prefix=M.context_without_future(c,through_vcr_id=10)
    assert [x["vcr_id"] for x in prefix["factual_queue"]]==[10]
    assert len(c["factual_queue"])==3
    with pytest.raises(ValueError,match="future factual"):
        M.predict_from_prefix(
            context=c,appearances={},cases={},game=555,turn=30,n=10)


def test_predict_parent_only_from_history_and_current_replay(monkeypatch):
    seen=setup(monkeypatch)
    r=M.predict_from_prefix(
        context=M.context_without_future({"factual_queue":queue()},through_vcr_id=10),
        appearances={},cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={})},
        game=555,turn=30,n=10
    )
    assert r["status"]=="PREDICTED_NEXT_PARENT_STANDARD"
    assert r["prediction"]["pair"]==[1,14]
    assert r["prediction"]["diplomacy_controls_through_vcr_id"]==10
    assert r["prediction"]["capture_fixture_order_used"] is False
    assert r["factual_comparison"] is None
    assert seen==[("initial",10),("replay",10),("adapter",10)]


def test_unknown_capture_does_not_guess_temporary_order(monkeypatch):
    seen=setup(monkeypatch,capture=True)
    r=M.predict_from_prefix(
        context=M.context_without_future({"factual_queue":queue()},through_vcr_id=10),
        appearances={},cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={})},
        game=555,turn=30,n=10)
    assert r["status"]=="ABSTAIN_CAPTURE_TEMPORARY_ORDER_NOT_INDEPENDENT"
    assert not any(x[0]=="adapter" for x in seen)


def test_bad_replay_fails_closed_no_standard_guess(monkeypatch):
    seen=setup(monkeypatch,match_start=False)
    r=M.predict_from_prefix(
        context=M.context_without_future({"factual_queue":queue()},through_vcr_id=10),
        appearances={},cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={})},
        game=555,turn=30,n=10)
    assert r["status"]=="ABSTAIN_CURRENT_REPLAY_OR_CARRIED_START"
    assert not any(x[0]=="adapter" for x in seen)


def test_observation_only_after_selection(monkeypatch):
    seen=setup(monkeypatch,next_pair=(1,13))
    cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={}),
           (30,11):SimpleNamespace(payload={"id":11},beams=(),torpedoes=(),settings={}),
           (30,12):SimpleNamespace(payload={"id":12},beams=(),torpedoes=(),settings={})}
    result=M.evaluate_site(
        site=site(),
        context={"factual_queue":queue()},appearances={},cases=cases)
    assert len(result["transitions"])==2
    assert result["missed_transitions"]==0
    t=result["transitions"][0]
    assert t["status"]=="PREDICTED_NEXT_PARENT_STANDARD"
    assert t["factual_comparison"]["exact"] is True
    assert all(x[0]!="replay" or x[1]==10 for x in seen[:3])
    assert result["transitions"][1]["factual_comparison"]["exact"] is False


def test_next_comparator_changes_without_altering_selection(monkeypatch):
    setup(monkeypatch,next_pair=(1,15))
    c={"factual_queue":queue((10,11))}
    pair=M.evaluate_site(
        site=site((10,11)),context=c,appearances={},
        cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={})})
    c["factual_queue"][1]["right_ship_id"]=15
    c["factual_queue"][1]["pair"]=(1,15)
    pair2=M.evaluate_site(
        site=site((10,11)),context=c,appearances={},
        cases={(30,10):SimpleNamespace(payload={"id":10},beams=(),torpedoes=(),settings={})})
    assert pair["transitions"][0]["prediction"]==pair2["transitions"][0]["prediction"]
    assert pair["transitions"][0]["factual_comparison"]["exact"] is False
    assert pair2["transitions"][0]["factual_comparison"]["exact"] is True


def test_no_silent_censor_if_frozen_site_membership_differs():
    r=M.evaluate_site(
        site=site(),context={"factual_queue":queue((10,11))},
        appearances={},cases={})
    assert r["status"]=="ABSTAIN_FROZEN_VCR_SITE_MEMBERSHIP_MISMATCH"
    assert r["missed_transitions"]==2


def test_pinned_frozen_census_requires_27_sites_and_63_adjacent():
    rows=[]
    for game in range(27):
        k=12 if game==0 else (9 if game==1 else 2)
        # 11+8+25=44; need 63 total: 19 further opportunities
        if game in range(2,21):k=3
        ids=list(range(1000,1000+k))
        rows.append({
            "game_id":game+1,"turn":20,"cohort":"EARLY_QUINTILE",
            "sites":[{
                "candidate_multi_ship_site":True,
                "category":"ORDINARY_SHIP_ONLY_MULTIVCR_SITE",
                "x":game+1,"y":10,
                "ordinary_ship_vcr_ids":ids,"all_vcr_ids":ids,
                "observed_ship_VCR_ID_adjacent_pairs":k-1,
            }],
        })
    n=sum(len(r["sites"][0]["ordinary_ship_vcr_ids"])-1 for r in rows)
    assert n==63
    rows.extend({"game_id":i+100,"turn":20,"sites":[]} for i in range(69))
    report={
        "schema":M.coverage.SCHEMA,"status":M.coverage.STATUS,
        "source_db_sha256":M.SHA256,
        "summary":{"games":48,"windows":96,
                   "current_VCR_observations":809,
                   "ordinary_ship_only_multi_VCR_sites":27},
        "preselected_window_evaluations":rows,
    }
    sites=M.freeze_sites(report)
    assert len(sites)==27
    assert sum(len(x["adjacent_pairs"]) for x in sites)==63
    report["summary"]["ordinary_ship_only_multi_VCR_sites"]=28
    with pytest.raises(ValueError,match="population"):
        M.freeze_sites(report)


def test_runner_and_evidence_shell_syntax():
    run=ROOT/"tools/run-combat-c5-ordinary-parent-forward-v1.sh"
    wrapper=ROOT/"tools/run-combat-c5-ordinary-parent-forward-v1-with-evidence.sh"
    for x in (run,wrapper):
        subprocess.run(["bash","-n",str(x)],check=True)
    assert "CURRENT" not in run.read_text()
    assert M.CENSUS_GIT_BLOB_SHA1 in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
