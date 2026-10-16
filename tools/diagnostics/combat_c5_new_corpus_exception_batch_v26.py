"""V26 NEW public8 corpus: 3 posthoc mechanism/visibility/ownership audits.

V25 outcome comparisons are already open: this is a fixed retrospective
exception follow-up, NOT a second independent validation.

Phases: exception_routes, archive_visibility, passenger_episodes.
Across all 33 frozen V25 active windows: verify all T-1 actor identities
and source locations (and target identities); freeze exact T-1 orders,
all stock Firecloud conventional chains, target and source co-location.
Only after all T-1 freezes inspect T owner-current and the T
perspective-member metadata. Strictly no N+1 VCR and no Host activation
assertion. Three JSON reports + SHA256 manifest in one evidence run.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

import duckdb
from planets_lab.corpus.corpus_db_runtime import member_refs_for_turns
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_chunnel_stabilization_provenance_v20 as v20

SCHEMA="planets-lab.combat-c5-new-corpus-exception-batch.v26"
STATUS="V25_GAME_DISJOINT_POSTHOC_ACTOR_RESIDUAL_AND_VISIBILITY_AUDIT_NOT_CAUSAL"
GENERATION="corpus-v2compact-c5-v25-public8-20261016.duckdb"
GENERATION_SHA="af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a"
ACTORS_BLOB="423e6123496068b8d2987bd27fe0b455fee4c1df"
PASSENGERS_BLOB="ebe8e812d91a80e4fd3c9ccdbc99df0edcc98145"
FIELDS_BLOB="b559901540ee1a906811ed4e510629be70aae365"
MANIFEST_BLOB="2c89d5320b31b2f12d9235192a8ac31240549052"
PHASES=("exception_routes","archive_visibility","passenger_episodes")
FIXED_ELSEWHERE=(403181,60,143,202)
FIXED_UNAVAILABLE=((521268,116,388,192),(521268,116,577,240))


def scalar(x:Any)->int|None:
    return x if type(x) is int else None


def pos(x:Any)->tuple[int,int]|None:
    return v20.position(x)


def git_file(path:Path,sha:str):
    data=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if actual!=sha:raise ValueError("pinned V25 published Git blob drift: "+str(path))
    obj=json.loads(data)
    if not isinstance(obj,dict):raise ValueError("published report is not a mapping")
    return obj,data


def source_gate(manifest,actor_doc,passenger_doc,field_doc,raw):
    if (manifest.get("schema")!="planets-lab.combat-c5-new-game-corpus-batch.v25"
        or manifest.get("status")!="V25_NEW_GAME_CORPUS_THREE_REPORTS_COMPLETE"
        or manifest.get("generation_sha256")!=GENERATION_SHA
        or manifest.get("all_three_complete") is not True
        or manifest.get("CURRENT_modified") is not False):
        raise ValueError("V25 corpus completeness/immutable generation proof drift")
    for name,doc,digest in (
        ("actors",actor_doc,ACTORS_BLOB),
        ("fields",field_doc,FIELDS_BLOB),
        ("passengers",passenger_doc,PASSENGERS_BLOB)):
        if (doc.get("schema")!="planets-lab.combat-c5-new-game-corpus-batch.v25"
            or doc.get("status")!=
                "NEWLY_ACQUIRED_GAME_DISJOINT_RETROSPECTIVE_TMINUS1_RULEAWARE_OBSERVATIONAL"
            or doc.get("phase")!=name
            or doc.get("generation_sha256")!=GENERATION_SHA
            or doc.get("Nplus1_VCR_used") is not False
            or doc.get("Tminus1_frozen_before_first_T") is not True):
            raise ValueError("V25 report provenance/freeze drift: "+name)
        summary=manifest.get("reports",{}).get(name)
        if not isinstance(summary,Mapping) or summary.get("sha256")!=hashlib.sha256(raw[name]).hexdigest():
            raise ValueError("V25 manifest SHA256 membership drift: "+name)
    a=actor_doc.get("preselected_actor_Tminus1_T_observations")
    p=passenger_doc.get("Tminus1_preselected_source_stack_posthost_comparisons")
    if not isinstance(a,list) or len(a)!=106 or not isinstance(p,list) or len(p)!=22:
        raise ValueError("V25 actor/passenger denominators drift")
    summary=actor_doc.get("summary",{})
    if any(summary.get(k)!=v for k,v in {
        "selected_disjoint_games":8,
        "baseline_games_excluded":100,
        "metadata_selected_adjacent_windows":192,
        "Tminus1_contexts_available":192,
        "posthost_compared_windows":33,
        "Tminus1_stock_chunnel_candidate_edges":106,
        "short_Tminus1_documented_field_witnesses":0,
        "context_errors":0,
    }.items()):raise ValueError("V25 fixed 8/192/33/106 cohort drift")
    cats=summary.get("T_endpoint_by_cohort",{}).get("LONG_CONVENTIONAL_PASS",{})
    if cats!={"AT_DISTINCT_FROZEN_TARGET":55,
              "ELSEWHERE":1,
              "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":2}:
        raise ValueError("V25 55/1/2 long actor outcomes drift")
    if field_doc.get("summary",{}).get("Tminus1_Dungeon_Stargate_appearances")!=0:
        raise ValueError("V25 no Dungeon exposures drift")
    if passenger_doc.get("summary",{}).get("preselected_source_ship_appearances")!=66:
        raise ValueError("V25 source ship population drift")
    selected=manifest.get("selected_game_ids")
    if not isinstance(selected,list) or len(selected)!=8 or len(set(selected))!=8:
        raise ValueError("V25 eight new game IDs drift")
    groups=defaultdict(list)
    keys=set()
    for record in a:
        key=tuple(scalar(record.get(k)) for k in (
            "game_id","turn","initiator_ship_id","target_ship_id"))
        if (any(v is None or v<=0 for v in key) or key in keys or
            key[0] not in selected):
            raise ValueError("V25 duplicate or malformed actor identity")
        keys.add(key)
        groups[key[:2]].append(record)
    if len(groups)!=33:raise ValueError("V25 33 active windows missing")
    expected_specials={
        key for key in keys if key==FIXED_ELSEWHERE or key in FIXED_UNAVAILABLE}
    if len(expected_specials)!=3:raise ValueError("V25 fixed anomaly/abstention identities drift")
    originals={key:row for rows in groups.values() for row in rows for key in [
        (row["game_id"],row["turn"],row["initiator_ship_id"],row["target_ship_id"])]}
    for key in (FIXED_ELSEWHERE,*FIXED_UNAVAILABLE):
        status=originals[key]["T_status"]
        if status!=("ELSEWHERE" if key==FIXED_ELSEWHERE else
                    "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"):
            raise ValueError("V25 specific episode comparison drift")
    return originals,tuple(sorted(groups)),p


def select_roster(conn,g,t,original):
    snapshots,_=v9.pre_snapshots(conn,game=g,before=t-1)
    roster=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),t-1)
    edges,_reasons=v16.potential_stock_edges(roster)
    edge_map={(x["initiator_ship_id"],x["target_ship_id"]):x for x in edges}
    original_cases=[(k,row) for k,row in sorted(original.items()) if k[:2]==(g,t)]
    watched=set()
    ships=[]
    for key,case in original_cases:
        _,_,sid,dst=key
        now=edge_map.get((sid,dst))
        if (now is None or now["owner_id"]!=case["owner_id"] or
            now["cohort"]!=case["cohort"] or
            now["single_failing_gate"]!=case["single_failing_gate"] or
            pos(now["source"])!=pos(case["source"]) or
            pos(now["target"])!=pos(case["target"])):
            raise ValueError("V25 source-edge identity changed under independent T-1 replay")
        watched.update((sid,dst))
        own,raw=roster[sid]
        # Public archival numeric/mission fields only; no friendly codes.
        way=pos((raw.get("targetx"),raw.get("targety")))
        ships.append({
            "game_id":g,"turn":t,"ship_id":sid,
            "target_ship_id":dst,"owner_id":own,
            "Tminus1_source":case["source"],"Tminus1_target":case["target"],
            "Tminus1_waypoint":list(way) if way is not None else None,
            "Tminus1_mission":scalar(raw.get("mission")),
            "Tminus1_warp":scalar(raw.get("warp")),
            "Tminus1_damage":scalar(raw.get("damage")),
            "Tminus1_fuel":scalar(raw.get("neutronium")),
            "Tminus1_target_warp":now["target_Tminus1_warp"],
            "Tminus1_distinct_source_target":pos(case["source"])!=pos(case["target"]),
            "Tminus1_cohort":case["Tminus1_cohort"],
            "Tminus1_original_status_only_for_POST_recheck":True,
        })
    where={}
    for sid,(owner,raw) in sorted(roster.items()):
        here=pos((raw.get("x"),raw.get("y")))
        if here is None:continue
        where.setdefault(here,[]).append({
            "ship_id":sid,"owner_id":owner,
            "hull_id":scalar(raw.get("hullid",raw.get("hull_id"))),
            "Tminus1_warp":scalar(raw.get("warp")),
            "Tminus1_fuel":scalar(raw.get("neutronium")),
        })
    pre_stack={}
    for sid in watched:
        if sid not in roster:raise ValueError("watched T-1 ship unavailable")
        raw=roster[sid][1]
        start=pos((raw.get("x"),raw.get("y")))
        pre_stack[sid]=where.get(start,[])
    tow={}
    for x,y in roster.items():
        rr=y[1]
        if scalar(rr.get("mission"))==v16.TOW_MISSION_ID:
            other=scalar(rr.get("mission1target"))
            if other in watched:
                tow.setdefault(other,[]).append(x)
    return {
        "game_id":g,"turn":t,
        "Tminus1_actor_orders":ships,
        "Tminus1_watch_ships":sorted(watched),
        "Tminus1_roster_by_position":[
            {"position":list(k),"ships":v} for k,v in sorted(where.items())],
        "Tminus1_tow_requested_on_watched_ship":tow,
        "Tminus1_eligible_stock_edges":[
            {"initiator_ship_id":r["initiator_ship_id"],
             "target_ship_id":r["target_ship_id"],
             "owner_id":r["owner_id"],
             "source":r["source"],"target":r["target"],
             "cohort":r["cohort"],"single_failing_gate":r["single_failing_gate"]}
            for r in edges],
        "Tminus1_all_features_frozen_before_any_T":True,
    }


def replay_post(pre,original,current):
    g,t=pre["game_id"],pre["turn"]
    out=[]
    for order in pre["Tminus1_actor_orders"]:
        key=(g,t,order["ship_id"],order["target_ship_id"])
        orig=original[key]
        status,raw=v13._current_ship(current,order["ship_id"],order["owner_id"],56)
        here=pos((raw.get("x"),raw.get("y"))) if raw is not None else None
        expected=pos(orig["T_position"]) if orig["T_position"] is not None else None
        if here!=expected or (raw is None)!=(orig["T_position"] is None):
            raise ValueError("V25 published T owner-current coordinate drift")
        target_id=order["target_ship_id"]
        target_status,target=v13._current_ship(
            current,target_id,order["owner_id"],56)
        target_post=pos((target.get("x"),target.get("y"))) if target else None
        orig_source,orig_dest=pos(order["Tminus1_source"]),pos(order["Tminus1_target"])
        waypoint=pos(order["Tminus1_waypoint"]) if order["Tminus1_waypoint"] else None
        ordinary=(
            waypoint==orig_dest and order["Tminus1_warp"] is not None
            and order["Tminus1_warp"]>0 and
            hypot(orig_dest[0]-orig_source[0],orig_dest[1]-orig_source[1])
                <=order["Tminus1_warp"]**2)
        out.append({
            **order,
            "T_reobserved_actor_status":status,
            "T_reobserved_actor_position":list(here) if here is not None else None,
            "T_target_owner_current_status":target_status,
            "T_target_owner_current_position":list(target_post) if target_post is not None else None,
            "T_target_remained_at_Tminus1_destination":
                target_post==orig_dest if target_post is not None else None,
            "Tminus1_simple_waypoint_warp_reaches_target":ordinary,
            "Tminus1_inbound_tow_requests":pre["Tminus1_tow_requested_on_watched_ship"].get(order["ship_id"],[]),
            "T_observed_actor_at_source":here==orig_source if here is not None else None,
            "T_observed_actor_at_target":here==orig_dest if here is not None else None,
            "original_V25_status":orig["T_status"],
            "actual_Host_Chunnel_activation_proven":False,
        })
    return out


def root(phase):
    return {
        "schema":SCHEMA,"status":STATUS,"phase":phase,
        "source_V25_actors_git_blob_sha1":ACTORS_BLOB,
        "source_V25_passengers_git_blob_sha1":PASSENGERS_BLOB,
        "source_V25_manifest_git_blob_sha1":MANIFEST_BLOB,
        "generation":GENERATION,"generation_sha256":GENERATION_SHA,
        "V25_original_comparison_outcomes_selected_before_V26":True,
        "all_33_source_windows_frozen_before_ANY_T_read":True,
        "Host_execution_or_mechanism_causality_proven":False,
        "new_production_Host_movement_or_combat_predictions":0,
        "Nplus1_VCR_used":False,
    }


def analyze_residuals(observed,original,pre_by_window,post_by_window):
    exceptions=[]
    clusters=defaultdict(Counter)
    for row in observed:
        key=(row["game_id"],row["turn"],row["ship_id"],row["target_ship_id"])
        cohort=row["Tminus1_cohort"]
        if cohort=="LONG_CONVENTIONAL_PASS":
            clusters[row["game_id"],row["turn"]][row["original_V25_status"]]+=1
        if row["original_V25_status"] not in ("ELSEWHERE","ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"):
            continue
        if key not in (FIXED_ELSEWHERE,*FIXED_UNAVAILABLE):continue
        pre=pre_by_window[key[:2]]
        endpoint=pos(row["T_reobserved_actor_position"]) if row["T_reobserved_actor_position"] else None
        T_owner_current=post_by_window[key[:2]]
        at_destination_pre=[]
        near_destination_pre=[]
        T_colocated=[]
        if endpoint is not None:
            for location in pre["Tminus1_roster_by_position"]:
                location_point=pos(location["position"])
                distance=hypot(location_point[0]-endpoint[0],location_point[1]-endpoint[1])
                if distance==0:at_destination_pre.extend(location["ships"])
                elif distance<=100:near_destination_pre.append({
                    "Tminus1_position":location["position"],
                    "distance_ly":round(distance,5),
                    "ship_count":len(location["ships"]),
                })
            for ship_id,(owner,raw) in sorted(T_owner_current.items()):
                loc=pos((raw.get("x"),raw.get("y")))
                if loc==endpoint:
                    T_colocated.append({"ship_id":ship_id,"owner_id":owner})
        T1_candidates=[
            x for x in pre["Tminus1_eligible_stock_edges"]
            if (pos(x["target"])==endpoint and endpoint is not None)
        ]
        exceptions.append({
            **row,
            "Tminus1_ships_at_observed_actor_T_location":at_destination_pre,
            "Tminus1_nearby_ship_sites_100LY":near_destination_pre,
            "Tminus1_stock_chunnel_target_at_observed_position":T1_candidates,
            "T_colocated_owner_current_ship_ids":T_colocated,
            "T_position_is_postHost_not_intermediate_phase":True,
        })
    actual_keys={
        (e["game_id"],e["turn"],e["ship_id"],e["target_ship_id"])
        for e in exceptions
    }
    if actual_keys!={FIXED_ELSEWHERE,*FIXED_UNAVAILABLE}:
        raise ValueError("missing one of the three V25 residual/visibility cases")
    exception=next(e for e in exceptions if (
        e["game_id"],e["turn"],e["ship_id"],e["target_ship_id"])==FIXED_ELSEWHERE)
    return {
        **root("exception_routes"),
        "summary":{
            "V25_eligible_long_actor_edges":58,
            "V25_T_distinct_target_matches":55,
            "V25_T_other_destination":1,
            "V25_T_owner_current_unavailable":2,
            "V25_eligible_long_episode_windows":len(clusters),
            "V25_eligible_long_distinct_games":len({g for g,t in clusters}),
            "G403181_T60_143_to_202_drift_explored":True,
            "G403181_T60_143_actor_observed_location":exception["T_reobserved_actor_position"],
            "G521268_T116_missing_actor_episodes":2,
            "original_V25_actor_outcomes_not_new_validation":True,
        },
        "three_frozen_positive_gate_residuals":exceptions,
        "all_long_episode_window_clusters":{
            f"{g}/{t}":dict(sorted(counts.items()))
            for (g,t),counts in sorted(clusters.items())},
    }


def archive_visibility(windows,pre_by_window,post_by_window,conn,original):
    # All the T archive metadata for all 33 windows is opened ONLY after PRE freeze.
    result=[]
    for g,t in windows:
        refs=v9.member_refs_for_turns(
            conn,game_id=g,turns={t},include_embedded_turn=False)
        perspectives=sorted({r.perspective_player_id for r in refs})
        pset=sorted({r.perspective_player_id for r in v9.member_refs_for_turns(
            conn,game_id=g,turns={t-1},include_embedded_turn=False)})
        if len(refs)==0:raise ValueError("empty T archive-member set")
        for (gg,tt,actor,target),case in sorted(original.items()):
            if (g,t)!=(gg,tt) or case["T_status"]!="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":
                continue
            initial=next(x for x in pre_by_window[g,t]["Tminus1_actor_orders"]
                         if x["ship_id"]==actor and x["target_ship_id"]==target)
            observed,status=v13._current_ship(
                post_by_window[g,t],actor,case["owner_id"],56)
            # Return ordering is (status,raw): don't misread unavailable as death.
            this_status,this_rec=observed,status
            if this_rec is not None or this_status!="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":
                raise ValueError("original T unavailable no longer reproduced")
            result.append({
                "game_id":g,"turn":t,
                "actor_ship_id":actor,"target_ship_id":target,
                "owner_id":case["owner_id"],
                "Tminus1_owner_current_available":True,
                "Tminus1_archive_perspective_slots":pset,
                "T_archive_perspective_slots":perspectives,
                "Tminus1_owner_perspective_in_archive":case["owner_id"] in pset,
                "T_owner_perspective_in_archive":case["owner_id"] in perspectives,
                "T_owner_current_status":this_status,
                "missing_T_not_assumed_destroyed_or_moved":True,
            })
    if len(result)!=2 or {r["actor_ship_id"] for r in result}!={388,577}:
        raise ValueError("V25 two owner-current visibility abstentions changed")
    return {
        **root("archive_visibility"),
        "summary":{
            "all_33_original_active_windows_audited_for_perspective_metadata":len(windows),
            "owner_current_T_unavailable":len(result),
            "unavailable_distinct_games":len({x["game_id"] for x in result}),
            "T_owner_perspective_present_count":sum(x["T_owner_perspective_in_archive"] for x in result),
            "T_owner_perspective_missing_count":sum(not x["T_owner_perspective_in_archive"] for x in result),
            "unavailable_not_counted_as_failed_chunnel":True,
        },
        "owner_current_missing_visibility_cases":result,
    }


def passenger_episodes(original_passengers,orig_actors):
    by_cohort=defaultdict(Counter)
    by_game=defaultdict(Counter)
    episodes=[]
    for ep in original_passengers:
        key=(ep["game_id"],ep["turn"],ep["initiator_ship_id"],ep["target_ship_id"])
        if key not in orig_actors:raise ValueError("V25 passenger episode not backed by frozen actor")
        if ep["Tminus1_cohort"]!=orig_actors[key]["Tminus1_cohort"]:
            raise ValueError("V25 passenger original cohort mismatch")
        stack=ep["T_members"]
        if len(stack)!=ep["Tminus1_stack_size"] or len({x["ship_id"] for x in stack})!=len(stack):
            raise ValueError("V25 source stack identity drift")
        own=[x for x in stack if x["same_owner_as_actor"]]
        other=[x for x in stack if not x["same_owner_as_actor"]]
        if not any(x["ship_id"]==ep["initiator_ship_id"] for x in own):
            raise ValueError("V25 stack absent actor")
        for label,members in (("SAME_OWNER",own),("DIFFERENT_OWNER",other)):
            by_cohort[label]["ship_appearances"]+=len(members)
            by_cohort[label]["at_target"]+=sum(x["T_at_frozen_target"] is True for x in members)
            by_cohort[label]["elsewhere"]+=sum(x["T_at_frozen_target"] is False for x in members)
            by_cohort[label]["abstain"]+=sum(x["T_at_frozen_target"] is None for x in members)
        by_game[ep["game_id"]]["episodes"]+=1
        episodes.append({
            "game_id":ep["game_id"],"turn":ep["turn"],
            "actor_ship_id":ep["initiator_ship_id"],
            "target_ship_id":ep["target_ship_id"],
            "frozen_cohort":ep["Tminus1_cohort"],
            "source_ship_appearances":len(stack),
            "same_owner_ship_appearances":len(own),
            "other_owner_ship_appearances":len(other),
            "same_owner_at_target":sum(x["T_at_frozen_target"] is True for x in own),
            "other_owner_at_target":sum(x["T_at_frozen_target"] is True for x in other),
            "at_target_is_observational_not_causation":True,
        })
    if len(episodes)!=22 or sum(x["source_ship_appearances"] for x in episodes)!=66:
        raise ValueError("V25 fixed 22 episode 66 ship denominator drift")
    other_at=sum(x["other_owner_at_target"] for x in episodes)
    if other_at!=7:raise ValueError("V25 other-owner seven observed at targets drift")
    return {
        **root("passenger_episodes"),
        "summary":{
            "V25_frozen_passenger_episodes":22,
            "V25_distinct_game_turn_windows":len({(e["game_id"],e["turn"]) for e in episodes}),
            "V25_distinct_games":len(by_game),
            "V25_source_ship_appearances":66,
            "V25_ownership_T_counts":{x:dict(sorted(v.items())) for x,v in sorted(by_cohort.items())},
            "V25_foreign_owner_at_target_ship_appearances":other_at,
            "V25_foreign_owner_at_target_distinct_episodes":sum(
                x["other_owner_at_target"]>0 for x in episodes),
            "passenger_transport_or_eligibility_proven":False,
        },
        "Tminus1_preselected_episode_ownership_outcomes":episodes,
        "game_clusters":{str(k):dict(sorted(v.items())) for k,v in sorted(by_game.items())},
    }


def publish(folder,reports):
    folder.mkdir(parents=True,exist_ok=True)
    index={}
    for phase,report in zip(PHASES,reports,strict=True):
        out=folder/(phase+".json")
        temp=out.with_suffix(".json.tmp")
        temp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(out)
        index[phase]={
            "filename":out.name,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
            "summary":report["summary"],
        }
        print("===== C5 V26",phase,"=====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        print("output:",out)
    manifest={
        "schema":SCHEMA,"status":"V26_POSTHOC_EXCEPTION_VISIBILITY_OWNERSHIP_COMPLETE",
        "all_three_complete":len(index)==3,
        "generation_sha256":GENERATION_SHA,
        "source_V25_manifest_git_blob_sha1":MANIFEST_BLOB,
        "reports":index,
        "posthoc_not_independent_validation":True,
        "Host_mechanism_proven":False,
    }
    out=folder/"manifest.json"
    temp=out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    temp.replace(out)
    print("===== C5 V26 COMPLETE THREE-REPORT MANIFEST =====")
    print("status:",manifest["status"])
    print("output:",out)


def main():
    p=argparse.ArgumentParser()
    for key in ("database","v25-manifest","v25-actors","v25-fields","v25-passengers","output-dir"):
        p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    try:
        originals={}
        data={}
        for name,path,sha in (
            ("manifest",args.v25_manifest,MANIFEST_BLOB),
            ("actors",args.v25_actors,ACTORS_BLOB),
            ("fields",args.v25_fields,FIELDS_BLOB),
            ("passengers",args.v25_passengers,PASSENGERS_BLOB)):
            originals[name],data[name]=git_file(path,sha)
        cases,windows,passengers=source_gate(
            originals["manifest"],originals["actors"],originals["passengers"],
            originals["fields"],data)
        db=args.database.resolve()
        if not db.is_file() or db.name!=GENERATION:
            raise ValueError("pinned explicit V25 new-game database absent")
        print("[c5-v26] verify immutable V25 corpus SHA256 once",flush=True)
        before=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=GENERATION_SHA:raise ValueError("new public8 corpus SHA256 changed")
        print(f"[c5-v26] SHA verified in {time.monotonic()-before:.1f}s",flush=True)
        conn=duckdb.connect(str(db),read_only=True)
        try:
            frozen={}
            for i,(g,t) in enumerate(windows,1):
                print(f"[c5-v26] PRE [{i}/{len(windows)}] G{g} T{t}",flush=True)
                frozen[g,t]=select_roster(conn,g,t,cases)
            # ABSOLUTE 33-window PRE barrier before any T observation, including archive refs.
            observed={}
            compared=[]
            for i,(g,t) in enumerate(windows,1):
                print(f"[c5-v26] POST [{i}/{len(windows)}] G{g} T{t}",flush=True)
                observed[g,t]=v9.after_owner_current(conn,game=g,turn=t)
                compared.extend(replay_post(frozen[g,t],cases,observed[g,t]))
            r1=analyze_residuals(compared,cases,frozen,observed)
            r2=archive_visibility(windows,frozen,observed,conn,cases)
        finally:conn.close()
        r3=passenger_episodes(passengers,cases)
        publish(args.output_dir,(r1,r2,r3))
    except (OSError,ValueError,TypeError,KeyError,duckdb.Error,json.JSONDecodeError) as err:
        print("ERROR V26:",err,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
