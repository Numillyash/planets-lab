from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_posthost_residual_coupling_v10.py"
SPEC=importlib.util.spec_from_file_location("c5_v9_residual_v10",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def example(*,ship,game,turn,owner,hull,cohort,model,actual):
    return {
        "game_id":game,"after_turn":turn,"ship_id":ship,
        "Tminus1_owner_id":owner,"Tminus1_hull_id":hull,
        "Tminus1_source":("normal_mine_route_risk" if cohort==M.v9.MINE else "normal_move"),
        "comparison_status":"POSTHOST_ENDPOINT_MISMATCH",
        "T_owner_current_owner_id":owner,
        "conditional_or_model_endpoint":list(model),
        "T_owner_current_position":list(actual),
        "cohort":cohort,"Nplus1_vcr_used":False,
        "precombat_site_membership_proven":False,
        "mine_hit_or_nonhit_proven":False,
        "conditional_no_mine_only":cohort==M.v9.MINE,
    }


def pinned_source():
    mine=[
        example(ship=sid,game=245123,turn=75,owner=10,hull=14,
                cohort=M.v9.MINE,model=(2513,1946),actual=(2504,1351))
        for sid in (325,360,912,923)
    ]
    mine += [
        example(ship=499,game=245123,turn=75,owner=9,hull=52,
                cohort=M.v9.MINE,model=(2270,1889),actual=(2268,1887)),
        example(ship=639,game=245123,turn=75,owner=9,hull=99,
                cohort=M.v9.MINE,model=(2291,1980),actual=(2289,1978)),
        example(ship=314,game=306971,turn=231,owner=4,hull=35,
                cohort=M.v9.MINE,model=(1319,1882),actual=(1334,1910)),
        example(ship=358,game=476826,turn=96,owner=6,hull=52,
                cohort=M.v9.MINE,model=(1629,2491),actual=(1525,2374)),
        example(ship=129,game=663317,turn=54,owner=5,hull=46,
                cohort=M.v9.MINE,model=(1374,2679),actual=(1350,2619)),
    ]
    regular=[
        example(ship=364,game=245123,turn=38,owner=3,hull=95,
                cohort=M.v9.NORMAL,model=(1163,1701),actual=(1506,1539))
    ]
    regular += [
        example(ship=sid,game=306971,turn=116,owner=6,
                hull=(18 if sid!=369 else 69),
                cohort=M.v9.NORMAL,model=(2653,2074),actual=(3074,1914))
        for sid in (211,285,369)
    ]
    games=(2466,245123,306971,350094,421949,476826,597910,663317)
    windows=[{"game_id":g,"turn":turn} for g in games for turn in (38,75)]
    # Replace with actual 16 chosen windows, as in the pinned report.
    windows=[
        {"game_id":g,"turn":t}
        for g,t in [(2466,60),(2466,111),(245123,38),(245123,75),
                    (306971,116),(306971,231),(350094,60),(350094,119),
                    (421949,45),(421949,88),(476826,49),(476826,96),
                    (597910,93),(597910,185),(663317,28),(663317,54)]
    ]
    return {
        "schema":M.V9_SCHEMA,"status":M.V9_STATUS,"source_db_sha256":M.SHA256,
        "summary":{
            "selected_games":8,"selected_windows":16,"selected_games_overlap_with_C5":0,
            "pre_forecast_rows":3191,"posthost_compared_rows":3191,
            "window_context_abstentions":2,
            "new_Host_combat_predictions":0,"Nplus1_VCR_read":False,
            "cohort_posthost_status_counts":{
                M.v9.MINE:{"POSTHOST_ENDPOINT_MISMATCH":9},
                M.v9.NORMAL:{"POSTHOST_ENDPOINT_MISMATCH":4},
            },
        },
        "frozen_metadata_selection":{
            "no_VCR_selection":True,"selected_game_turns":windows,
        },
        "mismatch_examples":{M.v9.MINE:mine,M.v9.NORMAL:regular},
    }


def test_exact_frozen_residuals_and_correlated_clusters():
    rows,window=M.freeze_v9_residuals(pinned_source())
    assert len(rows)==13 and len(window)==16
    assert len({(r["game_id"],r["turn"]) for r in rows})==6
    groups=M.cross_case_groups(rows)
    assert sorted(x["size"] for x in groups)==[3,4]
    assert sum(x["size"] for x in groups)==7
    assert all(x["same_pair_of_endpoints_is_shared_effect_not_mechanic_proof"] for x in groups)


def test_future_leak_and_duplicate_comparator_are_rejected():
    doc=pinned_source()
    doc["mismatch_examples"][M.v9.MINE][0]["Nplus1_vcr_used"]=True
    with pytest.raises(ValueError,match="proof boundary"):
        M.freeze_v9_residuals(doc)
    doc=pinned_source()
    doc["mismatch_examples"][M.v9.MINE][0]=dict(
        doc["mismatch_examples"][M.v9.MINE][1])
    with pytest.raises(ValueError,match="proof boundary"):
        M.freeze_v9_residuals(doc)
    doc=pinned_source()
    doc["mismatch_examples"][M.v9.MINE][0]["comparison_status"]="POSTHOST_ENDPOINT_MATCH"
    with pytest.raises(ValueError,match="proof boundary"):
        M.freeze_v9_residuals(doc)


def test_tminus1_tow_order_is_evidence_not_tow_success():
    case=M.freeze_v9_residuals(pinned_source())[0][0]
    sid=case["ship_id"]
    ships={
        sid:(case["owner_id"],{
            "x":100,"y":200,"targetx":150,"targety":220,
            "hullid":case["hull_id"],"mission":0,
            "warp":9,"neutronium":100,"damage":0,
        }),
        555:(case["owner_id"],{
            "x":100,"y":200,"targetx":150,"targety":220,
            "mission":6,"mission1target":sid,
        }),
        556:(2,{"x":220,"y":200,"mission":6,"mission1target":sid}),
    }
    result=M.tminus1_orders(case,ships)
    assert result["Tminus1_same_start_other_ships"]==1
    assert result["Tminus1_same_start_same_waypoint_other_ships"]==1
    assert result["Tminus1_tow_orders_targeting_ship"]==[
        {"tower_ship_id":555,"tower_owner_id":case["owner_id"],
         "tower_colocated_in_Tminus1":True,
         "tower_Tminus1_position":[100,200],
         "tow_order_seen_not_success_proven":True},
        {"tower_ship_id":556,"tower_owner_id":2,
         "tower_colocated_in_Tminus1":False,
         "tower_Tminus1_position":[220,200],
         "tow_order_seen_not_success_proven":True},
    ]


def test_posthost_owner_current_recheck_and_no_causal_promotion():
    case=M.freeze_v9_residuals(pinned_source())[0][0]
    actual=tuple(case["frozen_T_owner_current_endpoint"])
    source={"Tminus1_start":[10,20],"Tminus1_damage":0}
    result=M.t_observational_check(case,source,{
        case["ship_id"]:(case["owner_id"],{
            "x":actual[0],"y":actual[1],
            "hullid":case["hull_id"],"damage":20,
        })
    })
    assert result["source_post_T_status"]=="OWNER_CURRENT_T_ENDPOINT_REVERIFIED"
    assert result["T_damage_delta"]==20
    assert result["mine_hit_or_tow_success_proven"] is False
    assert result["precombat_position_proven"] is False
    with pytest.raises(ValueError,match="observed T endpoint mismatch"):
        M.t_observational_check(case,source,{
            case["ship_id"]:(case["owner_id"],{
                "x":999,"y":999,"hullid":case["hull_id"]})
        })


def test_complete_pre_phase_before_T_read(monkeypatch):
    rows,selection=M.freeze_v9_residuals(pinned_source())
    source=pinned_source()
    events=[]
    def pre(_conn,*,game,before):
        events.append("pre")
        return ((),())
    def ship_groups(*_):
        return {}
    def after(_conn,*,game,turn):
        assert events.count("pre")==6
        events.append("post")
        subset=[x for x in rows if (x["game_id"],x["turn"])==(game,turn)]
        return {x["ship_id"]:(x["owner_id"],{
            "x":x["frozen_T_owner_current_endpoint"][0],
            "y":x["frozen_T_owner_current_endpoint"][1],
            "hullid":x["hull_id"],
        }) for x in subset}
    monkeypatch.setattr(M.v9,"pre_snapshots",pre)
    monkeypatch.setattr(M,"group_perspective_records",ship_groups)
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_:{})
    monkeypatch.setattr(M.v9,"after_owner_current",after)
    report=M.build_report(object(),source)
    assert report["summary"]["V9_endpoint_mismatches"]==13
    assert report["summary"]["posthoc_same_endpoint_clusters"]==2
    assert report["summary"]["posthoc_clustered_ship_count"]==7
    assert report["summary"]["new_Host_combat_or_movement_predictions"]==0
    assert events.index("post")>max(i for i,x in enumerate(events) if x=="pre")


def test_server_scripts_syntax_and_no_current():
    run=ROOT/"tools/run-combat-c5-posthost-residual-coupling-v10.sh"
    wrap=ROOT/"tools/run-combat-c5-posthost-residual-coupling-v10-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    assert M.V9_BLOB in run.read_text()
    assert "/CURRENT" not in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrap.read_text()
