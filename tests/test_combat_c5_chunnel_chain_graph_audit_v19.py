from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_chunnel_chain_graph_audit_v19.py"
SPEC=importlib.util.spec_from_file_location("combat_chunnel_graph_v19",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def edge(g,t,actor,target,src,dest,*,gate=None,owner=13,after=None,delta=50):
    is_short=gate is not None
    return {
        "game_id":g,"turn":t,"initiator_ship_id":actor,
        "target_ship_id":target,"owner_id":owner,
        "source":list(src),"target":list(dest),
        "cohort":"ONE_TMINUS1_GATE_FAILS" if is_short else
                 "ALL_TMINUS1_GATES_PASS",
        "single_failing_gate":gate,
        "Tminus1_distance_ly":1 if is_short else 668,
        "T_actor_status":"T_ACTOR_ELSEWHERE" if is_short else
                         "T_ACTOR_AT_DISTINCT_FROZEN_TARGET",
        "T_actor_position":list(after or dest),
        "T_actor_net_fuel_delta_KT":delta,
    }


def graph_fixture():
    windows=[
        {"game_id":g,"turn":50 if g==338264 else 75 if g==467386 else 22,
         "edges":[]} for g in [338264,467386,*range(100,146)]]
    assert len(windows)==48
    windows[0]["edges"].extend([
        edge(338264,50,204,116,(2971,1728),(2971,1727),
             gate=M.v17.v16.SHORT_GATE if hasattr(M.v17.v16,"SHORT_GATE")
               else "DISTANCE_BELOW_100_AT_TMINUS1",
             after=(2327,1527)),
        edge(338264,50,116,129,(2971,1727),(2327,1527)),
    ])
    windows[1]["edges"].append(
        edge(467386,75,467,80,(1141,1459),(1126,1439),
             gate="DISTANCE_BELOW_100_AT_TMINUS1",
             owner=6,after=(1126,1439),delta=48))
    for i in range(110):
        w=windows[i%48]
        w["edges"].append(edge(w["game_id"],w["turn"],1000+i,2000+i,
                               (100,100),(400,400),owner=10))
    return {"windows":windows}


def test_graph_detects_downstream_candidate_but_not_short_distance_proof():
    document=graph_fixture()
    graphs,chains=M.freeze_tminus1_graph(document)
    assert len(graphs)==48
    assert sum(map(len,graphs.values()))==113
    chain=[c for c in chains if c["game_id"]==338264]
    assert len(chain)==1
    assert (chain[0]["first_actor_id"],chain[0]["intermediate_firecloud_id"],
            chain[0]["second_target_id"])==(204,116,129)
    assert chain[0]["graph_only_not_activation_evidence"] is True
    assert not [c for c in chains if c["first_actor_id"]==467]
    originals={(e["game_id"],e["turn"],e["initiator_ship_id"],e["target_ship_id"]):e
               for w in document["windows"] for e in w["edges"]}
    result=M.posthoc_graph_comparison(chains,originals)
    assert result[0]["T_first_actor_at_downstream_target"] is True
    assert result[0]["T_second_actor_at_downstream_target"] is True
    assert result[0]["posthoc_correlation_not_chunnel_execution_proof"] is True


def test_graph_ignores_colocation_and_owner_mismatch_and_wrong_intermediate_site():
    document=graph_fixture()
    document["windows"][0]["edges"][0]["target"]=[2972,1727]
    _graphs,chains=M.freeze_tminus1_graph(document)
    assert chains==[]
    document=graph_fixture()
    document["windows"][0]["edges"][0]["owner_id"]=9
    _graphs,chains=M.freeze_tminus1_graph(document)
    assert chains==[]
    document=graph_fixture()
    document["windows"][0]["edges"][0]["source"]=[2971,1727]
    _graphs,chains=M.freeze_tminus1_graph(document)
    assert chains==[]


def test_malformed_graph_identity_rejected():
    doc=graph_fixture()
    doc["windows"][0]["edges"][0]["game_id"]=0
    with pytest.raises(ValueError,match="graph source"):
        M.freeze_tminus1_graph(doc)


def test_normal_route_abstention_does_not_become_no_movement(monkeypatch):
    def pre(*_args,**_kw):return ((),())
    monkeypatch.setattr(M.v9,"pre_snapshots",pre)
    monkeypatch.setattr(M,"group_perspective_records",lambda *_args:{})
    roster={
        204:(13,{"x":2971,"y":1728,"hullid":56,"warp":0,
                 "neutronium":60,"targetx":2971,"targety":1728}),
        116:(13,{"x":2971,"y":1727,"hullid":56,"warp":0,
                 "neutronium":90,"targetx":2971,"targety":1727}),
        129:(13,{"x":2327,"y":1527,"hullid":56,"warp":0,
                 "neutronium":80,"targetx":2327,"targety":1527}),
    }
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_args:roster)
    def model(*_args):raise ValueError("unknown warp-well settings")
    monkeypatch.setattr(M.v9,"forecast_pre_window",model)
    pre_result=M.freeze_focus_tminus1(None,338264,50)
    assert pre_result["Tminus1_model_context_abstention"]
    row=next(x for x in pre_result["selected_ship_rows"] if x["ship_id"]==204)
    assert row["Tminus1_normal_model_endpoint"] is None
    assert row["Tminus1_no_model_is_not_evidence_of_no_movement"] is True
    assert row["Tminus1_position"]==[2971,1728]


def test_T_owner_or_hull_changes_remain_abstentions():
    raw={
        "game_id":467386,"turn":75,
        "Tminus1_normal_forecasts_in_window":0,
        "Tminus1_model_context_abstention":{},
        "selected_ship_rows":[{
            "ship_id":467,"owner_id":6,"Tminus1_status":"OWNER_CURRENT",
            "Tminus1_position":[1141,1459],
            "Tminus1_waypoint":[1141,1459],
            "Tminus1_hull_id":56,
            "Tminus1_neutronium":51,
            "Tminus1_normal_model_endpoint":None,
        }],
    }
    a=M.post_focus(raw,{467:(9,{"x":1126,"y":1439,"hullid":56})})
    assert a["selected_ship_posthost_comparisons"][0][
        "T_observation_status"]=="ABSTAIN_T_OWNER_DRIFT"
    b=M.post_focus(raw,{467:(6,{"x":1126,"y":1439,"hullid":55})})
    assert b["selected_ship_posthost_comparisons"][0][
        "T_observation_status"]=="ABSTAIN_T_HULL_IDENTITY_DRIFT"


def test_all_pre_windows_before_any_posthost_and_25ly_stays_unknown(monkeypatch):
    doc=graph_fixture()
    events=[]
    monkeypatch.setattr(M,"source_precheck",lambda src,_: ({
        (e["game_id"],e["turn"],e["initiator_ship_id"],e["target_ship_id"]):e
        for window in src["windows"] for e in window["edges"]
    },()))
    def pre(_conn,g,t):
        events.append("pre")
        return {
            "game_id":g,"turn":t,
            "Tminus1_normal_forecasts_in_window":0,
            "Tminus1_model_context_abstention":{},
            "selected_ship_rows":[],
        }
    monkeypatch.setattr(M,"freeze_focus_tminus1",pre)
    def post(_conn,*,game,turn):
        assert events.count("pre")==2
        events.append("post")
        return {}
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    result=M.build_report(object(),doc,{})
    assert result["summary"]["frozen_V17_candidate_edges"]==113
    assert result["summary"]["G338264_T50_204_to_116_to_129_graph_chain_preselected"] is True
    assert result["summary"]["G467386_T75_467_to_80_has_outgoing_eligible_long_edge"] is False
    assert result["summary"]["short_Chunnel_or_activation_proven"] is False
    assert events==["pre","pre","post","post"]


def test_runner_and_wrapper_and_pinned_provenance():
    runner=ROOT/"tools/run-combat-c5-chunnel-chain-graph-audit-v19.sh"
    wrapper=ROOT/"tools/run-combat-c5-chunnel-chain-graph-audit-v19-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    script=runner.read_text()
    for sha in (M.V17_BLOB,M.V18_BLOB):
        assert sha in script
    assert M.GENERATION in script
    assert "/CURRENT" not in script
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
