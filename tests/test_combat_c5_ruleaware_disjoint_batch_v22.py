from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_ruleaware_disjoint_batch_v22.py"
SPEC=importlib.util.spec_from_file_location("c5_ruleaware_v22",SCRIPT)
assert SPEC is not None and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def edge(*,owner=6,src=(100,100),dst=(125,100),gate="DISTANCE_BELOW_100_AT_TMINUS1"):
    return {
        "initiator_ship_id":467,"target_ship_id":80,"owner_id":owner,
        "source":list(src),"target":list(dst),
        "Tminus1_distance_ly":25,
        "cohort":"ONE_TMINUS1_GATE_FAILS" if gate else
                 "ALL_TMINUS1_GATES_PASS",
        "single_failing_gate":gate,
        "actor_Tminus1_fuel":70,
        "target_Tminus1_fuel":12,
        "actor_Tminus1_warp":0,"target_Tminus1_warp":0,
    }


def gate(owner=6,point=(120,120),eng=1):
    return {
        "ship_id":446,"owner_id":owner,
        "archived_catalog_name_confirms_dungeon_stargate":True,
        "Tminus1_position":list(point),
        "documentation_field_radius_ly":100+eng*50,
        "Tminus1_engine_id":eng,
    }


def test_short_distance_with_known_field_witness_is_not_an_activation_proof():
    features=M.field_features(edge(),[gate()],{}, {6:6})
    assert features["Tminus1_ruleaware_cohort"]=="SHORT_WITH_TMINUS1_STABILIZER_WITNESS"
    assert features["Tminus1_stabilization_field_witness"] is True
    assert features["Tminus1_phase_state_unproven"] is True
    assert features["Tminus1_stargate_source_coverage_candidates"][0]["active_at_Host_phase_proven"] is False
    assert features["Tminus1_stargate_source_coverage_candidates"][0]["target_also_inside_Tminus1_field"] is True


def test_rule_missing_is_abstain_not_disabled_and_stargate_outside_field():
    c=M.field_features(edge(),[gate(point=(500,500))],{}, {})
    assert c["Tminus1_ruleaware_cohort"]=="SHORT_NO_DOCUMENTED_STABILIZER_WITNESS"
    assert c["Tminus1_explicit_short_format_flag"] is None
    assert c["Tminus1_phase_state_unproven"] is True
    assert c["Tminus1_stargate_source_coverage_candidates"]==[]
    assert M.field_features(edge(),[],{"settings.shortformatrules":True},{6:6})[
        "Tminus1_ruleaware_cohort"]=="SHORT_WITH_TMINUS1_STABILIZER_WITNESS"
    assert M.field_features(edge(),[],{"settings.shortformatrules":True},{6:1})[
        "Tminus1_ruleaware_cohort"]=="SHORT_NO_DOCUMENTED_STABILIZER_WITNESS"


def test_colocation_overshadowing_and_long_conventional():
    collocated=edge(src=(100,100),dst=(100,100))
    assert M.field_features(collocated,[gate()],{}, {})["Tminus1_ruleaware_cohort"]=="NON_DISCRIMINATIVE_COLOCATED"
    long=edge(gate=None,dst=(400,100))
    assert M.field_features(long,[],{}, {})["Tminus1_ruleaware_cohort"]=="LONG_CONVENTIONAL_PASS"


def test_after_window_correctly_preserves_observed_owner_hull_abstentions():
    base={
        "game_id":123,"turn":10,
        "Tminus1_edges":[{**edge(),
            **M.field_features(edge(),[gate()],{}, {}),
            "Tminus1_source_target_distinct":True}],
        "Tminus1_stargates":[{**gate(),"hull_id":108,
                              "Tminus1_field_activation_verified":False}],
        "Tminus1_escorts":[{
            "game_id":123,"turn":10,
            "initiator_ship_id":467,"target_ship_id":80,
            "owner_id":6,"target":[125,100],
            "Tminus1_ruleaware_cohort":"SHORT_WITH_TMINUS1_STABILIZER_WITNESS",
            "Tminus1_stack":[{
                "ship_id":467,"owner_id":6,"Tminus1_hull_id":56,
                "Tminus1_fuel":70,"Tminus1_warp":0,"same_owner":True},
                {"ship_id":193,"owner_id":6,"Tminus1_hull_id":17,
                 "Tminus1_fuel":1,"Tminus1_warp":9,"same_owner":True},
            ]}],
    }
    current={
        467:(6,{"x":125,"y":100,"hullid":56,"neutronium":20}),
        80:(6,{"x":125,"y":100,"hullid":56}),
        193:(6,{"x":125,"y":100,"hullid":17,"neutronium":1}),
        446:(6,{"x":120,"y":120,"hullid":108,"engineid":1}),
    }
    actors,gates,stacks=M.after_window(base,current)
    assert actors[0]["T_actor_status"]=="T_ACTOR_AT_DISTINCT_TARGET"
    assert actors[0]["T_actor_net_fuel_loss_KT"]==50
    assert actors[0]["actual_Chunnel_execution_proven"] is False
    assert gates[0]["T_position_unchanged"] is True
    assert len(stacks)==1 and all(s["T_at_source_edge_target"] for s in stacks[0]["T_members"])
    assert all(s["true_Chunnel_passenger_proven"] is False for s in stacks[0]["T_members"])
    current[467]=(8,current[467][1])
    current[193]=(6,{"x":125,"y":100,"hullid":18})
    actors,_,stacks=M.after_window(base,current)
    assert actors[0]["T_actor_status"]=="ABSTAIN_T_OWNER_DRIFT"
    assert stacks[0]["T_members"][1]["T_owner_current_status"]=="ABSTAIN_T_HULL_IDENTITY_DRIFT"


def test_metadata_exclusions_all_v17_and_prior_games_no_future_vcr():
    earlier=list(range(1,58))
    selected=[{"game_id":g,"turn":t} for g in range(58,74) for t in (30,60,90)]
    source={
        "schema":M.v17.SCHEMA,"status":M.v17.STATUS,
        "source_db_sha256":M.SHA256,
        "summary":{"selected_game_count":16,"selected_window_count":48,
                   "candidate_stock_firecloud_edges":113,"Nplus1_VCR_used":False},
        "frozen_selection":{
            "no_ship_outcomes_or_VCR_in_selection":True,
            "excluded_V6_V9_V13_V14_game_ids":earlier,
            "game_turns":selected,
        },
    }
    v20={
        "schema":M.v20.SCHEMA,"status":M.v20.STATUS,
        "source_v17_git_blob_sha1":M.V17_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{"frozen_V17_short_distance_edges":13},
    }
    result=M.pinned_metadata_exclusions(source,v20)
    assert len(result)==73
    source["frozen_selection"]["game_turns"][0]["game_id"]=12
    with pytest.raises(ValueError,match="bad V17"):
        M.pinned_metadata_exclusions(source,v20)


def test_all_pre_windows_frozen_before_first_post(monkeypatch):
    events=[]
    class Meta:
        def execute(self,query):
            assert "source_members" in query and "vcr" not in query.lower()
            events.append("metadata")
            return self
        def fetchall(self):
            return [(g,t) for g in range(101,180) for t in range(1,10)]
    monkeypatch.setattr(M,"pinned_metadata_exclusions",lambda *_:frozenset(range(101,125)))
    def pre(_conn,g,t):
        events.append("PRE")
        return {"game_id":g,"turn":t,
                "Tminus1_edges":[],"Tminus1_stargates":[],
                "Tminus1_escorts":[],"Tminus1_rule_scalar_metadata":{},
                "Tminus1_frozen_before_any_T":True}
    def read(_conn,*,game,turn):
        assert events.count("PRE")==48
        events.append("POST")
        return {}
    monkeypatch.setattr(M,"pre_window",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",read)
    result=M.build_report(Meta(),{},{})
    assert len(result)==3
    assert all(x["summary"]["selected_windows"]==48 for x in result)
    assert all(x["summary"]["previous_research_game_overlap"]==0 for x in result)
    assert events.count("POST")==48
    assert events.index("POST")>max(i for i,x in enumerate(events) if x=="PRE")


def test_manifest_rejects_incomplete_output_and_single_batched_wrapper(tmp_path):
    empty=M.aggregate(
        {(g,t):{"Tminus1_edges":[],"Tminus1_stargates":[],
                "Tminus1_rule_scalar_metadata":{}}
         for g in range(100,116) for t in (30,60,90)},
        [([],[],[])],tuple((g,t) for g in range(100,116)
                           for t in (30,60,90)),
        frozenset(range(1,74)),[])
    M.publish_reports(tmp_path,empty)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_three_completed"] is True
    assert len(manifest["phase_reports"])==3
    assert all(len(x["sha256"])==64 for x in manifest["phase_reports"].values())
    runner=ROOT/"tools/run-combat-c5-ruleaware-disjoint-batch-v22.sh"
    wrapper=ROOT/"tools/run-combat-c5-ruleaware-disjoint-batch-v22-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.V17_BLOB in runner.read_text()
    assert M.V20_BLOB in runner.read_text()
    assert M.GENERATION in runner.read_text()
    assert "/CURRENT" not in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-ruleaware-disjoint-batch-v22/published" in wrapper.read_text()
