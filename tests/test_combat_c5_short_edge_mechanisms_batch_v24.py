from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_short_edge_mechanisms_batch_v24.py"
SPEC=importlib.util.spec_from_file_location("short_edge_v24",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def candidate(g,t,a,b,src,dst,*,group="SHORT",observed=None,field=False,owner=4):
    return {
        "game_id":g,"turn":t,"initiator_ship_id":a,"target_ship_id":b,
        "owner_id":owner,
        "Tminus1_cohort":group,
        "Tminus1_source":list(src),"Tminus1_target":list(dst),
        "Tminus1_distance_ly":round(((dst[0]-src[0])**2+(dst[1]-src[1])**2)**.5,5),
        "T_actor_position":list(observed) if observed is not None else None,
        "T_observation_status":"ELSEWHERE" if observed is not None else
            "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE",
        "Host_Chunnel_activation_proven":False,
        "Tminus1_short_field_status":"TMINUS1_DOCUMENTED_FIELD_WITNESS" if field else
            "ABSTAIN_NO_DOCUMENTED_FIELD_WITNESS",
    }


def study():
    return [
        candidate(449095,121,361,114,(2324,1829),(2323,1829),
                  observed=(1300,2140),field=True),
        candidate(449095,121,396,218,(1060,2295),(1060,2296),
                  observed=(1276,2810)),
        candidate(449095,141,547,229,(1885,2115),(1884,2115),
                  observed=(1884,2115),field=True),
        candidate(264889,74,329,375,(2750,2060),(2723,2001),observed=(2750,2060)),
        candidate(264889,124,340,358,(2958,1914),(2909,1956),observed=(2958,1914)),
        candidate(264889,160,91,243,(1558,1525),(1523,1603),observed=(1558,1525)),
        candidate(342288,187,504,160,(1679,1454),(1609,1443),observed=(1679,1454)),
        candidate(530633,121,344,201,(1029,2210),(1125,2217),observed=(1029,2210)),
    ]


def long(g,t,a,b,src,dst,*,owner=4,observed=None):
    return candidate(g,t,a,b,src,dst,group="LONG",owner=owner,observed=observed or dst)


def test_graph_matches_1ly_chains_even_without_stabilizer_evidence():
    sh={(e["game_id"],e["turn"],e["initiator_ship_id"],e["target_ship_id"]):e
        for e in study()}
    longedges=[
        long(449095,121,114,443,(2323,1829),(1300,2140)),
        long(449095,121,218,548,(1060,2296),(1276,2810)),
        long(449095,141,180,338,(1937,2974),(1214,2268)),
    ]
    ll={(e["game_id"],e["turn"],e["initiator_ship_id"],e["target_ship_id"]):e
        for e in longedges}
    chains=M.frozen_chains(sh,ll)
    assert len(chains)==2
    assert sorted((e["short_actor_id"],e["middle_firecloud_id"],e["downstream_target_id"])
                  for e in chains)==[(361,114,443),(396,218,548)]
    assert any(e["Tminus1_field_witness"]=="ABSTAIN_NO_DOCUMENTED_FIELD_WITNESS"
               for e in chains)
    assert all(e["Tminus1_chain_graph_only"] is True for e in chains)
    ll[(449095,121,114,443)]["owner_id"]=9
    assert len(M.frozen_chains(sh,ll))==1
    ll[(449095,121,114,443)]["owner_id"]=4
    ll[(449095,121,114,443)]["Tminus1_source"]=[2323,1830]
    assert len(M.frozen_chains(sh,ll))==1


def test_source_pin_8_short_375_long_and_manifest_sha(tmp_path):
    rows=study()
    for i in range(375):
        rows.append(long(300000+i,33,1000+i,2000+i,(100,100),(300,400)))
    windows=sorted({(x["game_id"],x["turn"]) for x in rows if x["Tminus1_cohort"]=="SHORT"})
    assert len(windows)==7
    field={
        "schema":"planets-lab.combat-c5-episode-field-discovery-batch.v23",
        "status":"V22_EPISODE_RECONCILIATION_AND_NEW_TMINUS1_FIELD_SCAN_OBSERVATIONAL",
        "phase":"field_scan",
        "source_db_sha256":M.SHA256,
        "Nplus1_VCR_used":False,
        "summary":{
            "selected_previous_games_excluded":89,
            "metadata_selected_unused_games":11,
            "metadata_selected_adjacent_windows":264,
            "Tminus1_distinct_short_candidate_edges":8,
            "Tminus1_long_controls":375,
            "short_with_Tminus1_documented_field_witness":2,
            "short_witness_distinct_games":1,
            "short_witness_distinct_windows":2,
            "all_unused_game_Tminus1_freezes_before_first_T":True,
            "Host_field_activation_or_Chunnel_proven":False,
            "no_new_public_corpus":True,
        },
        "posthost_short_and_long_comparisons":rows,
    }
    raw=json.dumps(field).encode()
    manifest={
        "status":"V23_EPISODES_OWNERSHIP_FIELD_SCAN_COMPLETE",
        "all_three_complete":True,
        "phase_reports":{"field_scan":{"sha256":__import__("hashlib").sha256(raw).hexdigest()}}
    }
    shorts,longs,win=M.freeze_source(field,manifest,raw)
    assert len(shorts)==8 and len(longs)==375 and len(win)==7
    field["posthost_short_and_long_comparisons"][0]["Host_Chunnel_activation_proven"]=True
    with pytest.raises(ValueError,match="identity drift"):
        M.freeze_source(field,manifest,raw)
    field["posthost_short_and_long_comparisons"][0]["Host_Chunnel_activation_proven"]=False
    manifest["phase_reports"]["field_scan"]["sha256"]="bad"
    with pytest.raises(ValueError,match="manifest mismatch"):
        M.freeze_source(field,manifest,raw)


def test_Tminus1_orders_and_direct_normal_motion_not_claimed_for_warp0():
    fields=[
        {"ship_id":361,"owner_id":4,"Tminus1_ship_status":"OWNER_CURRENT",
         "Tminus1_position":[2324,1829],"Tminus1_fuel":80,
         "Tminus1_hull_id":56,"Tminus1_warp":0},
        {"ship_id":114,"owner_id":4,"Tminus1_ship_status":"OWNER_CURRENT",
         "Tminus1_position":[2323,1829],"Tminus1_fuel":80,
         "Tminus1_hull_id":56,"Tminus1_warp":0},
        {"ship_id":443,"owner_id":4,"Tminus1_ship_status":"OWNER_CURRENT",
         "Tminus1_position":[1300,2140],"Tminus1_fuel":80,
         "Tminus1_hull_id":56,"Tminus1_warp":0},
    ]
    source=study()[0]
    c={
        "game_id":449095,"turn":121,
        "initiator_ship_id":361,"target_ship_id":114,"owner_id":4,
        "Tminus1_source":source["Tminus1_source"],
        "Tminus1_target":source["Tminus1_target"],
        "Tminus1_initiator_warp":0,"Tminus1_waypoint":[2323,1829],
        "Tminus1_frozen_downstream_chains":[{
            "game_id":449095,"turn":121,
            "short_actor_id":361,"middle_firecloud_id":114,
            "downstream_target_id":443,"owner_id":4,
            "Tminus1_downstream_target":[1300,2140],
            "Tminus1_chain_graph_only":True,
        }],
    }
    frozen={
        "game_id":449095,"turn":121,
        "Tminus1_selected_ship_roster":fields,
        "Tminus1_targeted_cases":[c],
        "Tminus1_dungeon_inventory":[],
    }
    after={
        361:(4,{"x":1300,"y":2140,"hullid":56,"neutronium":30}),
        114:(4,{"x":1300,"y":2140,"hullid":56,"neutronium":30}),
        443:(4,{"x":1300,"y":2140,"hullid":56,"neutronium":80}),
    }
    cases,gates=M.compare_window(frozen,after,
        {(449095,121,361,114):source},{})
    assert gates==[]
    x=cases[0]
    assert x["T_actor_matches_downstream_eligible_long_target"] is True
    assert x["T_actor_matches_original_short_target"] is False
    assert x["T_actor_direct_waypoint_warp_geometric_candidate"] is False
    assert x["frozen_downstream_chain_T_comparisons"][0][
        "T_middle_actor_at_downstream_destination"] is True
    after[361]=(9,after[361][1])
    with pytest.raises(ValueError,match="V23 short actor owner-current T drift"):
        M.compare_window(frozen,after,{(449095,121,361,114):source},{})


def test_phase_barrier_all_short_windows_pre_before_post(monkeypatch):
    short={(r["game_id"],r["turn"],r["initiator_ship_id"],r["target_ship_id"]):r
           for r in study()}
    windows=tuple(sorted({k[:2] for k in short}))
    events=[]
    def pre(_conn,g,t,short,long,chains):
        events.append("pre")
        return {"game_id":g,"turn":t,
                "Tminus1_targeted_cases":[],
                "Tminus1_selected_ship_roster":[],
                "Tminus1_dungeon_inventory":[],
                "Tminus1_field_geometry":[],
                "Tminus1_all_features_frozen_before_T":True}
    def post(_conn,*,game,turn):
        assert events.count("pre")==len(windows)
        events.append("post")
        return {}
    monkeypatch.setattr(M,"freeze_source",lambda *_:(short,{},windows))
    monkeypatch.setattr(M,"freeze_window",pre)
    monkeypatch.setattr(M.v9,"after_owner_current",post)
    report=M.build_report(None,{}, {},b"")
    assert len(report)==3
    assert all(o["summary"]["targeted_Tminus1_windows"]==7 for o in report)
    assert events==["pre"]*7+["post"]*7


def test_summarize_exposes_no_host_claims_and_both_chains():
    reports=M.summarize({}, {},(),{},())
    assert len(reports)==3
    assert all(r["Nplus1_VCR_used"] is False for r in reports)
    assert all(r["actual_chunnel_activation_or_movement_phase_proven"] is False for r in reports)


def test_one_server_command_three_reports_pins_and_bash_syntax():
    runner=ROOT/"tools/run-combat-c5-short-edge-mechanisms-batch-v24.sh"
    wrapper=ROOT/"tools/run-combat-c5-short-edge-mechanisms-batch-v24-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    for b in (M.V23_FIELD_BLOB,M.V23_MANIFEST_BLOB,M.GENERATION):
        assert b in runner.read_text()
    assert "/CURRENT" not in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/combat/c5-short-edge-mechanisms-batch-v24/published" in wrapper.read_text()


def test_reports_manifest_atomic_output(tmp_path):
    reports=M.summarize({}, {},(),{},())
    M.publish(tmp_path,reports)
    j=json.loads((tmp_path/"manifest.json").read_text())
    assert j["all_three_complete"] is True
    assert sorted(j["reports"])==sorted(M.OUTPUTS)
    assert all(len(v["sha256"])==64 for v in j["reports"].values())
