from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_chunnel_endpoint_screen_v11.py"
SPEC=importlib.util.spec_from_file_location("c5_chunnel_screen_v11",SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def ship(x,y,*,code="abc",hull=56,warp=1,gas=100,mission=0,target=0):
    return {"x":x,"y":y,"hullid":hull,"warp":warp,
            "friendlycode":code,"neutronium":gas,
            "mission":mission,"mission1target":target}


def sample_actors():
    # Ships 325 and 360 are passengers; initiator 50, warp0 destination 321.
    return {
        325:(10,ship(100,100,code="abc",hull=14)),
        360:(10,ship(100,100,code="abc",hull=14)),
        50:(10,ship(100,100,code="321",hull=56,gas=100)),
        321:(10,ship(500,300,code="abc",hull=56,warp=0,gas=20)),
        999:(5,ship(100,100,code="321",hull=56,gas=100)),
        700:(5,ship(500,300,code="abc",hull=56,warp=0,gas=20)),
    }


def test_friendly_code_is_three_numeric_digits_only():
    assert M.numeric_target("321")==321
    assert M.numeric_target("001")==1
    assert M.numeric_target("000")==0
    for raw in ("abc", "1", "12 ", "１２３", None, 321, "A21", "1234"):
        assert M.numeric_target(raw) is None


def test_exact_tminus1_conventional_edges_and_noncausal_flags():
    rows=sample_actors()
    edges,counts=M.screen_tminus1_edges(rows,{14:"Ship",56:"Firecloud Class Cruiser"})
    assert [(e["initiator_ship_id"],e["target_ship_id"]) for e in edges]==[(50,321)]
    assert edges[0]["initiator_start"]==[100,100]
    assert edges[0]["target_Tminus1_position"]==[500,300]
    assert edges[0]["distance_ly"]>100
    assert edges[0]["initiator_name_mentions_firecloud"] is True
    assert edges[0]["initiator_and_target_ability_independently_verified"] is False
    assert edges[0]["chunnel_execution_proven"] is False
    assert counts["NO_SAME_OWNER_FC_TARGET"]>=1


def test_negative_controls_target_warp0_fuel_owner_distance_and_tow():
    names={56:"Firecloud",14:"Other"}
    cases=[
        ({321:(10,ship(500,300,warp=1))},False),
        ({321:(10,ship(500,300,warp=0,gas=0))},False),
        ({321:(11,ship(500,300,warp=0,gas=20))},False),
        ({321:(10,ship(101,100,warp=0,gas=20))},False),
        ({50:(10,ship(100,100,code="321",gas=49))},False),
    ]
    for change,_ in cases:
        roster=sample_actors()
        roster.update(change)
        edges,_reasons=M.screen_tminus1_edges(roster,names)
        assert edges==()
    roster=sample_actors()
    roster[777]=(10,ship(100,100,code="zzz",mission=M.TOW_MISSION_ID,target=50))
    edges,_=M.screen_tminus1_edges(roster,names)
    assert len(edges)==1
    assert edges[0]["tow_order_on_initiator_or_target"] is True
    assert edges[0]["chunnel_execution_proven"] is False


def make_case(sid,*,game=245123,turn=75,owner=10,start=(100,100),end=(500,300)):
    return {"game_id":game,"turn":turn,"ship_id":sid,"owner_id":owner,
            "cohort":"NORMAL_MINE_RISK_CONDITIONAL_NO_HIT",
            "frozen_model_endpoint":[101,99],
            "Tminus1":{"Tminus1_start":list(start),"Tminus1_warp":1,
                        "Tminus1_fuel":900,"Tminus1_mission":1},
            "T_after_Host":{"T_posthost_position":list(end)}}


def test_posthoc_match_requires_reverified_owner_current_T():
    ship_id=325
    case=make_case(ship_id)
    rows=sample_actors()
    edges,_=M.screen_tminus1_edges(rows,{14:"Ship",56:"Firecloud"})
    out=M.observed_screen(case,rows,edges,{
        ship_id:(10,{"x":500,"y":300,"hullid":14})
    })
    assert out["Tminus1_candidate_edges_at_source_matching_T_endpoint"]==1
    assert out["canonical_chunnel_verified"] is False
    assert out["transport_or_mine_hit_attributed"] is False
    assert out["new_host_prediction"] is False
    with pytest.raises(ValueError,match="T endpoint disagrees"):
        M.observed_screen(case,rows,edges,{
            ship_id:(10,{"x":500,"y":301,"hullid":14})
        })
    with pytest.raises(ValueError,match="perspective unavailable"):
        M.observed_screen(case,rows,edges,{
            ship_id:(9,{"x":500,"y":300,"hullid":14})
        })


def test_shared_source_but_unmatched_endpoint_cannot_promote_mechanic():
    rows=sample_actors()
    edges,_=M.screen_tminus1_edges(rows,{14:"Ship",56:"Firecloud"})
    result=M.observed_screen(
        make_case(325,end=(700,300)),rows,edges,{
          325:(10,{"x":700,"y":300,"hullid":14})
        })
    assert result["Tminus1_candidate_edges_at_source_same_owner"]==1
    assert result["Tminus1_candidate_edges_at_source_matching_T_endpoint"]==0


def test_tminus1_graph_precedes_every_posthost_archive_read(monkeypatch):
    cases=[]
    windows=[(245123,75),(306971,116),(245123,38),
             (306971,231),(476826,96),(663317,54)]
    for i in range(13):
        game,turn=windows[i%6]
        cases.append(make_case(i+100,game=game,turn=turn,owner=10))
    events=[]
    def pre(_conn,game,turn):
        events.append(("pre",game,turn))
        these={c["ship_id"]:(10,ship(100,100,hull=14))
               for c in cases if (c["game_id"],c["turn"])==(game,turn)}
        return these,(),{}
    def post(_conn,*,game,turn):
        assert len([x for x in events if x[0]=="pre"])==6
        events.append(("post",game,turn))
        return {c["ship_id"]:(10,{"x":500,"y":300,"hullid":14})
                for c in cases if (c["game_id"],c["turn"])==(game,turn)}
    monkeypatch.setattr(M,"frozen_cases",lambda _source:tuple(cases))
    monkeypatch.setattr(M,"pre_window",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    report=M.build_report(None,{
        "posthoc_correlated_endpoint_groups":[
            {"game_id":245123,"turn":75,"size":4,"ship_ids":[
                c["ship_id"] for c in cases if c["game_id"]==245123 and c["turn"]==75][:4]},
            {"game_id":306971,"turn":116,"size":3,"ship_ids":[
                c["ship_id"] for c in cases if c["game_id"]==306971 and c["turn"]==116][:3]},
        ]
    })
    assert report["summary"]["new_combat_or_movement_predictions"]==0
    assert len(report["residual_case_evaluations"])==13
    assert events.index(next(e for e in events if e[0]=="post"))==6


def test_runner_wrapper_and_provenance():
    script=ROOT/"tools/run-combat-c5-chunnel-endpoint-screen-v11.sh"
    wrapper=ROOT/"tools/run-combat-c5-chunnel-endpoint-screen-v11-with-evidence.sh"
    subprocess.run(["bash","-n",str(script)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.V10_BLOB in script.read_text()
    assert M.GENERATION in script.read_text()
    assert "/CURRENT" not in script.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
