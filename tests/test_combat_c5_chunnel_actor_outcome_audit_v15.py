from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_chunnel_actor_outcome_audit_v15.py"
SPEC=importlib.util.spec_from_file_location("combat_c5_actor_audit_v15",SCRIPT)
assert SPEC is not None and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def edge(actor=293,target=646,owner=10,source=(2513,1946),
         dest=(2504,1351),initial=150,npass=0):
    return {
        "initiator_ship_id":actor,"target_ship_id":target,"owner_id":owner,
        "initiator_Tminus1_source":list(source),
        "target_Tminus1_destination":list(dest),
        "initiator_Tminus1_fuel":initial,
        "initiator_Tminus1_warp":0,
        "Tminus1_passenger_candidates":[{"ship_id":n+100} for n in range(npass)],
    }


def test_actor_at_target_and_net_fuel_50_are_independent_observations():
    e=edge()
    result=M.actor_edge_after(e,{
        293:(10,{"x":2504,"y":1351,"hullid":56,"neutronium":100}),
        646:(10,{"x":2504,"y":1351,"hullid":56,"neutronium":30}),
    },245123,75)
    assert result["T_actor_observation_status"]=="T_ACTOR_AT_FROZEN_TARGET"
    assert result["T_target_stayed_at_frozen_target"] is True
    assert result["T_actor_net_fuel_delta_KT"]==50
    assert result["T_actor_net_delta_exactly_50"] is True
    assert result["Chunnel_execution_proven"] is False


def test_chained_target_or_tow_displacement_and_missing_stay_abstained():
    candidate=edge()
    for source,target,status in [
        ({"x":2513,"y":1946,"hullid":56,"neutronium":150},
         {"x":2504,"y":1351,"hullid":56},
         "T_ACTOR_STILL_AT_TMINUS1_SOURCE"),
        ({"x":2400,"y":1351,"hullid":56,"neutronium":100},
         {"x":2400,"y":1351,"hullid":56},
         "T_ACTOR_AT_OTHER_POSITION"),
    ]:
        out=M.actor_edge_after(candidate,{293:(10,source),646:(10,target)},1,2)
        assert out["T_actor_observation_status"]==status
        assert out["Chunnel_execution_proven"] is False
    missing=M.actor_edge_after(candidate,{293:(11,{"x":2504,"y":1351,"hullid":56}),
                                            646:(10,{"x":2504,"y":1351,"hullid":56})},1,2)
    assert missing["T_actor_observation_status"]=="ABSTAIN_T_OWNER_DRIFT"
    assert missing["T_actor_passage_consistent_with_target"] is None


def test_negative_controls_use_posthoc_matches_only_not_new_predictions():
    actors=[M.actor_edge_after(edge(),{
        293:(10,{"x":2504,"y":1351,"hullid":56,"neutronium":100}),
        646:(10,{"x":2504,"y":1351,"hullid":56}),
    },1,2)]
    control={"ship_id":3,"Tminus1_owner_id":10,
             "Tminus1_hull_id":14,"Tminus1_model_endpoint":[2512,1946]}
    prior={"Tminus1_start":[2510,1946],"Tminus1_waypoint":[2512,1946],
           "Tminus1_warp":1}
    r=M.negative_comparison(control,prior,{
        3:(10,{"x":2504,"y":1351,"hullid":14})
    },actors,1,2)
    assert r["status"]=="MISMATCH"
    assert r["Tminus1_normal_input"]["Tminus1_warp"]==1
    assert r["POSTHOC_T_position_matches_another_eligible_target"]==[
        {"initiator_ship_id":293,"target_ship_id":646}]
    assert r["Tminus1_distance_to_nearest_eligible_Firecloud_source"]>0
    assert r["mine_hit_or_Chunnel_transport_proven"] is False
    no_observation=M.negative_comparison(control,prior,{},actors,1,2)
    assert no_observation["status"]=="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"


def test_crosscheck_pinned_v14_fails_on_corrupt_posthost_comparison(monkeypatch):
    case={
        "game_id":1,"turn":2,
        "preoutcome_unambiguous_passenger_cases":[],
        "preoutcome_nonexposed_negative_controls":[{
            "ship_id":3,"Tminus1_owner_id":10,
            "Tminus1_hull_id":14,"Tminus1_model_endpoint":[9,9]}],
        "preoutcome_eligible_edges":0,"preoutcome_ambiguous_passenger_ids":[],
    }
    original={
        "T_conditional_passenger_comparisons":[],
        "T_nonexposed_normal_control_comparisons":[{
            "ship_id":3,"status":"OWNER_CURRENT_T_OBSERVED",
            "T_normal_control_baseline_match":True}]
    }
    M.revalidate_v14_comparison(original,case,{
        3:(10,{"x":9,"y":9,"hullid":14})},1,2)
    with pytest.raises(ValueError,match="negative controls drift"):
        M.revalidate_v14_comparison(original,case,{
            3:(10,{"x":8,"y":9,"hullid":14})},1,2)


def v14_doc():
    games=range(101,121)
    windows=[{"game_id":g,"turn":t} for g in games for t in (30,60,90)]
    return {
        "schema":M.v14.SCHEMA,"status":M.v14.STATUS,
        "source_v6_git_blob_sha1":M.v14.V6_BLOB,
        "source_v9_git_blob_sha1":M.v14.V9_BLOB,
        "source_v13_git_blob_sha1":M.v14.V13_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{
            "selected_game_count":20,"selected_window_count":60,
            "V6_V9_V13_game_overlap":0,"completed_windows":60,
            "context_abstentions":0,
            "eligible_Tminus1_Firecloud_edges_in_completed_windows":95,
            "frozen_unambiguous_candidate_passengers":55,
            "ambiguous_passenger_exclusions":0,
            "new_production_Host_movement_or_combat_predictions":0,
            "Chunnel_execution_independently_proven":False,
            "Nplus1_VCR_used":False,"new_independent_corpus":False,
            "T_passenger_conditional_vs_baseline_counts":{
                "T_MATCHES_CONDITIONAL_CHUNNEL_ONLY":55},
            "T_negative_normal_control_counts":{
                "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":1,
                "ABSTAIN_T_HULL_IDENTITY_DRIFT":1,
                "ABSTAIN_T_OWNER_DRIFT":4,
                "MATCH":526,"MISMATCH":8,
            },
        },
        "frozen_selection":{
            "no_VCR_or_T_outcome_selection":True,
            "selected_game_turns":windows,
        },
        "window_evaluations":[{
            "game_id":row["game_id"],"turn":row["turn"],
            "T_conditional_passenger_comparisons":[],
            "T_nonexposed_normal_control_comparisons":[]
        } for row in windows],
    }


def test_frozen_60_window_identifiers_not_future_selected():
    r=v14_doc()
    rows, bywindow=M.verify_v14(r,frozenset(range(1,26)))
    assert len(rows)==60 and len(bywindow)==60
    r["frozen_selection"]["selected_game_turns"][0]["game_id"]=1
    with pytest.raises(ValueError,match="overlap"):
        M.verify_v14(r,frozenset(range(1,26)))
    r=v14_doc()
    r["summary"]["T_negative_normal_control_counts"]["MISMATCH"]=7
    with pytest.raises(ValueError,match="denominator"):
        M.verify_v14(r,frozenset(range(1,26)))


def test_full_pre_phase_before_any_T_and_denominator_invariants(monkeypatch):
    report=v14_doc()
    events=[]
    # A synthetic exact 95-edge/540-control population, preserving
    # 60-window order, without making runtime DB calls in unit tests.
    windows=tuple(sorted((w["game_id"],w["turn"]) for w in
                          report["frozen_selection"]["selected_game_turns"]))
    def fake_pre(_conn,game,turn):
        events.append(("PRE",game,turn))
        i=windows.index((game,turn))
        count_edges=2 if i<35 else 1  # 35*2 + 25 = 95
        edges=[edge(actor=100+j,target=300+j) for j in range(count_edges)]
        controls=[{
            "ship_id":j+1,"Tminus1_owner_id":10,
            "Tminus1_hull_id":14,"Tminus1_model_endpoint":[100+j,200],
        } for j in range(9)]
        return {
            "game_id":game,"turn":turn,
            "features":{
                "Tminus1_Firecloud_source_target_edges":edges,
                "Tminus1_negative_normal_controls":controls,
            },
            "conditional_cases":{},
            "negative_control_Tminus1_features":{
                j+1:{"Tminus1_start":[90+j,200]} for j in range(9)},
        }
    def fake_after(_conn,*,game,turn):
        assert sum(x[0]=="PRE" for x in events)==60
        events.append(("POST",game,turn))
        return {}
    # Only the phase barrier and immutable denominators are tested
    # here; exact post-Host comparator consistency has its own test.
    def fake_crosscheck(*_args):return None
    monkeypatch.setattr(M.v14,"verify_source",lambda *_:frozenset())
    monkeypatch.setattr(M,"pre_window",fake_pre)
    monkeypatch.setattr(M.v9,"after_owner_current",fake_after)
    monkeypatch.setattr(M,"revalidate_v14_comparison",fake_crosscheck)
    with pytest.raises(ValueError,match="negative control observational denominator drift"):
        M.build_report(object(),{},{},{},report)
    assert sum(x[0]=="PRE" for x in events)==60
    assert sum(x[0]=="POST" for x in events)==60
    assert min(i for i,x in enumerate(events) if x[0]=="POST")>max(
        i for i,x in enumerate(events) if x[0]=="PRE")


def test_server_wrappers_and_git_source_pins():
    run=ROOT/"tools/run-combat-c5-chunnel-actor-outcome-audit-v15.sh"
    wrap=ROOT/"tools/run-combat-c5-chunnel-actor-outcome-audit-v15-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    assert M.V14_BLOB in run.read_text()
    assert "/CURRENT" not in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrap.read_text()
