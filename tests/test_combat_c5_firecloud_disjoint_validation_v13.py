from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_firecloud_disjoint_validation_v13.py"
SPEC=importlib.util.spec_from_file_location("combat_firecloud_disjoint_v13",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def ship(x,y,*,code="abc",hull=56,warp=0,fuel=200):
    return {"x":x,"y":y,"hullid":hull,"warp":warp,
            "friendlycode":code,"neutronium":fuel}


def roster():
    return {
        293:(10,ship(2513,1946,code="646",warp=0,fuel=122)),
        646:(10,ship(2504,1351,warp=0,fuel=32)),
        325:(10,ship(2512,1947,hull=14,warp=1)),
        999:(9,ship(2513,1946,warp=1)),
        700:(10,ship(2500,1900,hull=14,warp=2)),
    }


def forecast(sid,owner,pos,*,mine=False,hull=14):
    return {"ship_id":sid,"Tminus1_owner_id":owner,
            "Tminus1_hull_id":hull,
            "Tminus1_source":"normal_mine_route_risk" if mine else "normal_move",
            "cohort":M.v9.MINE if mine else M.v9.NORMAL,
            "conditional_or_model_endpoint":list(pos),
            "conditional_no_mine_only":mine}


def test_game_and_turn_selection_uses_only_metadata():
    metadata=[(g,t) for g in range(1,61) for t in range(1,11)]
    old=frozenset(range(1,26))
    selected=M.choose_windows(metadata,old)
    assert selected==M.choose_windows(list(reversed(metadata)),old)
    assert len(selected)==36
    assert len({g for g,_ in selected})==12
    assert all(g not in old and t>1 for g,t in selected)
    assert len(set(selected))==36
    with pytest.raises(ValueError,match="insufficient"):
        M.choose_windows([(1,2),(1,3)],frozenset())
    with pytest.raises(ValueError,match="invalid source_members"):
        M.choose_windows([(1,True)],frozenset())


def test_stock_firecloud_positive_and_nonstock_false_positive():
    r=roster()
    r[300]=(10,ship(2600,2000,code="646",hull=14,warp=0))
    edges,ex=M.eligible_edges(r,{56:"Firecloud Class Cruiser",14:"Fuel Carrier"})
    assert [(e["initiator_ship_id"],e["target_ship_id"]) for e in edges]==[(293,646)]
    assert ex["NON_STOCK_FIRECLOUD_NUMERIC_FC_EDGE"]==1
    assert edges[0]["execution_proven"] is False


def test_ambiguous_target_id_fails_closed_and_tow_blocks():
    rows=roster()
    rows[1646]=(10,ship(2400,1300,warp=0))
    edges,why=M.eligible_edges(rows,{56:"Firecloud",14:"Fuel Carrier"})
    assert not edges
    assert why["AMBIGUOUS_TARGET_IDS_ABSTAIN"]==2
    rows=roster()
    rows[777]=(10,{"x":1,"y":1,"hullid":14,"warp":1,"neutronium":1,
                    "friendlycode":"abc",
                    "mission":M.v11.TOW_MISSION_ID,"mission1target":293})
    edges,why=M.eligible_edges(rows,{56:"Firecloud",14:"Fuel Carrier"})
    assert not edges
    assert why["TOW_REQUEST_ENDPOINT_UNRESOLVED"]==1


def test_phase_frozen_passengers_only_from_independent_normal_endpoint(monkeypatch):
    monkeypatch.setattr(M,"group_perspective_records",lambda *_a:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_a:roster())
    monkeypatch.setattr(M.v11,"hull_name_inventory",
                        lambda _raw:{56:"Firecloud",14:"Fuel Carrier"})
    monkeypatch.setattr(M.v9,"forecast_pre_window",
        lambda _g,_t,_s,_r:([
            forecast(325,10,(2513,1946),mine=True),
            forecast(999,9,(2513,1946)),
            forecast(700,10,(2510,1920)),
        ],Counter(),len(roster())))
    result=M.freeze_window(1,50,(),())
    assert len(result["Tminus1_Firecloud_source_target_edges"])==1
    passengers=result["Tminus1_Firecloud_source_target_edges"][0]["Tminus1_passenger_candidates"]
    assert [p["ship_id"] for p in passengers]==[325]
    assert passengers[0]["conditional_on_no_mine_interference"] is True
    assert passengers[0]["Tminus1_inferred_actual_arrival"] is False
    assert [c["ship_id"] for c in result["Tminus1_negative_normal_controls"]]==[700]


def window_fixture():
    return {
        "game_id":1,"turn":50,
        "Tminus1_Firecloud_source_target_edges":[{
            "initiator_ship_id":293,"target_ship_id":646,"owner_id":10,
            "initiator_Tminus1_source":[2513,1946],
            "target_Tminus1_destination":[2504,1351],
            "initiator_Tminus1_fuel":122,
            "target_Tminus1_fuel":32,
            "Tminus1_passenger_candidates":[{
                "ship_id":325,"Tminus1_owner_id":10,
                "Tminus1_hull_id":14,
                "Tminus1_model_cohort":M.v9.MINE,
                "conditional_on_no_mine_interference":True,
                "Tminus1_model_prechunnel_endpoint":[2513,1946],
                "Tminus1_predicted_transport_destination":[2504,1351],
                "Tminus1_inferred_actual_arrival":False,
            }],
        }],
        "Tminus1_negative_normal_controls":[{
            "ship_id":700,"Tminus1_owner_id":10,
            "Tminus1_hull_id":14,
            "Tminus1_model_endpoint":[2510,1920],
            "selection_did_not_use_T_archive":True,
        }]
    }


def test_posthost_signature_and_negative_controls_do_not_infer_execution():
    result=M.evaluate_window(window_fixture(),{
        293:(10,{"x":2504,"y":1351,"neutronium":72,"hullid":56}),
        646:(10,{"x":2504,"y":1351,"hullid":56}),
        325:(10,{"x":2504,"y":1351,"hullid":14}),
        700:(10,{"x":2510,"y":1920,"hullid":14}),
    })
    edge=result["Tminus1_Firecloud_edge_observations"][0]
    assert edge["T_actor_target_observational_signature"]=="SUPPORTIVE_TARGET_AND_50KT_CONCORDANCE"
    assert edge["Chunnel_executed_proven"] is False
    assert edge["posthost_passengers"][0]["T_observation_status"]=="T_PASSENGER_AT_PRESELECTED_TARGET"
    assert edge["posthost_passengers"][0]["Chunnel_transport_proven"] is False
    assert result["Tminus1_negative_normal_control_observations"][0]["T_model_endpoint_match"] is True


def test_missing_owner_drift_and_fuel_delta10_are_not_success():
    result=M.evaluate_window(window_fixture(),{
        293:(10,{"x":2504,"y":1351,"neutronium":112,"hullid":56}),
        646:(10,{"x":2504,"y":1351,"hullid":56}),
        325:(11,{"x":2504,"y":1351,"hullid":14}),
    })
    edge=result["Tminus1_Firecloud_edge_observations"][0]
    assert edge["T_actor_fuel_delta_KT"]==10
    assert edge["T_actor_target_observational_signature"]=="OBSERVATIONAL_SIGNATURE_NOT_CONFIRMED"
    assert edge["posthost_passengers"][0]["T_observation_status"]=="ABSTAIN_T_OWNER_DRIFT"
    assert edge["posthost_passengers"][0]["T_endpoint_matches_preselected_target"] is None


def test_complete_prephase_before_any_postarchive(monkeypatch):
    events=[]
    class DB:
        def execute(self,q):
            assert "source_members" in q and "vcr" not in q.lower()
            events.append("metadata")
            return self
        def fetchall(self):
            return [(g,t) for g in range(101,141) for t in range(1,8)]
    monkeypatch.setattr(M,"excluded_games",lambda *_:frozenset(range(1,26)))
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *_args,**_kwargs:((),()))
    def freeze(g,t,_snap,_raw):
        events.append("pre")
        return {"game_id":g,"turn":t,
                "Tminus1_Firecloud_source_target_edges":[],
                "Tminus1_negative_normal_controls":[]}
    monkeypatch.setattr(M,"freeze_window",freeze)
    def after(*_args,**_kwargs):
        assert events.count("pre")==36
        events.append("post")
        return {}
    monkeypatch.setattr(M.v9,"after_owner_current",after)
    result=M.build_report(DB(),{}, {})
    assert result["summary"]["selected_game_count"]==12
    assert result["summary"]["selected_window_count"]==36
    assert result["summary"]["Tminus1_stock_firecloud_edges"]==0
    assert result["summary"]["new_Host_position_or_combat_predictions_promoted"]==0
    assert events.index("post")>max(i for i,x in enumerate(events) if x=="pre")


def test_runner_and_evidence_wrapper_are_pinned():
    runner=ROOT/"tools/run-combat-c5-firecloud-disjoint-validation-v13.sh"
    evidence=ROOT/"tools/run-combat-c5-firecloud-disjoint-validation-v13-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(evidence)],check=True)
    src=runner.read_text()
    assert M.V6_BLOB in src and M.V9_BLOB in src
    assert M.GENERATION in src
    assert "/CURRENT" not in src
    assert "run-with-runtime-evidence.sh" in evidence.read_text()
