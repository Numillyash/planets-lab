from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"tools/diagnostics/combat_c5_moving_target_visibility_foreign_v27.py"
SPEC=importlib.util.spec_from_file_location("c5_moving_target_v27",TARGET)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def case(actor=143,target=202,g=403181,t=60,owner=1,
         src=(1509,2683),dst=(2326,2181),current=(2198,1799),
         target_t=(2198,1799),status="ELSEWHERE"):
    return {
        "game_id":g,"turn":t,"actor_id":actor,
        "target_ship_id":target,"owner_id":owner,
        "Tminus1_actor_source":list(src),"Tminus1_frozen_target":list(dst),
        "V25_endpoint_status":status,
        "T_actor_owner_current_status":"OWNER_CURRENT_T_OBSERVED",
        "T_target_owner_current_status":"OWNER_CURRENT_T_OBSERVED",
        "T_actor_position":list(current) if current else None,
        "T_target_position":list(target_t) if target_t else None,
        "T_target_moved_from_frozen_position":target_t!=dst if target_t else None,
        "T_actor_and_current_target_colocated":current==target_t if current and target_t else None,
    }


def test_original_mismatch_is_reinterpretable_but_not_rescored():
    rows=[case()]
    for i in range(55):
        rows.append(case(actor=500+i,target=800+i,g=521268,t=15+i,
                         src=(100,100),dst=(200,200),
                         current=(200,200),target_t=(200,200),
                         status="AT_DISTINCT_FROZEN_TARGET"))
    for i in range(2):
        rows.append(case(actor=388+i,target=192+i,g=521268,t=116,
                         src=(100,100),dst=(200,200),current=None,
                         target_t=None,status="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"))
    obj=M.moving_report(rows)
    assert obj["summary"]["frozen_V25_long_candidate_actor_rows"]==58
    assert obj["summary"]["G403181_T60_143_and_202_colocated_after_T"] is True
    assert obj["summary"]["conventional_55_1_2_scoring_not_retroactively_changed"] is True
    assert obj["summary"]["T_actor_target_colocation_by_original_V25_result"]["ELSEWHERE"][
        "T_ACTOR_WITH_CURRENT_TARGET"]==1
    rows[0]["T_target_position"]=[2326,2181]
    rows[0]["T_actor_and_current_target_colocated"]=False
    rows[0]["T_target_moved_from_frozen_position"]=False
    with pytest.raises(ValueError,match="no longer jointly observed"):
        M.moving_report(rows)


def test_pre_foreign_reads_only_Tminus1_and_enforces_owner_hull_warp_fuel(monkeypatch):
    source={
        270:(7,{"x":1200,"y":1900,"hullid":56,"warp":0,"neutronium":100}),
        239:(6,{"x":1200,"y":1900,"hullid":105,"warp":0,"neutronium":3,
                "mission":1,"targetx":1200,"targety":1900}),
        312:(6,{"x":1200,"y":1900,"hullid":104,"warp":0,"neutronium":141,
                "mission":1,"targetx":1335,"targety":1902}),
    }
    events=[]
    def pre(_conn,*,game,before):
        assert (game,before)==(521268,30)
        events.append("PRE")
        return (),()
    monkeypatch.setattr(M.v9,"pre_snapshots",pre)
    monkeypatch.setattr(M,"group_perspective_records",lambda *_:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_:source)
    e={
        "game_id":521268,"turn":31,"actor_id":270,"target_id":255,
        "actor_owner":7,"source":[1200,1900],"target":[1335,1902],
        "published_ships":[
            {"ship_id":239,"owner_id":6,"hull_id":105,"warp":0,"fuel":3,
             "T_at_frozen_target":True,"T_position":[1335,1902]},
            {"ship_id":312,"owner_id":6,"hull_id":104,"warp":0,"fuel":141,
             "T_at_frozen_target":True,"T_position":[1335,1902]},
        ],
    }
    result=M.pre_foreign(None,521268,31,[e])
    assert len(result)==2 and events==["PRE"]
    assert all(x["Tminus1_warp"]==0 for x in result)
    assert all("friendlycode" not in str(x) for x in result)
    assert result[1]["Tminus1_waypoint"]==[1335,1902]
    source[312][1]["neutronium"]=140
    with pytest.raises(ValueError,match="identity/position/order drift"):
        M.pre_foreign(None,521268,31,[e])


def test_foreign_warp0_is_not_direct_route_and_not_automatic_chunnel(monkeypatch):
    frozen=[]
    for i in range(8):
        frozen.append({
            "game_id":521268,"turn":31 if i<2 else 41+i,
            "actor_id":270+i,"actor_owner_id":7,
            "chunnel_target_id":255+i,
            "ship_id":239+i,"owner_id":6,"hull_id":105,
            "Tminus1_source":[1200,1900],"Tminus1_target":[1335,1902],
            "Tminus1_warp":0,"Tminus1_fuel":100,
            "Tminus1_waypoint":[1335,1902],
            "Tminus1_mission":1,
            "Tminus1_inbound_tow_request_ids":[],
            "V25_frozen_T_at_target":i!=7,
            "V25_frozen_T_position":[1335,1902] if i!=7 else [100,100],
        })
    post={}
    for x in frozen:
        key=x["game_id"],x["turn"]
        post.setdefault(key,{})[x["ship_id"]]=(
            6,{"x":1335 if x["V25_frozen_T_at_target"] else 100,
               "y":1902 if x["V25_frozen_T_at_target"] else 100,
               "hullid":105})
    doc=M.foreign_report(frozen,post)
    assert doc["summary"]["T_foreign_at_frozen_destination"]==7
    assert doc["summary"]["foreign_Tminus1_direct_waypoint_warp_possible"]==0
    assert doc["summary"]["frozen_foreign_owner_distinct_games"]==1
    assert all(x["co-location_is_not_automatic_passenger_eligibility"] for x in
               doc["frozen_foreign_owner_orders_T_endpoint_comparisons"])


def test_tplus1_visibility_is_posthoc_only_and_t_owner_perspective_required(monkeypatch):
    refs=lambda players:[SimpleNamespace(perspective_player_id=p) for p in players]
    def meta(_conn,*,game_id,turns,include_embedded_turn):
        assert (game_id,include_embedded_turn)==(521268,False)
        if turns=={116}:return refs(range(1,13))
        if turns=={117}:return refs(range(1,13))
        raise AssertionError(turns)
    after={
        388:(7,{"x":1152,"y":2243,"hullid":56}),
        577:(4,{"x":1152,"y":2243,"hullid":56}),
    }
    monkeypatch.setattr(M.v9,"member_refs_for_turns",meta)
    monkeypatch.setattr(M.v9,"after_owner_current",
                        lambda _conn,*,game,turn: after if turn==117 else {})
    obj=M.missing_report(None,{}, {(521268,116):{}})
    assert obj["summary"]["missing_actor_and_target_owner_current_pairs"]==2
    assert obj["summary"]["missing_distinct_game_turns"]==1
    assert obj["summary"]["no_VCR_used"] is True
    assert all(x["Tplus1_not_used_to_relabel_V25_or_infer_death"]
               for x in obj["T_owner_current_missing_and_Tplus1_followups"])
    assert {x["Tplus1_actor_status"] for x in obj[
        "T_owner_current_missing_and_Tplus1_followups"]}=={"OWNER_CURRENT_T_OBSERVED"}


def test_manifest_reports_and_single_evidence_wrapper(tmp_path):
    docs=tuple({**M.base(p),"summary":{}} for p in M.REPORTS)
    M.publish(tmp_path,docs)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_three_reports_complete"] is True
    assert manifest["relabel_V25_old_endpoint_scores"] is False
    assert manifest["Nplus1_VCR_used"] is False
    for n in M.REPORTS:
        assert manifest["report_sha256"][n]["sha256"]==hashlib.sha256(
            (tmp_path/(n+".json")).read_bytes()).hexdigest()
    runner=ROOT/"tools/run-combat-c5-moving-target-visibility-foreign-v27.sh"
    wrapper=ROOT/"tools/run-combat-c5-moving-target-visibility-foreign-v27-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    sh=runner.read_text()
    assert M.V26_BLOBS["manifest"] in sh
    assert M.V25_BLOBS["manifest"] in sh
    assert M.NEW_DB_SHA256 in sh
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-moving-target-visibility-foreign-v27/published" in wrapper.read_text()
    assert "--activate-current" not in sh.lower()
