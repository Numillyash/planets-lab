"""V18: V17 outcome-selected anomalies and owner-current archive coverage.

Post-hoc diagnostic: not a new holdout. Freeze all targeted T-1 facts
and identities before reading ANY T archive. T perspectives explain
visibility/owner-current status only, never serve as alternate factual
precombat position or proof of a short-distance Chunnel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for item in (ROOT/"src",Path(__file__).resolve().parent):
    if str(item) not in sys.path:sys.path.insert(0,str(item))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,member_refs_for_turns,reconstruct_members
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot,mechanics_projection
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn,TOW_MISSION_ID
import combat_c5_disjoint_discriminative_chunnel_gates_v17 as v17
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_chunnel_endpoint_screen_v11 as v11
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-short-chunnel-and-archive-coverage.v18"
STATUS="POSTHOC_V17_ANOMALY_AND_OWNER_CURRENT_VISIBILITY_NOT_CHUNNEL_RULE"
V17_BLOB="a6256b70dc63b9b7126a211245bc65ce20ece863"
GENERATION=v17.GENERATION
SHA256=v17.SHA256
FROZEN_WINDOWS=48
FROZEN_CANDIDATES=113


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def point(v:Any)->tuple[int,int]|None:
    return v17.point(v)


def load_source(path:Path):
    data=path.read_bytes()
    calculated=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if calculated!=V17_BLOB:raise ValueError("V17 Git blob mismatch")
    report=json.loads(data)
    if not isinstance(report,dict):raise ValueError("V17 source root invalid")
    return report


def frozen_v17(report:Mapping[str,Any]):
    if (report.get("schema")!=v17.SCHEMA or
        report.get("status")!=v17.STATUS or
        report.get("source_db_sha256")!=SHA256 or
        report.get("source_v16_git_blob_sha1")!=v17.V16_BLOB):
        raise ValueError("V17 provenance/schema changed")
    summary=report.get("summary")
    expected={
        "selected_game_count":16,"selected_window_count":48,
        "evaluated_windows":48,"context_abstentions":0,
        "candidate_stock_firecloud_edges":113,
        "discriminative_positive_Tminus1_edges":98,
        "discriminative_single_failed_Tminus1_edges":6,
        "non_discriminative_colocated_Tminus1_edges":9,
        "Tminus1_all_windows_frozen_before_T":True,
        "new_Host_movement_or_combat_predictions_promoted":0,
        "Chunnel_activation_proven":False,
        "Nplus1_VCR_used":False,"independent_new_corpus":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in expected.items()):
        raise ValueError("V17 original population/guard changed")
    windows=report.get("windows")
    if not isinstance(windows,list) or len(windows)!=48:
        raise ValueError("V17 window cohort truncated")
    original={}
    windows_seen=set()
    statuses=Counter()
    for window in windows:
        if not isinstance(window,Mapping):raise ValueError("bad V17 window")
        g,t=integer(window.get("game_id")),integer(window.get("turn"))
        if g is None or g<=0 or t is None or t<=1 or (g,t) in windows_seen:
            raise ValueError("duplicate V17 window")
        windows_seen.add((g,t))
        for case in window.get("edges",[]):
            if not isinstance(case,Mapping):raise ValueError("malformed V17 edge")
            key=(g,t,case.get("initiator_ship_id"),case.get("target_ship_id"))
            if (any(integer(z) is None or z<=0 for z in key)
                or key in original or
                case.get("Host_Chunnel_activation_or_inactivation_proven") is not False or
                case.get("Nplus1_VCR_used") is not False or
                point(case.get("source")) is None or
                point(case.get("target")) is None):
                raise ValueError("duplicate/invalid V17 edge or proof boundary")
            original[key]=case
            statuses[(case["cohort"],case["T_actor_status"])]+=1
    if len(original)!=113 or len({g for g,_ in windows_seen})!=16:
        raise ValueError("V17 census not preserved")
    positives=[(key,case) for key,case in original.items()
               if case["cohort"]=="ALL_TMINUS1_GATES_PASS" and
               case["T_actor_status"].startswith("ABSTAIN")]
    negatives=[(key,case) for key,case in original.items()
               if case["cohort"]=="ONE_TMINUS1_GATE_FAILS" and
               case["Tminus1_source_differs_from_target"] is True]
    short_hit=[(key,case) for key,case in negatives
               if case["T_actor_status"]=="T_ACTOR_AT_DISTINCT_FROZEN_TARGET"]
    if len(positives)!=14 or len(negatives)!=6 or len(short_hit)!=1:
        raise ValueError("V17 frozen 14/6/1 targeted census changed")
    if (short_hit[0][0]!=(467386,75,467,80) or
        short_hit[0][1]["Tminus1_distance_ly"]!=25 or
        point(short_hit[0][1]["source"])!=(1141,1459) or
        point(short_hit[0][1]["target"])!=(1126,1439)):
        raise ValueError("V17 25LY anomaly identity changed")
    targets=dict(positives+negatives)
    return targets,tuple(sorted({(g,t) for g,t,_,_ in targets}))


def _ship_tminus1(case:Mapping[str,Any],roster:Mapping[int,Any]):
    sid,target,owner=(case[k] for k in
        ("initiator_ship_id","target_ship_id","owner_id"))
    for ship_id,expected in ((sid,point(case["source"])),
                             (target,point(case["target"]))):
        entry=roster.get(ship_id)
        if entry is None or entry[0]!=owner:raise ValueError("V17 owner-current Tminus1 edge missing")
        raw=entry[1]
        if (integer(raw.get("hullid",raw.get("hull_id")))!=56 or
            point((raw.get("x"),raw.get("y")))!=expected):
            raise ValueError("V17 Tminus1 Firecloud identity/position drift")
    actor=roster[sid][1]
    tar=roster[target][1]
    if (v11.numeric_target(actor.get("friendlycode",actor.get("friendly_code")))!=target%1000 or
        integer(actor.get("neutronium"))!=case["actor_Tminus1_fuel"] or
        integer(tar.get("neutronium"))!=case["target_Tminus1_fuel"] or
        integer(actor.get("warp"))!=case["actor_Tminus1_warp"] or
        integer(tar.get("warp"))!=case["target_Tminus1_warp"]):
        raise ValueError("V17 Tminus1 actor/target numeric control drift")
    at_start=[s for s,(_o,r) in roster.items()
              if point((r.get("x"),r.get("y")))==point(case["source"])]
    at_dest=[s for s,(_o,r) in roster.items()
             if point((r.get("x"),r.get("y")))==point(case["target"])]
    tow=[{
        "tower_ship_id":s,"tower_owner_id":own,
        "tower_start_at_actor":point((raw.get("x"),raw.get("y")))==point(case["source"]),
        "tower_start_at_target":point((raw.get("x"),raw.get("y")))==point(case["target"]),
        "request_not_confirmed_tow_lock":True,
    } for s,(own,raw) in roster.items() if
        integer(raw.get("mission"))==TOW_MISSION_ID and
        integer(raw.get("mission1target")) in (sid,target)]
    def reduced(ship_id,raw):
        waypoint=point((raw.get("targetx"),raw.get("targety")))
        return {
            "ship_id":ship_id,"start":list(point((raw.get("x"),raw.get("y")))),
            "waypoint":list(waypoint) if waypoint is not None else None,
            "mission":integer(raw.get("mission")),
            "warp":integer(raw.get("warp")),
            "fuel":integer(raw.get("neutronium")),
            "damage":integer(raw.get("damage")),
        }
    background=[{
        "ship_id":ship,"owner_id":own,
        "Tminus1_start":list(point((raw.get("x"),raw.get("y")))),
        "Tminus1_warp":integer(raw.get("warp")),
        "is_stock_firecloud":integer(raw.get("hullid",raw.get("hull_id")))==56,
    } for ship,(own,raw) in sorted(roster.items())
        if ship not in (sid,target)
        and point((raw.get("x"),raw.get("y"))) in
        (point(case["source"]),point(case["target"]))]
    return {
        "Tminus1_actor":reduced(sid,actor),
        "Tminus1_target":reduced(target,tar),
        "Tminus1_tow_requests_on_endpoints":tow,
        "Tminus1_other_ships_colocated_with_actor":len(at_start)-1,
        "Tminus1_other_ships_colocated_with_target":len(at_dest)-1,
        "Tminus1_nearby_ships_at_endpoints":background,
        "Tminus1_numeric_friendly_code_target_confirmed":True,
        "Tminus1_candidate_source_target_distance_ly":case["Tminus1_distance_ly"],
        "Tminus1_25ly_event_not_assigned_cause":True,
    }


def freeze_tminus1_window(conn:Any,game:int,turn:int,cases:Mapping[tuple[int,...],Any]):
    snaps,_=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),turn-1)
    rows={}
    for key,case in sorted(cases.items()):
        if key[:2]!=(game,turn):continue
        rows[key]=_ship_tminus1(case,roster)
    if not rows:raise ValueError("targeted Tminus1 window empty")
    return rows


def _t_snapshots(conn:Any,game:int,turn:int):
    refs=member_refs_for_turns(conn,game_id=game,turns={turn},include_embedded_turn=False)
    if not refs:raise ValueError("T perspectives unavailable")
    snapshots=[]
    perspectives=set()
    for ref,parsed in reconstruct_members(conn,refs):
        if (ref.game_id!=game or ref.archive_turn!=turn or ref.embedded_turn!=turn or
            not isinstance(parsed.get("game"),Mapping) or
            integer(parsed["game"].get("id"))!=game or
            integer(parsed["game"].get("turn"))!=turn):
            raise ValueError("T archive snapshot identity drift")
        projection=mechanics_projection(parsed,member=ref.turn_member.name)
        player=projection.get("player")
        if not isinstance(player,Mapping) or integer(player.get("id"))!=ref.perspective_player_id:
            raise ValueError("T perspective identity mismatch")
        snapshots.append(ArchiveTurnSnapshot(
            member=ref.turn_member,game_id=game,player_id=ref.perspective_player_id,
            embedded_turn=turn,snapshot_hash=ref.decoded_payload_sha256,
            mechanics_payload=projection,
        ))
        perspectives.add(ref.perspective_player_id)
    return tuple(snapshots),frozenset(perspectives)


def perspective_coverage(case:Mapping[str,Any],snapshots,owners):
    grouped=group_perspective_records(snapshots,"ship")
    turn=case["turn"]
    source_owner=case["owner_id"]
    details={}
    for role,sid in (("actor",case["initiator_ship_id"]),
                     ("target",case["target_ship_id"])):
        records=grouped.get((turn,sid),())
        current=[r for r in records if r.is_current]
        stale=[r for r in records if not r.is_current]
        fresh_owners=sorted({integer(r.raw.get("ownerid",r.raw.get("owner_id")))
                             for r in current if
                             integer(r.raw.get("ownerid",r.raw.get("owner_id"))) is not None})
        details[role]={
            "ship_id":sid,
            "T_fresh_perspectives":[r.player_id for r in current],
            "T_stale_perspectives":[r.player_id for r in stale],
            "T_fresh_reported_owners":fresh_owners,
            "T_owner_current_record_available":
                any(r.player_id==source_owner and r.is_current and
                    integer(r.raw.get("ownerid",r.raw.get("owner_id")))==source_owner
                    for r in records),
            "T_stale_contacts_not_authoritative":True,
        }
    return {
        "T_archived_perspective_player_ids":sorted(owners),
        "T_source_owner_perspective_present":source_owner in owners,
        "T_fresh_ship_evidence":details,
        "T_visibility_only_not_host_mechanic_or_ship_destruction":True,
    }


def post_audit(original:Mapping[str,Any],pre:Mapping[str,Any],current,snapshots,owners):
    key=(original["game_id"],original["turn"],
         original["initiator_ship_id"],original["target_ship_id"])
    verified=v17.compare_one(original,current)
    if (verified["T_actor_status"]!=original["T_actor_status"] or
        verified["T_actor_position"]!=original["T_actor_position"] or
        verified["T_actor_net_fuel_delta_KT"]!=original["T_actor_net_fuel_delta_KT"]):
        raise ValueError("V17 posthost outcome no longer reproducible")
    return {
        "game_id":key[0],"turn":key[1],"initiator_ship_id":key[2],
        "target_ship_id":key[3],"owner_id":original["owner_id"],
        "V17_frozen_cohort":original["cohort"],
        "V17_frozen_gate":original["single_failing_gate"],
        "V17_posthost_classification":original["T_actor_status"],
        "Tminus1_frozen_features":pre,
        "T_archive_visibility":perspective_coverage(original,snapshots,owners),
        "T_after_Host_actor_position":original["T_actor_position"],
        "T_after_Host_target_position":original["T_target_position"],
        "T_actor_net_fuel_delta_KT":original["T_actor_net_fuel_delta_KT"],
        "T_current_owner_source_provenance_only":True,
        "Chunnel_activation_or_short_distance_override_proven":False,
        "Nplus1_VCR_used":False,
    }


def build_report(conn:Any,source:Mapping[str,Any]):
    cases,windows=frozen_v17(source)
    first={}
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v18] PRE [{n}/{len(windows)}] G{g} T{t}",flush=True)
        first[g,t]=freeze_tminus1_window(conn,g,t,cases)
    # ALL affected T-1 windows frozen before ANY T archive is read.
    output=[]
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v18] POST [{n}/{len(windows)}] G{g} T{t}",flush=True)
        current=v9.after_owner_current(conn,game=g,turn=t)
        snapshots,perspective_ids=_t_snapshots(conn,g,t)
        for key,pre in sorted(first[g,t].items()):
            output.append(post_audit(cases[key],pre,current,snapshots,perspective_ids))
    if len(output)!=20:raise ValueError("V17 targeted 14/6 mismatch census altered")
    unavailable=[r for r in output if r["V17_posthost_classification"].startswith("ABSTAIN")]
    source_missing=sum(
        not r["T_archive_visibility"]["T_source_owner_perspective_present"]
        for r in unavailable)
    actor_current_missing=sum(
        not r["T_archive_visibility"]["T_fresh_ship_evidence"]["actor"][
            "T_owner_current_record_available"]
        for r in unavailable)
    by_window=defaultdict(Counter)
    for r in unavailable:
        by_window[f'G{r["game_id"]}/T{r["turn"]}'][r["V17_posthost_classification"]]+=1
    anomaly=[r for r in output if (r["game_id"],r["turn"],r["initiator_ship_id"],
                              r["target_ship_id"])==(467386,75,467,80)]
    if len(anomaly)!=1:raise ValueError("G467386/T75 25ly source unavailable")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v17_git_blob_sha1":V17_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "V17_frozen_48_windows_16_games":True,
            "V17_frozen_113_candidates":113,
            "targeted_V17_positive_owner_current_abstentions":14,
            "targeted_V17_discriminative_negative_edges":6,
            "targeted_Tminus1_windows":len(windows),
            "reverified_Tminus1_T_cases":len(output),
            "source_owner_T_perspective_missing_appearances":source_missing,
            "actor_T_owner_current_unavailable_appearances":actor_current_missing,
            "posthoc_25ly_anomaly_cases":len(anomaly),
            "new_Host_movement_or_combat_predictions":0,
            "Host_short_distance_Chunnel_or_activation_proven":False,
            "Nplus1_VCR_used":False,
        },
        "positive_abstention_window_clusters":{
            k:dict(sorted(v.items())) for k,v in sorted(by_window.items())},
        "short_distance_25ly_case":anomaly[0],
        "targeted_case_evaluations":output,
        "boundary":(
            "All 20 cases are POST-HOC selected from published V17 after "
            "examining outcomes, not new heldout predictions. Tminus1 actor/"
            "target positions, orders, fuel, waypoint, tow requests and "
            "colocations are collected for all selected windows BEFORE "
            "reading T. T perspective census and fresh/stale information "
            "are for archive visibility attribution only. A missing "
            "owner-current observation is not a missing/destroyed starship "
            "and a fresh non-owner report cannot become an authoritative "
            "current precombat position. G467386/T75 Firecloud #467 to "
            "#80 had Tminus1 separation 25LY: posthost coincidence and "
            "net fuel delta48KT do not prove a sub-100LY Chunnel. "
            "No activation rule, future VCR, mine RNG or production executor "
            "updates follow from this retrospective audit."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-v17",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    try:
        report=load_source(a.frozen_v17)
        frozen_v17(report)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("public100 pinned DB unavailable")
        print("[c5-v18] checking pinned public100 SHA256 once",flush=True)
        ts=time.monotonic()
        with db.open("rb") as f:hash_val=hashlib.file_digest(f,"sha256").hexdigest()
        if hash_val!=SHA256:raise ValueError("public100 checksum drift")
        print(f"[c5-v18] checksum verified in {time.monotonic()-ts:.1f}s; read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:result=build_report(conn,report)
        finally:conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temp=a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 V17 ARCHIVE VISIBILITY AND 25-LY CHUNNEL ANOMALY V18 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
