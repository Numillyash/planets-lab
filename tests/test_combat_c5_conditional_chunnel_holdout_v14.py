from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_conditional_chunnel_holdout_v14.py"
SPEC=importlib.util.spec_from_file_location("c5_chunnel_holdout_v14",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def candidate(sid=3,*,owner=2,source=(110,200),dest=(490,500),mine=False):
    return {
        "ship_id":sid,"Tminus1_owner_id":owner,
        "Tminus1_hull_id":14,
        "Tminus1_model_cohort":M.MINE if mine else M.NORMAL,
        "conditional_on_no_mine_interference":mine,
        "Tminus1_model_prechunnel_endpoint":list(source),
        "Tminus1_predicted_transport_destination":list(dest),
        "Tminus1_inferred_actual_arrival":False,
    }


def edge(*,actor=25,target=42,passengers=None,owner=2,source=(110,200),dest=(490,500)):
    return {
        "initiator_ship_id":actor,"target_ship_id":target,
        "owner_id":owner,"initiator_Tminus1_source":list(source),
        "target_Tminus1_destination":list(dest),
        "initiator_Tminus1_warp":0,
        "stock_hulls_verified_from_Tminus1":True,
        "execution_proven":False,
        "Tminus1_passenger_candidates":passengers or [],
    }


def pre(*edges,controls=None):
    return {
        "game_id":100,"turn":10,
        "status":"TMINUS1_PREOUTCOME_FROZEN",
        "T_archive_not_read_for_selection":True,
        "Tminus1_Firecloud_source_target_edges":list(edges),
        "Tminus1_negative_normal_controls":controls if controls is not None else [],
    }


def test_freeze_and_compare_chunnel_and_no_chunnel_baselines():
    frozen=M.freeze_conditional_cases(pre(
        edge(passengers=[candidate(3),candidate(4,mine=True)]),
        controls=[{"ship_id":7,"Tminus1_owner_id":2,"Tminus1_hull_id":14,
                   "Tminus1_model_endpoint":[115,200]}]))
    assert len(frozen["preoutcome_unambiguous_passenger_cases"])==2
    assert frozen["preoutcome_unambiguous_passenger_cases"][0]["activation_proven"] is False
    output=M.post_compare(frozen,{
        3:(2,{"x":490,"y":500,"hullid":14}),
        4:(2,{"x":110,"y":200,"hullid":14}),
        7:(2,{"x":115,"y":200,"hullid":14}),
    })
    got=output["T_conditional_passenger_comparisons"]
    assert [r["T_observation_status"] for r in got]==[
        "T_MATCHES_CONDITIONAL_CHUNNEL_ONLY","T_MATCHES_NORMAL_BASELINE_ONLY"]
    assert got[0]["Chunnel_execution_proven"] is False
    assert got[1]["mine_exposure_requires_no_hit_assumption"] is True
    assert output["T_nonexposed_normal_control_comparisons"][0][
        "T_normal_control_baseline_match"] is True


def test_missing_t_record_owner_hull_drift_and_neither_are_not_success():
    frozen=M.freeze_conditional_cases(pre(edge(passengers=[
        candidate(3),candidate(4),candidate(5),candidate(6)])))
    out=M.post_compare(frozen,{
        4:(3,{"x":490,"y":500,"hullid":14}),
        5:(2,{"x":490,"y":500,"hullid":16}),
        6:(2,{"x":222,"y":301,"hullid":14}),
    })
    assert [x["T_observation_status"] for x in out["T_conditional_passenger_comparisons"]]==[
        "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE",
        "ABSTAIN_T_OWNER_DRIFT",
        "ABSTAIN_T_HULL_IDENTITY_DRIFT",
        "T_MATCHES_NEITHER_BASELINE",
    ]


def test_double_candidate_for_one_ship_abstains_without_using_T():
    frozen=M.freeze_conditional_cases(pre(
        edge(actor=25,target=42,passengers=[candidate(3)]),
        edge(actor=26,target=43,passengers=[
            candidate(3,source=(111,200),dest=(500,501))],
             source=(111,200),dest=(500,501))))
    assert frozen["preoutcome_ambiguous_passenger_ids"]==[3]
    assert frozen["preoutcome_unambiguous_passenger_cases"]==[]


def test_source_feature_tampering_fail_closed():
    broken=edge(passengers=[candidate()])
    broken["stock_hulls_verified_from_Tminus1"]=False
    with pytest.raises(ValueError,match="source graph"):
        M.freeze_conditional_cases(pre(broken))
    bad=candidate()
    bad["Tminus1_model_prechunnel_endpoint"]=[99,99]
    with pytest.raises(ValueError,match="passenger identity"):
        M.freeze_conditional_cases(pre(edge(passengers=[bad])))
    with pytest.raises(ValueError,match="invalid/duplicate"):
        M.freeze_conditional_cases(pre(edge(passengers=[candidate()]),
            controls=[{"ship_id":3,"Tminus1_model_endpoint":[111,201]}]))


def test_v13_games_are_excluded_in_addition_to_v6_v9(monkeypatch):
    monkeypatch.setattr(M.v13,"excluded_games",lambda *_:frozenset({1,2,3}))
    summary={
        "selected_game_count":12,"selected_window_count":36,
        "game_overlap_with_V6_and_V9":0,
        "pre_or_post_context_errors":0,"post_context_evaluated_windows":36,
        "Tminus1_stock_firecloud_edges":52,
        "Tminus1_candidate_passenger_appearances":28,
        "new_Host_position_or_combat_predictions_promoted":0,
        "Nplus1_VCR_used":False,"Chunnel_execution_proven":False,
        "independent_new_corpus":False,
    }
    turns=[{"game_id":g,"turn":t} for g in range(10,22) for t in (30,60,90)]
    source={
        "schema":M.v13.SCHEMA,"status":M.v13.STATUS,
        "source_v6_git_blob_sha1":M.V6_BLOB,
        "source_v9_git_blob_sha1":M.V9_BLOB,
        "source_db_sha256":M.SHA256,"summary":summary,
        "source_metadata_selection":{
            "no_posthost_T_or_VCR_in_selection":True,
            "selected_windows":turns},
    }
    excluded=M.verify_source({}, {},source)
    assert excluded==frozenset({1,2,3,*range(10,22)})
    source["source_metadata_selection"]["selected_windows"][0]["game_id"]=1
    with pytest.raises(ValueError,match="overlap"):
        M.verify_source({}, {},source)


def test_all_pre_windows_frozen_before_any_T_archive(monkeypatch):
    events=[]
    class Metadata:
        def execute(self,query):
            assert "source_members" in query and "vcr" not in query.lower()
            events.append("metadata")
            return self
        def fetchall(self):
            return [(g,t) for g in range(100,161) for t in range(1,8)]
    monkeypatch.setattr(M,"verify_source",lambda *_:frozenset(range(100,120)))
    def pre_snap(_conn,*,game,before):
        events.append("snapshot")
        return (),()
    def freeze_window(game,turn,_snap,_raw):
        events.append("forecast")
        return {**pre(),"game_id":game,"turn":turn}
    def post(_conn,*,game,turn):
        assert events.count("forecast")==60
        events.append("post")
        return {}
    monkeypatch.setattr(M.v9,"pre_snapshots",pre_snap)
    monkeypatch.setattr(M.v13,"freeze_window",freeze_window)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    result=M.build_report(Metadata(),{}, {}, {})
    assert result["summary"]["selected_game_count"]==20
    assert result["summary"]["selected_window_count"]==60
    assert result["summary"]["frozen_unambiguous_candidate_passengers"]==0
    assert result["summary"]["new_production_Host_movement_or_combat_predictions"]==0
    assert events.index("post")>max(i for i,e in enumerate(events) if e=="forecast")


def test_runner_wrapper_and_pinned_source_blobs():
    runner=ROOT/"tools/run-combat-c5-conditional-chunnel-holdout-v14.sh"
    wrapper=ROOT/"tools/run-combat-c5-conditional-chunnel-holdout-v14-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    src=runner.read_text()
    assert M.V6_BLOB in src and M.V9_BLOB in src and M.V13_BLOB in src
    assert M.GENERATION in src
    assert "/CURRENT" not in src
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
