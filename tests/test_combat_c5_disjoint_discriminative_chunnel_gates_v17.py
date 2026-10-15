from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools/diagnostics/combat_c5_disjoint_discriminative_chunnel_gates_v17.py"
SPEC=importlib.util.spec_from_file_location("combat_c5_discriminative_v17",P)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def e(source=(100,100),target=(450,100),*,gate=None,cohort="ALL_TMINUS1_GATES_PASS"):
    return {
        "initiator_ship_id":293,"target_ship_id":646,"owner_id":10,
        "source":list(source),"target":list(target),
        "actor_Tminus1_fuel":100,"target_Tminus1_fuel":50,
        "actor_Tminus1_warp":0,"target_Tminus1_warp":0,
        "Tminus1_distance_ly":350,
        "cohort":cohort,"single_failing_gate":gate,
        "actual_Chunnel_activation_proven":False,
    }


def observed(pos,target=(450,100),*,owner=10):
    return {293:(owner,{"x":pos[0],"y":pos[1],"hullid":56,"neutronium":50}),
            646:(10,{"x":target[0],"y":target[1],"hullid":56,"neutronium":45})}


def test_at_target_when_source_equals_target_is_not_a_success():
    raw={**e((100,100),(100,100),gate="DISTANCE_BELOW_100_AT_TMINUS1",
             cohort="ONE_TMINUS1_GATE_FAILS"),
        "game_id":1,"turn":2,
        "Tminus1_source_differs_from_target":False,
        "Tminus1_scoring_population":"NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"}
    row=M.compare_one(raw,observed((100,100),target=(100,100)))
    assert row["T_actor_status"]=="NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"
    assert row["T_coincident_actor_target_never_counted_as_positive"] is True
    assert row["Host_Chunnel_activation_or_inactivation_proven"] is False
    assert row["T_actor_net_fuel_delta_KT"]==50  # even 50 does not make it proof


def test_distinct_source_target_success_source_other_and_missing():
    raw={**e(),"Tminus1_source_differs_from_target":True,
         "game_id":1,"turn":2}
    assert M.compare_one(raw,observed((450,100)))["T_actor_status"]=="T_ACTOR_AT_DISTINCT_FROZEN_TARGET"
    assert M.compare_one(raw,observed((100,100)))["T_actor_status"]=="T_ACTOR_AT_FROZEN_SOURCE"
    assert M.compare_one(raw,observed((300,100)))["T_actor_status"]=="T_ACTOR_ELSEWHERE"
    assert M.compare_one(raw,{646:(10,{"x":450,"y":100,"hullid":56})})[
        "T_actor_status"]=="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"
    assert M.compare_one(raw,observed((450,100),owner=11))[
        "T_actor_status"]=="ABSTAIN_T_OWNER_DRIFT"


def test_freeze_classifies_geometry_before_outcomes(monkeypatch):
    roster={
        293:(10,{"x":100,"y":100,"hullid":56,"friendlycode":"646","warp":0,"neutronium":50}),
        646:(10,{"x":100,"y":100,"hullid":56,"friendlycode":"abc","warp":0,"neutronium":50}),
    }
    monkeypatch.setattr(M.v9,"pre_snapshots",lambda *_args,**_kw:((),()))
    monkeypatch.setattr(M,"group_perspective_records",lambda *_args:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_args:roster)
    actual=M.freeze_pre_window(None,123,50)
    assert len(actual["Tminus1_candidate_edges"])==1
    row=actual["Tminus1_candidate_edges"][0]
    assert row["Tminus1_scoring_population"]=="NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"
    assert row["cohort"]=="ONE_TMINUS1_GATE_FAILS"
    assert row["T_outcome_not_used_to_choose_or_score_populations"] is True


def test_prior_cohorts_and_published_v16_pin_exclusions(monkeypatch):
    monkeypatch.setattr(M.v14,"verify_source",lambda *_:frozenset(range(1,38)))
    fixed=[(g,t) for g in range(38,58) for t in (20,40,60)]
    monkeypatch.setattr(M.v15,"verify_v14",lambda *_:
                        (tuple(fixed),{key:{} for key in fixed}))
    collocated=[{"single_failing_gate":"DISTANCE_BELOW_100_AT_TMINUS1",
                 "source":[100,100],"target":[100,100]} for _ in range(14)]
    cases=collocated+[
        {"single_failing_gate":"INITIATOR_FUEL_LT50",
         "source":[100,100],"target":[450,100]}
        for _ in range(13)]
    report={
        "schema":M.v16.SCHEMA,"status":M.v16.STATUS,
        "source_v15_git_blob_sha1":M.v16.V15_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{
            "fixed_V14_windows":60,"fixed_V14_games":20,
            "frozen_original_V15_positive_actor_edges":95,
            "Tminus1_single_failed_gate_candidates":27,
            "all_forecasts_frozen_before_T":True,"future_VCR_used":False,
            "Host_Chunnel_activation_proven":False,
            "new_canonical_movement_or_combat_predictions":0,
        },
        "negative_single_failed_gate_cases":cases,
    }
    assert M.source_exclusions({}, {}, {}, {},report)==frozenset(range(1,58))
    report["negative_single_failed_gate_cases"][0]["target"]=[100,101]
    with pytest.raises(ValueError,match="zero-distance"):
        M.source_exclusions({}, {}, {}, {},report)


def test_metadata_selected_full_prephase_before_any_T(monkeypatch):
    events=[]
    class Conn:
        def execute(self,query):
            assert "source_members" in query and "vcr" not in query.lower()
            events.append("metadata")
            return self
        def fetchall(self):
            return [(g,t) for g in range(58,110) for t in range(1,9)]
    monkeypatch.setattr(M,"source_exclusions",lambda *_:frozenset(range(1,58)))
    def pre(_conn,g,t):
        events.append("PRE")
        return {"game_id":g,"turn":t,"Tminus1_candidate_edges":[],
                "Tminus1_absence_and_gate_counts":{},
                "Tminus1_all_selected_before_T":True}
    def post(_conn,*,game,turn):
        assert events.count("PRE")==48
        events.append("POST")
        return {}
    monkeypatch.setattr(M,"freeze_pre_window",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    result=M.build_report(Conn(),{},{},{},{},{})
    assert result["summary"]["selected_game_count"]==16
    assert result["summary"]["selected_window_count"]==48
    assert result["summary"]["candidate_stock_firecloud_edges"]==0
    assert result["summary"]["Tminus1_all_windows_frozen_before_T"] is True
    assert events.index("POST")>max(i for i,x in enumerate(events) if x=="PRE")


def test_shell_runners_are_pinned_and_readonly():
    run=ROOT/"tools/run-combat-c5-disjoint-discriminative-chunnel-gates-v17.sh"
    wrap=ROOT/"tools/run-combat-c5-disjoint-discriminative-chunnel-gates-v17-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    src=run.read_text()
    for sha in (M.V6_BLOB,M.V9_BLOB,M.V13_BLOB,M.V14_BLOB,M.V16_BLOB):
        assert sha in src
    assert M.GENERATION in src
    assert "/CURRENT" not in src
    assert "run-with-runtime-evidence.sh" in wrap.read_text()
