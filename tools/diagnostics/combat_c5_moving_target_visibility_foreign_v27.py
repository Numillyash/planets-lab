"""V27: one-batch posthoc moving-target, missing-identity and foreign-route audit.

Fixed cohort is the newly acquired V25 public8 (33 active windows, 106
stock actor candidates). This is NOT additional independent validation.
Freeze all T-1 rosters and eight cross-owner candidate ship orders before
reading ANY T or T+1 observation. Optional T+1 OWNER-CURRENT is strictly
posthoc identity provenance, never an N+1 VCR or forecast input.

Reports: moving_targets.json, identity_provenance.json,
foreign_routes.json, manifest.json. All research-only.
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
for directory in (ROOT/"src",Path(__file__).resolve().parent):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))
import duckdb
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_new_corpus_exception_batch_v26 as v26
import combat_c5_site_disjoint_movement_validation_v9 as v9
import combat_c5_firecloud_disjoint_validation_v13 as v13

SCHEMA="planets-lab.combat-c5-moving-target-and-identity-audit.v27"
STATUS="RETROSPECTIVE_V25_MOVING_TARGET_MISSING_SHIPS_FOREIGN_ROUTES_NOT_HOST_PROOF"
REPORTS=("moving_targets","identity_provenance","foreign_routes")
V26_BLOBS={
    "manifest":"1b44aa0d1f885a3adbf58bdf7fffd065d18e42f8",
    "exception_routes":"65816f42bd5030da8cd58ca8fb76cf0eea3f864a",
    "archive_visibility":"327af41f73a4415650cc2c07ac08a30a5c7d6105",
    "passenger_episodes":"8c55051e98ab0b4a6484054d494316ad81db95e9",
}
V25_BLOBS={
    "manifest":v26.MANIFEST_BLOB,"actors":v26.ACTORS_BLOB,
    "fields":v26.FIELDS_BLOB,"passengers":v26.PASSENGERS_BLOB,
}
NEW_DB_NAME=v26.GENERATION
NEW_DB_SHA256=v26.GENERATION_SHA
MISSING=((521268,116,388,192,7),(521268,116,577,240,4))
MOVED=(403181,60,143,202)


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def xy(x:Any)->tuple[int,int]|None:
    return v26.pos(x)


def pinned(path:Path,digest:str):
    payload=path.read_bytes()
    calculated=hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\x00"+payload).hexdigest()
    if calculated!=digest:raise ValueError("frozen report Git blob mismatch: "+str(path))
    doc=json.loads(payload)
    if not isinstance(doc,dict):raise ValueError("published source not JSON object")
    return doc,payload


def source_gate(v25,v26reports,raw):
    originals,windows,stacks=v26.source_gate(
        v25["manifest"],v25["actors"],v25["passengers"],v25["fields"],
        {name:raw["v25_"+name] for name in V25_BLOBS})
    manifest=v26reports["manifest"]
    if (manifest.get("schema")!=v26.SCHEMA or
        manifest.get("status")!="V26_POSTHOC_EXCEPTION_VISIBILITY_OWNERSHIP_COMPLETE"
        or manifest.get("all_three_complete") is not True
        or manifest.get("posthoc_not_independent_validation") is not True
        or manifest.get("generation_sha256")!=NEW_DB_SHA256):
        raise ValueError("V26 manifest/causal boundary drift")
    for name in ("exception_routes","archive_visibility","passenger_episodes"):
        doc=v26reports[name]
        if (doc.get("schema")!=v26.SCHEMA or doc.get("status")!=v26.STATUS
            or doc.get("phase")!=name or
            doc.get("source_V25_manifest_git_blob_sha1")!=v26.MANIFEST_BLOB or
            doc.get("generation_sha256")!=NEW_DB_SHA256 or
            doc.get("Nplus1_VCR_used") is not False or
            doc.get("all_33_source_windows_frozen_before_ANY_T_read") is not True):
            raise ValueError("V26 source report phase or provenance changed: "+name)
        entry=manifest.get("reports",{}).get(name)
        if not isinstance(entry,Mapping) or entry.get("sha256")!=hashlib.sha256(
                raw["v26_"+name]).hexdigest():
            raise ValueError("V26 manifest report SHA256 drift: "+name)
    exc=v26reports["exception_routes"]
    vis=v26reports["archive_visibility"]
    pas=v26reports["passenger_episodes"]
    if (exc.get("summary",{}).get("V25_eligible_long_actor_edges")!=58
        or exc.get("summary",{}).get("V25_T_distinct_target_matches")!=55
        or exc.get("summary",{}).get("V25_T_other_destination")!=1
        or exc.get("summary",{}).get("V25_T_owner_current_unavailable")!=2
        or vis.get("summary",{}).get("T_owner_perspective_present_count")!=2
        or vis.get("summary",{}).get("T_owner_perspective_missing_count")!=0
        or pas.get("summary",{}).get("V25_foreign_owner_at_target_ship_appearances")!=7):
        raise ValueError("V26 frozen 55/1/2, archive, or passenger controls drift")
    exceptions=exc.get("three_frozen_positive_gate_residuals")
    if not isinstance(exceptions,list) or len(exceptions)!=3:
        raise ValueError("V26 missing fixed 3 residual cases")
    s=next((x for x in exceptions if (x["game_id"],x["turn"],x["ship_id"],x["target_ship_id"])==MOVED),None)
    if (s is None or s["T_reobserved_actor_position"]!=[2198,1799]
        or s["T_target_owner_current_position"]!=[2198,1799]
        or s["Tminus1_target"]!=[2326,2181]):
        raise ValueError("V26 moving-target exception provenance drift")
    foreign=[]
    for episode in stacks:
        target=xy(episode["Tminus1_destination"])
        key=(episode["game_id"],episode["turn"],
             episode["initiator_ship_id"],episode["target_ship_id"])
        if key not in originals:
            raise ValueError("foreign-source actor absent from published V25")
        source=xy(originals[key]["source"])
        others=[ship for ship in episode["T_members"]
                if not ship["same_owner_as_actor"]]
        if others:
            foreign.append({
                "game_id":key[0],"turn":key[1],"actor_id":key[2],
                "target_id":key[3],"actor_owner":originals[key]["owner_id"],
                "source":list(source),"target":list(target),
                "published_ships":others,
            })
    if len(foreign)!=5 or sum(len(e["published_ships"]) for e in foreign)!=8:
        raise ValueError("V25 five cross-owner source episodes / eight ship appearances drift")
    if any(f["game_id"]!=521268 for f in foreign):
        raise ValueError("V25 cross-owner examples unexpectedly from another game")
    return originals,windows,foreign


def pre_foreign(conn,g,t,groups):
    relevant=[e for e in groups if (e["game_id"],e["turn"])==(g,t)]
    if not relevant:return []
    snaps,_=v9.pre_snapshots(conn,game=g,before=t-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),t-1)
    out=[]
    for ep in relevant:
        for stored in ep["published_ships"]:
            sid=stored["ship_id"]
            found=roster.get(sid)
            if found is None:raise ValueError("V25 Tminus1 foreign passenger owner-current missing")
            owner,ship=found
            start=xy((ship.get("x"),ship.get("y")))
            hull=integer(ship.get("hullid",ship.get("hull_id")))
            warp=integer(ship.get("warp"))
            fuel=integer(ship.get("neutronium"))
            if (owner!=stored["owner_id"] or hull!=stored["hull_id"]
                or warp!=stored["warp"] or fuel!=stored["fuel"]
                or start!=xy(ep["source"])):
                raise ValueError("V25 frozen foreign ship identity/position/order drift")
            way=xy((ship.get("targetx"),ship.get("targety")))
            tow_ids=sorted(
                shid for shid,(_owner,raw) in roster.items()
                if integer(raw.get("mission"))==v26.v16.TOW_MISSION_ID
                and integer(raw.get("mission1target"))==sid)
            out.append({
                "game_id":g,"turn":t,
                "actor_id":ep["actor_id"],"actor_owner_id":ep["actor_owner"],
                "chunnel_target_id":ep["target_id"],
                "ship_id":sid,"owner_id":owner,"hull_id":hull,
                "Tminus1_source":ep["source"],"Tminus1_target":ep["target"],
                "Tminus1_warp":warp,"Tminus1_fuel":fuel,
                "Tminus1_waypoint":list(way) if way else None,
                "Tminus1_mission":integer(ship.get("mission")),
                "Tminus1_inbound_tow_request_ids":tow_ids,
                "V25_frozen_T_at_target":stored["T_at_frozen_target"],
                "V25_frozen_T_position":stored["T_position"],
                "posthost_not_used_to_select":True,
            })
    return out


def compare_all(original,windows,pre,current):
    rows=[]
    for g,t in windows:
        full=pre[g,t]
        for item in full["Tminus1_actor_orders"]:
            key=(g,t,item["ship_id"],item["target_ship_id"])
            frozen=original[key]
            if frozen["Tminus1_cohort"]!="LONG_CONVENTIONAL_PASS":continue
            owner=item["owner_id"]
            actor_status,actor=v13._current_ship(current[g,t],item["ship_id"],owner,56)
            target_status,target=v13._current_ship(current[g,t],item["target_ship_id"],owner,56)
            actor_at=xy((actor.get("x"),actor.get("y"))) if actor else None
            target_at=xy((target.get("x"),target.get("y"))) if target else None
            expected_actor=xy(frozen["T_position"]) if frozen["T_position"] else None
            if actor_at!=expected_actor:
                raise ValueError("V25 long actor T owner-current comparison drift")
            dest=xy(item["Tminus1_target"])
            rows.append({
                "game_id":g,"turn":t,"actor_id":item["ship_id"],
                "target_ship_id":item["target_ship_id"],"owner_id":owner,
                "Tminus1_actor_source":item["Tminus1_source"],
                "Tminus1_frozen_target":item["Tminus1_target"],
                "V25_endpoint_status":frozen["T_status"],
                "T_actor_owner_current_status":actor_status,
                "T_target_owner_current_status":target_status,
                "T_actor_position":list(actor_at) if actor_at else None,
                "T_target_position":list(target_at) if target_at else None,
                "T_target_moved_from_frozen_position":(
                    target_at!=dest if target_at is not None else None),
                "T_actor_and_current_target_colocated":(
                    actor_at==target_at if actor_at is not None and target_at is not None else None),
                "actual_Host_Chunnel_activation_proven":False,
            })
    if len(rows)!=58:raise ValueError("V25 fixed 58 long candidate roster drift")
    return rows


def moving_report(rows):
    by_old=defaultdict(Counter)
    by_game=defaultdict(Counter)
    for r in rows:
        by_old[r["V25_endpoint_status"]][
            "T_ACTOR_WITH_CURRENT_TARGET" if r["T_actor_and_current_target_colocated"] is True
            else "T_ACTOR_NOT_WITH_CURRENT_TARGET" if r["T_actor_and_current_target_colocated"] is False
            else "ABSTAIN_TARGET_OR_ACTOR_T"]+=1
        by_game[r["game_id"]][r["V25_endpoint_status"]]+=1
    focus=next(r for r in rows if (r["game_id"],r["turn"],r["actor_id"],r["target_ship_id"])==MOVED)
    if (focus["V25_endpoint_status"]!="ELSEWHERE" or
        focus["T_target_moved_from_frozen_position"] is not True or
        focus["T_actor_and_current_target_colocated"] is not True):
        raise ValueError("V26 actor and moving target no longer jointly observed")
    return {
        **base("moving_targets"),
        "summary":{
            "frozen_V25_long_candidate_actor_rows":len(rows),
            "frozen_V25_long_game_turn_windows":len({(r["game_id"],r["turn"]) for r in rows}),
            "frozen_V25_long_distinct_games":len({r["game_id"] for r in rows}),
            "T_actor_target_colocation_by_original_V25_result":{
                k:dict(sorted(v.items())) for k,v in sorted(by_old.items())},
            "G403181_T60_143_and_202_colocated_after_T":True,
            "G403181_T60_target_202_moved":True,
            "conventional_55_1_2_scoring_not_retroactively_changed":True,
            "actual_chunnel_execution_or_target_movement_phase_proven":False,
        },
        "observed_long_actor_and_target_T_endpoints":rows,
        "by_game_original_V25_status":{str(k):dict(sorted(v.items())) for k,v in sorted(by_game.items())},
    }


def foreign_report(frozen,post):
    result=[]
    for f in frozen:
        g,t=f["game_id"],f["turn"]
        obs,ship=v13._current_ship(post[g,t],f["ship_id"],f["owner_id"],f["hull_id"])
        found=xy((ship.get("x"),ship.get("y"))) if ship else None
        expected=xy(f["V25_frozen_T_position"]) if f["V25_frozen_T_position"] else None
        if found!=expected:raise ValueError("V25 foreign T position changed under read-only replay")
        target=xy(f["Tminus1_target"])
        src=xy(f["Tminus1_source"])
        way=xy(f["Tminus1_waypoint"]) if f["Tminus1_waypoint"] else None
        direct=(f["Tminus1_warp"] is not None
            and f["Tminus1_warp"]>0 and way==target
            and hypot(src[0]-target[0],src[1]-target[1])<=f["Tminus1_warp"]**2)
        result.append({
            **f,"T_owner_current_status":obs,
            "T_reobserved_position":list(found) if found is not None else None,
            "T_at_frozen_target":found==target if found is not None else None,
            "Tminus1_direct_waypoint_warp_geometry_possible":direct,
            "co-location_is_not_automatic_passenger_eligibility":True,
        })
    if len(result)!=8 or sum(x["T_at_frozen_target"] is True for x in result)!=7:
        raise ValueError("V25 published 8 foreign-source / 7 frozen-target count drift")
    return {
        **base("foreign_routes"),
        "summary":{
            "frozen_V25_foreign_owner_ship_appearances":len(result),
            "frozen_foreign_owner_source_episodes":len({
                (x["game_id"],x["turn"],x["actor_id"],x["chunnel_target_id"]) for x in result}),
            "frozen_foreign_owner_distinct_games":len({x["game_id"] for x in result}),
            "T_foreign_at_frozen_destination":sum(x["T_at_frozen_target"] is True for x in result),
            "T_foreign_not_at_frozen_destination":sum(x["T_at_frozen_target"] is False for x in result),
            "foreign_Tminus1_direct_waypoint_warp_possible":sum(
                x["Tminus1_direct_waypoint_warp_geometry_possible"] for x in result),
            "foreign_Tminus1_inbound_tow_requests":sum(
                len(x["Tminus1_inbound_tow_request_ids"]) for x in result),
            "same_site_ephemeral_correlations_not_independent_mechanic_proof":True,
        },
        "frozen_foreign_owner_orders_T_endpoint_comparisons":result,
    }


def missing_report(conn,pre,post):
    items=[]
    # T+1 OWNER-CURRENT is a retrospective provenance follow-up.
    # It is NEVER used to select T-1 cases, score V25, or inspect N+1 VCR.
    for g,t,sid,tid,owner in MISSING:
        T_ref=v9.member_refs_for_turns(conn,game_id=g,turns={t},include_embedded_turn=False)
        Tp1_ref=v9.member_refs_for_turns(conn,game_id=g,turns={t+1},include_embedded_turn=False)
        pids=sorted({r.perspective_player_id for r in T_ref})
        next_pids=sorted({r.perspective_player_id for r in Tp1_ref})
        if owner not in pids or len(pids)!=12:
            raise ValueError("V26 full 12-player archive T appearance changed")
        actor_t,raw_t=v13._current_ship(post[g,t],sid,owner,56)
        target_t,tar_t=v13._current_ship(post[g,t],tid,owner,56)
        if (actor_t!="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE" or raw_t is not None
            or target_t!="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE" or tar_t is not None):
            raise ValueError("V26 T owner-current missing actor and target drift")
        later_label="ABSTAIN_TPLUS1_ARCHIVE_NOT_AVAILABLE"
        actor_plus=target_plus=None
        later_actor_position=later_target_position=None
        if Tp1_ref:
            try:
                nxt=v9.after_owner_current(conn,game=g,turn=t+1)
                actor_plus,ar=v13._current_ship(nxt,sid,owner,56)
                target_plus,tr=v13._current_ship(nxt,tid,owner,56)
                a=xy((ar.get("x"),ar.get("y"))) if ar else None
                b=xy((tr.get("x"),tr.get("y"))) if tr else None
                later_actor_position=list(a) if a is not None else None
                later_target_position=list(b) if b is not None else None
                later_label="TPLUS1_OWNER_CURRENT_COMPARED_NOT_PREDICTIVE"
            except (ValueError,TypeError,KeyError):
                later_label="ABSTAIN_TPLUS1_OWNER_CURRENT_CONTEXT"
        items.append({
            "game_id":g,"turn":t,"actor_id":sid,"target_id":tid,
            "owner_id":owner,
            "T_owner_perspective_present":True,
            "T_owner_current_actor_status":actor_t,
            "T_owner_current_target_status":target_t,
            "Tplus1_owner_perspective_present":owner in next_pids,
            "Tplus1_provenance_status":later_label,
            "Tplus1_actor_status":actor_plus,
            "Tplus1_target_status":target_plus,
            "Tplus1_actor_position":later_actor_position,
            "Tplus1_target_position":later_target_position,
            "Tplus1_not_used_to_relabel_V25_or_infer_death":True,
            "Nplus1_VCR_used":False,
        })
    return {
        **base("identity_provenance"),
        "summary":{
            "T_owner_perspectives_present_both_original_missing_actors":len(items),
            "missing_actor_and_target_owner_current_pairs":len(items),
            "missing_distinct_game_turns":len({(x["game_id"],x["turn"]) for x in items}),
            "Tplus1_snapshot_provenance_statuses":dict(sorted(Counter(
                x["Tplus1_provenance_status"] for x in items).items())),
            "Tplus1_actor_identity_statuses":dict(sorted(Counter(
                x["Tplus1_actor_status"] for x in items).items(),key=lambda x:str(x[0]))),
            "retrospective_Tplus1_not_validated_Host_activations":True,
            "no_VCR_used":True,
        },
        "T_owner_current_missing_and_Tplus1_followups":items,
    }


def base(phase):
    return {
        "schema":SCHEMA,"status":STATUS,"phase":phase,
        "source_V26_manifest_git_blob_sha1":V26_BLOBS["manifest"],
        "source_V25_manifest_git_blob_sha1":V25_BLOBS["manifest"],
        "generation_sha256":NEW_DB_SHA256,
        "all_33_Tminus1_windows_frozen_before_any_T_or_Tplus1":True,
        "same_V25_8_game_corpus_not_new_validation":True,
        "Nplus1_VCR_used":False,
        "Host_activation_or_combat_prediction_proven":False,
        "new_production_Host_movement_or_combat_predictions":0,
    }


def publish(outdir,docs):
    outdir.mkdir(parents=True,exist_ok=True)
    index={}
    for name,doc in zip(REPORTS,docs,strict=True):
        target=outdir/(name+".json")
        temp=target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(doc,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(target)
        index[name]={
            "file":target.name,
            "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            "summary":doc["summary"],
        }
        print("===== C5 V27",name,"=====")
        print("status:",doc["status"])
        print("summary:",doc["summary"])
        print("output:",target)
    manifest={
        "schema":SCHEMA,"phase":"manifest",
        "status":"V27_MOVING_TARGET_IDENTITY_AND_FOREIGN_ROUTE_BATCH_COMPLETE",
        "all_three_reports_complete":len(index)==3,
        "report_sha256":index,
        "new_db_sha256":NEW_DB_SHA256,
        "V26_manifest_git_blob_sha1":V26_BLOBS["manifest"],
        "new_Host_chunnel_activation_predictions":0,
        "relabel_V25_old_endpoint_scores":False,
        "Nplus1_VCR_used":False,
    }
    target=outdir/"manifest.json"
    temp=target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    temp.replace(target)
    print("===== C5 V27 ALL THREE REPORTS / MANIFEST COMPLETE =====")
    print("status:",manifest["status"])
    print("output:",target)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--database",type=Path,required=True)
    for name in V25_BLOBS:
        p.add_argument("--v25-"+name.replace("_","-"),dest="v25_"+name,type=Path,required=True)
    for name in V26_BLOBS:
        p.add_argument("--v26-"+name.replace("_","-"),dest="v26_"+name,type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        origins={}
        payload={}
        for group,items in (("v25",V25_BLOBS),("v26",V26_BLOBS)):
            for name,digest in items.items():
                doc,data=pinned(getattr(args,group+"_"+name),digest)
                origins[group+"_"+name]=doc
                payload[group+"_"+name]=data
        orig,windows,foreign=source_gate(
            {k:origins["v25_"+k] for k in V25_BLOBS},
            {k:origins["v26_"+k] for k in V26_BLOBS},payload)
        db=args.database.resolve()
        if not db.is_file() or db.name!=NEW_DB_NAME:
            raise ValueError("specific immutable new public8 generation missing")
        print("[c5-v27] checking new public8 SHA256 ONCE, read-only",flush=True)
        started=time.monotonic()
        with db.open("rb") as fd:sha=hashlib.file_digest(fd,"sha256").hexdigest()
        if sha!=NEW_DB_SHA256:raise ValueError("pinned new game corpus SHA256 drift")
        print(f"[c5-v27] verified in {time.monotonic()-started:.1f}s",flush=True)
        conn=duckdb.connect(str(db),read_only=True)
        try:
            pre={}
            precross=[]
            for n,(g,t) in enumerate(windows,1):
                print(f"[c5-v27] PRE [{n}/{len(windows)}] G{g} T{t}",flush=True)
                pre[g,t]=v26.select_roster(conn,g,t,orig)
                precross.extend(pre_foreign(conn,g,t,foreign))
            if len(precross)!=8:raise ValueError("V25 fixed eight foreign T-1 source identities incomplete")
            # HARD BARRIER: no T/T+1 reads before 33 complete T-1 rosters.
            post={}
            for n,(g,t) in enumerate(windows,1):
                print(f"[c5-v27] POST [{n}/{len(windows)}] G{g} T{t}",flush=True)
                post[g,t]=v9.after_owner_current(conn,game=g,turn=t)
                v26.replay_post(pre[g,t],orig,post[g,t])
            endpoints=compare_all(orig,windows,pre,post)
            a=moving_report(endpoints)
            b=missing_report(conn,pre,post)
            c=foreign_report(precross,post)
        finally:conn.close()
        publish(args.output_dir,(a,b,c))
    except (OSError,ValueError,TypeError,KeyError,IndexError,duckdb.Error,json.JSONDecodeError) as error:
        print("ERROR V27:",error,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
