from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_new_corpus_exception_batch_v26.py"
SPEC=importlib.util.spec_from_file_location("c5_new_corpus_v26",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def observations():
    selected=[233802,290449,403181,444043,469931,521268,536676,608293]
    rows=[]
    for i in range(106):
        if i==0:g,t,s,d,status=403181,60,143,202,"ELSEWHERE"
        elif i==1:g,t,s,d,status=521268,116,388,192,"ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"
        elif i==2:g,t,s,d,status=521268,116,577,240,"ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"
        else:
            g=selected[(i-3)%8]
            t=15+((i-3)//8)*2
            s=1000+i; d=2000+i
            status="AT_DISTINCT_FROZEN_TARGET"
        if i<58:
            cohort="LONG_CONVENTIONAL_PASS"
            rawcohort="ALL_TMINUS1_GATES_PASS"
        elif i<96:
            cohort="NON_DISCRIMINATIVE_COLOCATED"
            rawcohort="ALL_TMINUS1_GATES_PASS"
        else:
            cohort="OTHER_SINGLE_FAILED_GATE"
            rawcohort="ONE_TMINUS1_GATE_FAILS"
            status="AT_SOURCE" if i<105 else "ELSEWHERE"
        if i==0:src,dst,found=[1509,2683],[2326,2181],[2198,1799]
        elif i in (1,2):src,dst,found=[1300,2100],[1152,2243],None
        else:
            src=[100,100]
            dst=[100,100] if i<96 and i>=58 else [200,200]
            found=(dst if status=="AT_DISTINCT_FROZEN_TARGET"
                   else src if status=="AT_SOURCE"
                   else [300,300])
        rows.append({
            "game_id":g,"turn":t,"initiator_ship_id":s,"target_ship_id":d,
            "owner_id":1 if i==0 else 7 if i==1 else 4 if i==2 else 6,
            "T_status":status,"T_position":found,
            "Tminus1_cohort":cohort,"cohort":rawcohort,
            "single_failing_gate":None if rawcohort=="ALL_TMINUS1_GATES_PASS" else "INITIATOR_FUEL_LT50",
            "source":src,"target":dst,
        })
    assert len(rows)==106
    return rows,selected


def test_published_provenance_needs_exact_counts_sha_and_three_residuals():
    rows,selected=observations()
    # The production original data has 33 windows, while the synthetic
    # per-case construction uses more windows. Explicitly reject drift.
    groups={(r["game_id"],r["turn"]) for r in rows}
    assert len(groups)!=33
    for x in rows[3:]:
        x["game_id"]=selected[0]
        x["turn"]=15+((rows.index(x)-3)%31)*2
    # Keep three original residual identities untouched.
    groups={(r["game_id"],r["turn"]) for r in rows}
    assert len(groups)==33
    actor={"schema":"planets-lab.combat-c5-new-game-corpus-batch.v25",
           "status":"NEWLY_ACQUIRED_GAME_DISJOINT_RETROSPECTIVE_TMINUS1_RULEAWARE_OBSERVATIONAL",
           "phase":"actors","generation_sha256":M.GENERATION_SHA,
           "Nplus1_VCR_used":False,"Tminus1_frozen_before_first_T":True,
           "summary":{"selected_disjoint_games":8,"baseline_games_excluded":100,
                      "metadata_selected_adjacent_windows":192,"Tminus1_contexts_available":192,
                      "posthost_compared_windows":33,"Tminus1_stock_chunnel_candidate_edges":106,
                      "short_Tminus1_documented_field_witnesses":0,
                      "context_errors":0,
                      "T_endpoint_by_cohort":{"LONG_CONVENTIONAL_PASS":{
                          "AT_DISTINCT_FROZEN_TARGET":55,
                          "ELSEWHERE":1,
                          "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":2}}},
           "preselected_actor_Tminus1_T_observations":rows}
    fields={"schema":actor["schema"],"status":actor["status"],"phase":"fields",
            "generation_sha256":M.GENERATION_SHA,"Nplus1_VCR_used":False,
            "Tminus1_frozen_before_first_T":True,
            "summary":{"Tminus1_Dungeon_Stargate_appearances":0}}
    stacks=[]
    for i in range(22):
        r=rows[i+3]
        members=[
            {"ship_id":r["initiator_ship_id"],"same_owner_as_actor":True,
             "T_at_frozen_target":True},
            {"ship_id":30000+i,"same_owner_as_actor":i>=7,
             "T_at_frozen_target":True},
            {"ship_id":40000+i,"same_owner_as_actor":True,
             "T_at_frozen_target":False},
        ]
        stacks.append({
            "game_id":r["game_id"],"turn":r["turn"],
            "initiator_ship_id":r["initiator_ship_id"],
            "target_ship_id":r["target_ship_id"],
            "Tminus1_cohort":r["Tminus1_cohort"],
            "Tminus1_stack_size":3,"T_members":members,
        })
    passengers={"schema":actor["schema"],"status":actor["status"],
                "phase":"passengers","generation_sha256":M.GENERATION_SHA,
                "Nplus1_VCR_used":False,"Tminus1_frozen_before_first_T":True,
                "summary":{"preselected_source_ship_appearances":66},
                "Tminus1_preselected_source_stack_posthost_comparisons":stacks}
    payload={}
    for name,doc in (("actors",actor),("fields",fields),("passengers",passengers)):
        payload[name]=json.dumps(doc,sort_keys=True).encode()
    manifest={"schema":actor["schema"],
              "status":"V25_NEW_GAME_CORPUS_THREE_REPORTS_COMPLETE",
              "generation_sha256":M.GENERATION_SHA,
              "all_three_complete":True,"CURRENT_modified":False,
              "selected_game_ids":selected,
              "reports":{k:{"sha256":hashlib.sha256(v).hexdigest()}
                         for k,v in payload.items()}}
    originals,windows,source_stacks=M.source_gate(
        manifest,actor,passengers,fields,payload)
    assert len(originals)==106 and len(windows)==33 and len(source_stacks)==22
    actor["summary"]["posthost_compared_windows"]=32
    with pytest.raises(ValueError,match="cohort drift"):
        M.source_gate(manifest,actor,passengers,fields,payload)


def test_independent_Tminus1_pre_reconstruction_no_raw_friendly_codes(monkeypatch):
    row={
        "game_id":403181,"turn":60,"initiator_ship_id":143,"target_ship_id":202,
        "owner_id":1,"source":[1509,2683],"target":[2326,2181],
        "cohort":"ALL_TMINUS1_GATES_PASS",
        "single_failing_gate":None,"Tminus1_cohort":"LONG_CONVENTIONAL_PASS",
        "T_status":"ELSEWHERE","T_position":[2198,1799],
    }
    ships={
        143:(1,{"x":1509,"y":2683,"warp":0,"hullid":56,"neutronium":51,
                "mission":0,"targetx":1509,"targety":2683,"friendlycode":"202"}),
        202:(1,{"x":2326,"y":2181,"warp":0,"hullid":56,"neutronium":257}),
        50:(1,{"x":2198,"y":1799,"warp":0,"hullid":66,"neutronium":20}),
    }
    def pre(_conn,*,game,before):
        assert (game,before)==(403181,59)
        return (),()
    monkeypatch.setattr(M.v9,"pre_snapshots",pre)
    monkeypatch.setattr(M,"group_perspective_records",lambda *_:{})
    monkeypatch.setattr(M,"_owner_rows_for_turn",lambda *_:ships)
    monkeypatch.setattr(M.v16,"potential_stock_edges",lambda *_:(
        ({"initiator_ship_id":143,"target_ship_id":202,"owner_id":1,
          "source":[1509,2683],"target":[2326,2181],
          "cohort":"ALL_TMINUS1_GATES_PASS","single_failing_gate":None,
          "target_Tminus1_warp":0},),{}))
    frozen=M.select_roster(None,403181,60,{(403181,60,143,202):row})
    assert frozen["Tminus1_actor_orders"][0]["Tminus1_waypoint"]==[1509,2683]
    assert 50 in [x["ship_id"] for e in frozen["Tminus1_roster_by_position"]
                  for x in e["ships"]]
    assert "friendlycode" not in str(frozen).lower()
    after={
        143:(1,{"x":2198,"y":1799,"hullid":56,"neutronium":101}),
        202:(1,{"x":2326,"y":2181,"hullid":56,"neutronium":257}),
        50:(1,{"x":2198,"y":1799,"hullid":66,"neutronium":20}),
    }
    compared=M.replay_post(frozen,{(403181,60,143,202):row},after)
    assert len(compared)==1
    assert compared[0]["Tminus1_simple_waypoint_warp_reaches_target"] is False
    assert compared[0]["T_target_remained_at_Tminus1_destination"] is True
    assert compared[0]["actual_Host_Chunnel_activation_proven"] is False


def test_replay_rejects_T_outcome_identity_drift():
    original={
        (403181,60,143,202):{
            "T_status":"ELSEWHERE","T_position":[2198,1799],
        }
    }
    pre={"game_id":403181,"turn":60,"Tminus1_actor_orders":[{
        "game_id":403181,"turn":60,"ship_id":143,"target_ship_id":202,
        "owner_id":1,"Tminus1_source":[1509,2683],
        "Tminus1_target":[2326,2181],"Tminus1_waypoint":[1509,2683],
        "Tminus1_warp":0,
    }],"Tminus1_tow_requested_on_watched_ship":{}}
    wrong={143:(1,{"x":2199,"y":1799,"hullid":56}),
           202:(1,{"x":2326,"y":2181,"hullid":56})}
    with pytest.raises(ValueError,match="coordinate drift"):
        M.replay_post(pre,original,wrong)


def test_missing_owner_current_visibility_is_archival_abstention(monkeypatch):
    windows=((521268,116),)
    original={}
    for s,d,owner in ((388,192,7),(577,240,4)):
        original[(521268,116,s,d)]={
            "game_id":521268,"turn":116,"initiator_ship_id":s,
            "target_ship_id":d,"owner_id":owner,
            "T_status":"ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"
        }
    frozen={
        (521268,116):{"Tminus1_actor_orders":[
            {"ship_id":s,"target_ship_id":d,"owner_id":own}
            for s,d,own in ((388,192,7),(577,240,4))]
        }
    }
    post={(521268,116):{}}
    def refs(_conn,*,game,turns,include_embedded_turn):
        assert game==521268 and include_embedded_turn is False
        return [SimpleNamespace(perspective_player_id=i)
                for i in ([4,7,10] if turns=={115} else [10,11])]
    monkeypatch.setattr(M.v9,"member_refs_for_turns",refs)
    obj=M.archive_visibility(windows,frozen,post,None,original)
    assert obj["summary"]["owner_current_T_unavailable"]==2
    assert obj["summary"]["T_owner_perspective_missing_count"]==2
    assert all(not x["missing_T_not_assumed_destroyed_or_moved"] is False
               for x in obj["owner_current_missing_visibility_cases"])


def test_ownership_episodes_not_independent_host_activations():
    original={}
    records=[]
    for i in range(22):
        key=(401000+i,30,400+i,500+i)
        original[key]={"Tminus1_cohort":"LONG_CONVENTIONAL_PASS"}
        members=[
            {"ship_id":400+i,"same_owner_as_actor":True,
             "T_at_frozen_target":True},
            {"ship_id":800+i,"same_owner_as_actor":False,
             "T_at_frozen_target":i<7},
            {"ship_id":1200+i,"same_owner_as_actor":True,
             "T_at_frozen_target":False}
        ]
        records.append({
            "game_id":key[0],"turn":key[1],
            "initiator_ship_id":key[2],"target_ship_id":key[3],
            "Tminus1_cohort":"LONG_CONVENTIONAL_PASS",
            "Tminus1_stack_size":3,"T_members":members,
        })
    out=M.passenger_episodes(records,original)
    assert out["summary"]["V25_frozen_passenger_episodes"]==22
    assert out["summary"]["V25_source_ship_appearances"]==66
    assert out["summary"]["V25_foreign_owner_at_target_ship_appearances"]==7
    assert out["summary"]["V25_foreign_owner_at_target_distinct_episodes"]==7
    assert out["Host_execution_or_mechanism_causality_proven"] is False


def test_manifests_and_single_evidence_runner(tmp_path):
    docs=[{**M.root(name),"summary":{}} for name in M.PHASES]
    M.publish(tmp_path,docs)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_three_complete"] is True
    assert manifest["posthoc_not_independent_validation"] is True
    for name in M.PHASES:
        assert manifest["reports"][name]["sha256"]==hashlib.sha256(
            (tmp_path/(name+".json")).read_bytes()).hexdigest()
    runner=ROOT/"tools/run-combat-c5-new-corpus-exception-batch-v26.sh"
    wrapper=ROOT/"tools/run-combat-c5-new-corpus-exception-batch-v26-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    sh=runner.read_text()
    for s in (M.GENERATION,M.GENERATION_SHA,
              M.ACTORS_BLOB,M.FIELDS_BLOB,M.PASSENGERS_BLOB,M.MANIFEST_BLOB):
        assert s in sh
    assert "/CURRENT" not in sh
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-new-corpus-exception-batch-v26/published" in wrapper.read_text()
