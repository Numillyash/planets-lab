from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"tools/diagnostics/combat_c5_short_chunnel_and_visibility_audit_v18.py"
SPEC=importlib.util.spec_from_file_location("c5_v18",SOURCE)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def sample_case(*,g=467386,t=75,a=467,b=80,owner=6,src=(1141,1459),dst=(1126,1439)):
    return {
        "game_id":g,"turn":t,"initiator_ship_id":a,"target_ship_id":b,
        "owner_id":owner,"source":list(src),"target":list(dst),
        "actor_Tminus1_fuel":51,"target_Tminus1_fuel":1,
        "actor_Tminus1_warp":0,"target_Tminus1_warp":0,
        "Tminus1_distance_ly":25,
        "cohort":"ONE_TMINUS1_GATE_FAILS",
        "single_failing_gate":"DISTANCE_BELOW_100_AT_TMINUS1",
        "T_actor_status":"T_ACTOR_AT_DISTINCT_FROZEN_TARGET",
        "T_actor_position":list(dst),"T_target_position":list(dst),
        "T_actor_net_fuel_delta_KT":48,
        "Tminus1_source_differs_from_target":True,
        "Host_Chunnel_activation_or_inactivation_proven":False,
        "Nplus1_VCR_used":False,
    }


def roster():
    return {
        467:(6,{
            "id":467,"x":1141,"y":1459,
            "hullid":56,"warp":0,"neutronium":51,
            "friendlycode":"080","targetx":1141,"targety":1459,
            "mission":0,"damage":0,
        }),
        80:(6,{
            "id":80,"x":1126,"y":1439,
            "hullid":56,"warp":0,"neutronium":1,
            "friendlycode":"abc","targetx":1126,"targety":1439,
            "mission":0,
        }),
        245:(6,{
            "id":245,"x":1141,"y":1459,
            "hullid":14,"warp":1,"mission":0,
        }),
    }


def test_25ly_source_is_verified_without_promoting_a_short_chunnel():
    data=M._ship_tminus1(sample_case(),roster())
    assert data["Tminus1_numeric_friendly_code_target_confirmed"] is True
    assert data["Tminus1_actor"]["warp"]==0
    assert data["Tminus1_candidate_source_target_distance_ly"]==25
    assert data["Tminus1_other_ships_colocated_with_actor"]==1
    assert data["Tminus1_tow_requests_on_endpoints"]==[]
    assert data["Tminus1_25ly_event_not_assigned_cause"] is True


def test_preexisting_tow_request_is_not_proof_of_lock():
    rows=roster()
    rows[710]=(5,{
        "id":710,"x":1141,"y":1459,"hullid":14,
        "mission":M.TOW_MISSION_ID,"mission1target":467,
    })
    data=M._ship_tminus1(sample_case(),rows)
    assert len(data["Tminus1_tow_requests_on_endpoints"])==1
    assert data["Tminus1_tow_requests_on_endpoints"][0][
        "request_not_confirmed_tow_lock"] is True


def test_modified_pre_state_fails_closed():
    rows=roster()
    rows[467][1]["x"]=900
    with pytest.raises(ValueError,match="identity/position"):
        M._ship_tminus1(sample_case(),rows)
    rows=roster()
    rows[467][1]["neutronium"]=40
    with pytest.raises(ValueError,match="numeric control"):
        M._ship_tminus1(sample_case(),rows)


def test_archive_perspectives_record_fresh_vs_stale_without_ownership_guess():
    before=sample_case()
    actor_records=[
        SimpleNamespace(player_id=6,is_current=False,raw={"ownerid":6}),
        SimpleNamespace(player_id=8,is_current=True,raw={"ownerid":7}),
    ]
    target_records=[
        SimpleNamespace(player_id=6,is_current=False,raw={"ownerid":6}),
        SimpleNamespace(player_id=8,is_current=True,raw={"ownerid":7}),
    ]
    monkeypatch_group=lambda *_:{
        (75,467):tuple(actor_records),(75,80):tuple(target_records)}
    orig=M.group_perspective_records
    try:
        M.group_perspective_records=monkeypatch_group
        result=M.perspective_coverage(before,(),frozenset({6,8}))
    finally:
        M.group_perspective_records=orig
    assert result["T_source_owner_perspective_present"] is True
    assert result["T_fresh_ship_evidence"]["actor"]["T_owner_current_record_available"] is False
    assert result["T_fresh_ship_evidence"]["actor"]["T_fresh_reported_owners"]==[7]
    assert result["T_fresh_ship_evidence"]["actor"]["T_stale_contacts_not_authoritative"] is True


def test_posthoc_recheck_rejects_changed_archived_T(monkeypatch):
    case=sample_case()
    monkeypatch.setattr(M.v17,"compare_one",lambda *_:{
        "T_actor_status":"T_ACTOR_AT_FROZEN_SOURCE",
        "T_actor_position":case["T_actor_position"],
        "T_actor_net_fuel_delta_KT":48})
    with pytest.raises(ValueError,match="outcome no longer reproducible"):
        M.post_audit(case,{}, {},(),frozenset())


def synthetic_v17_report():
    games=list(range(100,115))+[467386]
    wins=[{"game_id":g,"turn":turn,"edges":[]}
          for g in games for turn in (25,50,75)]
    original=[
        {**sample_case(g=w["game_id"],t=w["turn"],a=100+i,b=200+i,
                       src=(500,500),dst=(900,900)),
         "cohort":"ALL_TMINUS1_GATES_PASS",
         "single_failing_gate":None,
         "T_actor_status":(
             "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE" if i<13 else
             "ABSTAIN_T_OWNER_DRIFT" if i==13 else
             "T_ACTOR_AT_DISTINCT_FROZEN_TARGET"
         ),"T_actor_position":None if i<14 else [900,900],
         "T_actor_net_fuel_delta_KT":None if i<14 else 50,
        } for i,w in enumerate(wins[:98] if False else [wins[i%48] for i in range(98)])]
    # Force all positive distinct windows and ship identities (within each
    # window the ship id is deliberately different).
    negatives=[sample_case(g=wins[(i+20)%48]["game_id"],
                           t=wins[(i+20)%48]["turn"],
                           a=500+i,b=600+i,src=(500,500),dst=(550,500))
               for i in range(6)]
    negatives[0]=sample_case()
    for control in negatives[1:]:
        control["T_actor_status"]="T_ACTOR_AT_FROZEN_SOURCE"
        control["T_actor_position"]=list(control["source"])
        control["T_actor_net_fuel_delta_KT"]=0
    neg_non_discriminating=[
        {**sample_case(g=wins[(i+30)%48]["game_id"],t=wins[(i+30)%48]["turn"],
                       a=700+i,b=800+i,src=(500,500),dst=(500,500)),
         "Tminus1_source_differs_from_target":False,
         "T_actor_status":"NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"}
        for i in range(9)
    ]
    all_cases=original+negatives+neg_non_discriminating
    for x in all_cases:
        idx=next(j for j,w in enumerate(wins)
                 if w["game_id"]==x["game_id"] and w["turn"]==x["turn"])
        wins[idx]["edges"].append(x)
    return {
        "schema":M.v17.SCHEMA,"status":M.v17.STATUS,
        "source_db_sha256":M.SHA256,
        "source_v16_git_blob_sha1":M.v17.V16_BLOB,
        "summary":{
            "selected_game_count":16,"selected_window_count":48,
            "evaluated_windows":48,"context_abstentions":0,
            "candidate_stock_firecloud_edges":113,
            "discriminative_positive_Tminus1_edges":98,
            "discriminative_single_failed_Tminus1_edges":6,
            "non_discriminative_colocated_Tminus1_edges":9,
            "Tminus1_all_windows_frozen_before_T":True,
            "new_Host_movement_or_combat_predictions_promoted":0,
            "Chunnel_activation_proven":False,
            "Nplus1_VCR_used":False,"independent_new_corpus":False,
        },
        "windows":wins,
    }


def test_frozen_113_census_and_14_abstentions_are_provenance_guarded():
    doc=synthetic_v17_report()
    cases,windows=M.frozen_v17(doc)
    assert len(cases)==20
    assert len(windows)>=3
    doc["summary"]["candidate_stock_firecloud_edges"]=112
    with pytest.raises(ValueError,match="population"):
        M.frozen_v17(doc)
    doc=synthetic_v17_report()
    doc["windows"][0]["edges"][0]["Nplus1_VCR_used"]=True
    with pytest.raises(ValueError,match="proof boundary"):
        M.frozen_v17(doc)


def test_all_target_tminus1_frozen_before_any_T_read(monkeypatch):
    source=synthetic_v17_report()
    _targets,wins=M.frozen_v17(source)
    events=[]
    monkeypatch.setattr(M,"freeze_tminus1_window",lambda _conn,g,t,_cases:
        (events.append("pre") or {
            k:{"Tminus1_actor":{"start":[1141,1459]}} for k in _targets if k[:2]==(g,t)}))
    def post(_conn,*,game,turn):
        assert events.count("pre")==len(wins)
        events.append("post")
        return {}
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    monkeypatch.setattr(M,"_t_snapshots",lambda *_args:((),frozenset()))
    def audit(case,pre,*_rest):
        return {
            "game_id":case["game_id"],"turn":case["turn"],
            "initiator_ship_id":case["initiator_ship_id"],
            "target_ship_id":case["target_ship_id"],
            "V17_posthost_classification":case["T_actor_status"],
            "T_archive_visibility":{
                "T_source_owner_perspective_present":False,
                "T_fresh_ship_evidence":{"actor":{"T_owner_current_record_available":False}}},
        }
    monkeypatch.setattr(M,"post_audit",audit)
    report=M.build_report(object(),source)
    assert report["summary"]["reverified_Tminus1_T_cases"]==20
    assert report["summary"]["new_Host_movement_or_combat_predictions"]==0
    assert events.index("post")>max(i for i,x in enumerate(events) if x=="pre")


def test_runner_evidence_syntax_and_source_pin():
    run=ROOT/"tools/run-combat-c5-short-chunnel-and-visibility-audit-v18.sh"
    wrap=ROOT/"tools/run-combat-c5-short-chunnel-and-visibility-audit-v18-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    assert M.V17_BLOB in run.read_text()
    assert M.GENERATION in run.read_text()
    assert "/CURRENT" not in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrap.read_text()
