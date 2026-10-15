from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_phase_aware_firecloud_v12.py"
SPEC=importlib.util.spec_from_file_location("combat_phase_firecloud_v12",SCRIPT)
assert SPEC is not None and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def edge(src=293,dst=646,*,owner=10,source=(2513,1946),
         endpoint=(2504,1351),source_hull=56,target_hull=56,tow=False):
    return {
        "initiator_ship_id":src,"initiator_owner_id":owner,
        "initiator_hull_id":source_hull,"target_ship_id":dst,
        "target_hull_id":target_hull,
        "initiator_start":list(source),"target_Tminus1_position":list(endpoint),
        "target_Tminus1_warp":0,
        "numeric_FC_same_owner_fuel_distance_gates_only":True,
        "tow_order_on_initiator_or_target":tow,
    }


def ship(x,y,*,hull=56,warp=0,fuel=100):
    return {"x":x,"y":y,"hullid":hull,"warp":warp,"neutronium":fuel}


def window(edge_list,owner=10):
    rows={}
    for e in edge_list:
        s,t=e["initiator_ship_id"],e["target_ship_id"]
        x,y=e["initiator_start"]
        a,b=e["target_Tminus1_position"]
        rows[s]=(owner,ship(x,y,hull=e["initiator_hull_id"],fuel=140))
        rows[t]=(owner,ship(a,b,hull=e["target_hull_id"],fuel=30))
    return rows


def example(sid=325,*,game=245123,turn=75,owner=10,
            predicted=(2513,1946),observed=(2504,1351),start=(2512,1947)):
    return {
        "game_id":game,"turn":turn,"ship_id":sid,
        "Tminus1_owner_id":owner,"Tminus1_start":list(start),
        "frozen_normal_model_endpoint":list(predicted),
        "published_posthost_T_endpoint":list(observed),
        "cohort":"NORMAL_MINE_RISK_CONDITIONAL_NO_HIT",
        "canonical_chunnel_verified":False,
        "transport_or_mine_hit_attributed":False,
        "Nplus1_VCR_used":False,
    }


def test_exclude_nonfirecloud_fc_edges_and_preserve_stock_controls(monkeypatch):
    raw=[
        edge(src=325,source=(2512,1947),source_hull=14),
        edge(src=293,source=(2513,1946))
    ]
    rows=window(raw)
    def before(_conn,g,t):
        assert (g,t)==(245123,75)
        return rows,raw,{}
    monkeypatch.setattr(M.v11,"pre_window",before)
    frozen=M.freeze_tminus1_window(None,245123,75)
    assert frozen["Tminus1_all_numeric_fc_edges"]==2
    assert frozen["Tminus1_nonstock_numeric_fc_edges"]==1
    assert len(frozen["Tminus1_stock_firecloud_edges"])==1
    assert frozen["Tminus1_stock_firecloud_edges"][0]["initiator_ship_id"]==293
    assert frozen["Tminus1_stock_firecloud_edges"][0]["initiator_Tminus1_warp"]==0


def test_premove_factual_start_alone_is_inadequate_but_model_endpoint_joins():
    actor=edge()
    frozen={"Tminus1_stock_firecloud_edges":[{
        "initiator_ship_id":293,"target_ship_id":646,"owner_id":10,
        "initiator_Tminus1_position":[2513,1946],
        "target_Tminus1_position":[2504,1351],
        "initiator_Tminus1_fuel":140,"target_Tminus1_fuel":30,
        "initiator_Tminus1_warp":0,"target_Tminus1_warp":0,
        "Tminus1_tow_order_on_endpoints":False,
    }]}
    row=M.pre_join([example()],{(245123,75):frozen})[0]
    assert row["frozen_Tminus1_start"]==[2512,1947]
    assert row["frozen_Tminus1_pre_move_normal_endpoint"]==[2513,1946]
    assert row["Tminus1_without_T_observation_status"]=="PREMOVE_MODEL_ENDPOINT_AT_STOCK_FIRECLOUD_SOURCE"
    assert len(row["Tminus1_stock_firecloud_source_candidates"])==1
    returnrow=row


def test_posthost_actor_fuel_delta_not_proof_and_tampering_rejected():
    preedge={
        "initiator_ship_id":293,"target_ship_id":646,"owner_id":10,
        "initiator_Tminus1_position":[2513,1946],
        "target_Tminus1_position":[2504,1351],
        "initiator_Tminus1_fuel":140,"target_Tminus1_fuel":30,
        "Tminus1_tow_order_on_endpoints":False,
    }
    candidate=M.pre_join([example()],{(245123,75):{
        "Tminus1_stock_firecloud_edges":[preedge]
    }})[0]
    obs={
        325:(10,ship(2504,1351,hull=14)),
        293:(10,ship(2504,1351,fuel=90)),
        646:(10,ship(2504,1351,fuel=30)),
    }
    out=M.post_compare(candidate,obs)
    assert out["T_observation_comparison_status"]=="POSTHOC_T_ENDPOINT_CONCORDANT_WITH_PREMOVE_FIRECLOUD_EDGE"
    witness=out["T_actor_target_comparisons"][0]
    assert witness["T_actor_fuel_delta_exactly_50"] is True
    assert witness["T_actor_at_preselected_target"] is True
    assert witness["T_target_still_at_Tminus1_endpoint"] is True
    assert witness["chunnel_execution_proven"] is False
    assert out["new_host_position_prediction"] is False
    with pytest.raises(ValueError,match="independently reverified"):
        M.post_compare(candidate,{**obs,325:(10,ship(2505,1351,hull=14))})


def test_model_at_source_with_different_owner_does_not_join():
    e={
        "initiator_ship_id":377,"target_ship_id":581,"owner_id":6,
        "initiator_Tminus1_position":[2653,2074],
        "target_Tminus1_position":[3074,1914],
        "Tminus1_tow_order_on_endpoints":False,
    }
    good=example(211,game=306971,turn=116,owner=6,
                 predicted=(2653,2074),observed=(3074,1914),
                 start=(2652,2075))
    wrong=example(285,game=306971,turn=116,owner=7,
                  predicted=(2653,2074),observed=(3074,1914),
                  start=(2652,2075))
    out=M.pre_join([good,wrong],{(306971,116):{
        "Tminus1_stock_firecloud_edges":[e]
    }})
    assert len(out[0]["Tminus1_stock_firecloud_source_candidates"])==1
    assert not out[1]["Tminus1_stock_firecloud_source_candidates"]
    assert out[1]["Tminus1_without_T_observation_status"].startswith("NO_STOCK_")


def test_tow_blocks_join_but_does_not_establish_failed_chunnel():
    e={
        "initiator_ship_id":377,"target_ship_id":581,"owner_id":6,
        "initiator_Tminus1_position":[2653,2074],
        "target_Tminus1_position":[3074,1914],
        "Tminus1_tow_order_on_endpoints":True,
    }
    row=M.pre_join([
       example(211,game=306971,turn=116,owner=6,
               predicted=(2653,2074),observed=(3074,1914))
    ],{(306971,116):{"Tminus1_stock_firecloud_edges":[e]}})[0]
    assert row["Tminus1_without_T_observation_status"]=="ABSTAIN_ONLY_TOW_BLOCKED_FIRECLOUD_SOURCE"
    assert row["Tminus1_stock_firecloud_source_candidates"]==[]


def test_census_13_cases_reject_missing_duplicate_and_future_flag():
    windows=[{"game_id":g,"turn":t} for g,t in [
        (245123,38),(245123,75),(306971,116),(306971,231),
        (476826,96),(663317,54)
    ]]
    rows=[]
    alloc=[(245123,75,4),(306971,116,3),(245123,38,1),
           (306971,231,1),(476826,96,1),(663317,54,1),
           (245123,75,2)]
    for g,t,n in alloc:
        for _ in range(n):
            rows.append(example(100+len(rows),game=g,turn=t))
    source={
        "schema":M.V11_SCHEMA,"status":M.V11_STATUS,
        "source_v10_git_blob_sha1":M.v11.V10_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{
            "frozen_v9_mismatches":13,"frozen_v10_distinct_windows":6,
            "frozen_v10_distinct_games":4,
            "frozen_v10_correlated_clusters":2,
            "frozen_v10_correlated_ships":7,
            "Tminus1_pre_context_failures":0,
            "new_combat_or_movement_predictions":0,
            "chunnel_execution_proven":False,"Nplus1_VCR_read":False,
        },
        "residual_case_evaluations":rows,"window_evaluations":windows,
    }
    cases,pre=M.freeze_cases(source)
    assert len(cases)==13 and len(pre)==6
    source["residual_case_evaluations"][0]=dict(rows[1])
    with pytest.raises(ValueError,match="identity"):
        M.freeze_cases(source)
    source["residual_case_evaluations"][0]=dict(rows[0],Nplus1_VCR_used=True)
    with pytest.raises(ValueError,match="identity"):
        M.freeze_cases(source)


def test_runner_and_source_pin():
    script=ROOT/"tools/run-combat-c5-phase-aware-firecloud-v12.sh"
    wrapper=ROOT/"tools/run-combat-c5-phase-aware-firecloud-v12-with-evidence.sh"
    subprocess.run(["bash","-n",str(script)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.V11_BLOB in script.read_text()
    assert M.GENERATION in script.read_text()
    assert "/CURRENT" not in script.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
