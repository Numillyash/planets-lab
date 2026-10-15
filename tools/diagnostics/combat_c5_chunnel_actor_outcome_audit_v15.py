"""V15 outcome-blind actor/target outcomes for all V14 T-1 Firecloud edges.

Replays EXACT frozen metadata cohort and reconstructs all T-1 candidate
edges, passenger exposure and ten-per-window model negative controls.
No after-T archive is read until all 60 windows have frozen. T-side
observations never select cases. Actor/target endpoint+fuel signatures
are observational post-Host indicators, NOT a Host activation oracle.

Do not use posthoc T outcomes to change the Firecloud activation resolver.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for x in (ROOT/"src",Path(__file__).resolve().parent):
    if str(x) not in sys.path:sys.path.insert(0,str(x))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_conditional_chunnel_holdout_v14 as v14
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-chunnel-actor-outcome-audit.v15"
STATUS="V14_TMINUS1_ALL_ACTORS_AND_CONTROL_RESIDUALS_POSTHOST_OBSERVATIONAL"
V14_BLOB="60aeb5ae5ccc828116911bbc61bd752374bc2df7"
GENERATION=v14.GENERATION
SHA256=v14.SHA256


def integer(value:Any)->int|None:
    return value if type(value) is int else None


def point(value:Any)->tuple[int,int]|None:
    return v14.point(value)


def pinned_v14(path:Path)->dict[str,Any]:
    data=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if sha!=V14_BLOB:raise ValueError("immutable V14 report Git blob mismatch")
    report=json.loads(data)
    if not isinstance(report,dict):raise ValueError("V14 root object missing")
    return report


def verify_v14(v14report:Mapping[str,Any],excluded:frozenset[int]):
    if (v14report.get("schema")!=v14.SCHEMA or
        v14report.get("status")!=v14.STATUS or
        v14report.get("source_v6_git_blob_sha1")!=v14.V6_BLOB or
        v14report.get("source_v9_git_blob_sha1")!=v14.V9_BLOB or
        v14report.get("source_v13_git_blob_sha1")!=v14.V13_BLOB or
        v14report.get("source_db_sha256")!=SHA256):
        raise ValueError("V14 provenance drift")
    summary=v14report.get("summary")
    expect={
        "selected_game_count":20,"selected_window_count":60,
        "V6_V9_V13_game_overlap":0,"completed_windows":60,
        "context_abstentions":0,
        "eligible_Tminus1_Firecloud_edges_in_completed_windows":95,
        "frozen_unambiguous_candidate_passengers":55,
        "ambiguous_passenger_exclusions":0,
        "new_production_Host_movement_or_combat_predictions":0,
        "Chunnel_execution_independently_proven":False,
        "Nplus1_VCR_used":False,"new_independent_corpus":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in expect.items()):
        raise ValueError("V14 frozen protocol/sample drift")
    counts=summary.get("T_passenger_conditional_vs_baseline_counts")
    control=summary.get("T_negative_normal_control_counts")
    if not isinstance(counts,Mapping) or counts!={"T_MATCHES_CONDITIONAL_CHUNNEL_ONLY":55}:
        raise ValueError("V14 passenger outcome denominator drift")
    expected_controls={
        "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":1,
        "ABSTAIN_T_HULL_IDENTITY_DRIFT":1,"ABSTAIN_T_OWNER_DRIFT":4,
        "MATCH":526,"MISMATCH":8,
    }
    if not isinstance(control,Mapping) or dict(control)!=expected_controls:
        raise ValueError("V14 negative control denominator drift")
    selection=v14report.get("frozen_selection")
    if not isinstance(selection,Mapping) or selection.get("no_VCR_or_T_outcome_selection") is not True:
        raise ValueError("V14 selection was not outcome blind")
    windows=selection.get("selected_game_turns")
    if not isinstance(windows,list) or len(windows)!=60:
        raise ValueError("V14 frozen windows unavailable")
    original=set()
    for rec in windows:
        if not isinstance(rec,Mapping):raise ValueError("bad V14 metadata window")
        game,turn=integer(rec.get("game_id")),integer(rec.get("turn"))
        if (game is None or game<=0 or turn is None or turn<2
            or game in excluded or (game,turn) in original):
            raise ValueError("V14 selected-game overlap or duplicate")
        original.add((game,turn))
    if len({g for g,_ in original})!=20:
        raise ValueError("V14 game diversity lost")
    reported=v14report.get("window_evaluations")
    if not isinstance(reported,list) or len(reported)!=60:
        raise ValueError("V14 published window evaluations incomplete")
    by_window={}
    for row in reported:
        if not isinstance(row,Mapping):raise ValueError("bad V14 published result")
        key=(row.get("game_id"),row.get("turn"))
        if key not in original or key in by_window:
            raise ValueError("V14 published window ID mismatch")
        by_window[key]=row
    return tuple(sorted(original)),by_window


def pre_window(conn:Any,game:int,turn:int):
    """Never queries T archive; reader must call ALL pre_window first."""
    snapshots,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    features=v13.freeze_window(game,turn,snapshots,raws)
    if (features.get("game_id"),features.get("turn"))!=(game,turn):
        raise ValueError("T-1 independent window identity drift")
    cases=v14.freeze_conditional_cases(features)
    roster=_owner_rows_for_turn(
        group_perspective_records(snapshots,"ship"),turn-1)
    raw_controls={}
    for c in cases["preoutcome_nonexposed_negative_controls"]:
        sid=c["ship_id"]
        entry=roster.get(sid)
        if entry is None or entry[0]!=c["Tminus1_owner_id"]:
            raise ValueError("T-1 negative control owner-current unavailable")
        raw=entry[1]
        if integer(raw.get("hullid",raw.get("hull_id")))!=c["Tminus1_hull_id"]:
            raise ValueError("T-1 negative control hull differs from frozen")
        raw_controls[sid]={
            "Tminus1_start":list(point((raw.get("x"),raw.get("y"))))
                if point((raw.get("x"),raw.get("y"))) is not None else None,
            "Tminus1_waypoint":list(point((raw.get("targetx"),raw.get("targety"))))
                if point((raw.get("targetx"),raw.get("targety"))) is not None else None,
            "Tminus1_warp":integer(raw.get("warp")),
            "Tminus1_mission":integer(raw.get("mission")),
            "Tminus1_fuel":integer(raw.get("neutronium")),
        }
    return {
        "game_id":game,"turn":turn,"features":features,"conditional_cases":cases,
        "negative_control_Tminus1_features":raw_controls,
    }


def get_observation(current:Mapping[int,Any],sid:int,owner:int,hull:int=56):
    return v13._current_ship(current,sid,owner,hull)


def actor_edge_after(edge:Mapping[str,Any],current:Mapping[int,Any],
                     game:int,turn:int):
    src=point(edge["initiator_Tminus1_source"])
    dest=point(edge["target_Tminus1_destination"])
    owner,actor,target=(edge[k] for k in
        ("owner_id","initiator_ship_id","target_ship_id"))
    actor_status,a=get_observation(current,actor,owner)
    target_status,t=get_observation(current,target,owner)
    apos=point((a.get("x"),a.get("y"))) if a is not None else None
    tpos=point((t.get("x"),t.get("y"))) if t is not None else None
    fuel=integer(a.get("neutronium")) if a is not None else None
    initial=integer(edge.get("initiator_Tminus1_fuel"))
    delta=initial-fuel if initial is not None and fuel is not None else None
    if a is None: status=actor_status
    elif apos==dest:status="T_ACTOR_AT_FROZEN_TARGET"
    elif apos==src:status="T_ACTOR_STILL_AT_TMINUS1_SOURCE"
    else:status="T_ACTOR_AT_OTHER_POSITION"
    return {
        "game_id":game,"turn":turn,
        "initiator_ship_id":actor,"target_ship_id":target,
        "owner_id":owner,"Tminus1_source":list(src),
        "Tminus1_target":list(dest),
        "Tminus1_actor_warp":edge["initiator_Tminus1_warp"],
        "Tminus1_actor_fuel":initial,
        "T_actor_observation_status":status,
        "T_target_observation_status":target_status,
        "T_actor_owner_current_position":list(apos) if apos is not None else None,
        "T_target_owner_current_position":list(tpos) if tpos is not None else None,
        "T_target_stayed_at_frozen_target":tpos==dest if tpos is not None else None,
        "T_actor_net_fuel_delta_KT":delta,
        "T_actor_net_delta_exactly_50":delta==50 if delta is not None else None,
        "T_actor_passage_consistent_with_target":apos==dest if apos is not None else None,
        "Tminus1_preselected_passenger_count":len(edge["Tminus1_passenger_candidates"]),
        "Tminus1_Tow_and_ambiguity_gates_from_v13":True,
        "Chunnel_execution_proven":False,
    }


def negative_comparison(control:Mapping[str,Any],pre:Mapping[str,Any],
                        current:Mapping[int,Any],
                        actors:list[Mapping[str,Any]],game:int,turn:int):
    sid=control["ship_id"]
    owner=control["Tminus1_owner_id"]
    hull=control["Tminus1_hull_id"]
    state,raw=get_observation(current,sid,owner,hull)
    observed=point((raw.get("x"),raw.get("y"))) if raw is not None else None
    forecast=point(control["Tminus1_model_endpoint"])
    if forecast is None:raise ValueError("Tminus1 normal control model missing")
    if raw is None:comparison=state
    elif observed==forecast:comparison="MATCH"
    else:comparison="MISMATCH"
    # These are POSTHOC explanations only, not features available to
    # earlier V14 negative control selection.
    possible_target_matches=[{
        "initiator_ship_id":e["initiator_ship_id"],
        "target_ship_id":e["target_ship_id"],
    } for e in actors if e["owner_id"]==owner and
        observed is not None and
        point(e["Tminus1_target"])==observed]
    candidate_source_distance=min((
        hypot(forecast[0]-point(e["Tminus1_source"])[0],
              forecast[1]-point(e["Tminus1_source"])[1])
        for e in actors if e["owner_id"]==owner),
        default=None)
    return {
        "game_id":game,"turn":turn,
        "ship_id":sid,"owner_id":owner,"hull_id":hull,
        "frozen_normal_endpoint":list(forecast),
        "T_owner_current_position":list(observed) if observed is not None else None,
        "status":comparison,
        "Tminus1_normal_input":pre,
        "Tminus1_distance_to_nearest_eligible_Firecloud_source":
            round(candidate_source_distance,4) if candidate_source_distance is not None else None,
        "POSTHOC_T_position_matches_another_eligible_target":possible_target_matches,
        "mine_hit_or_Chunnel_transport_proven":False,
    }


def revalidate_v14_comparison(published:Mapping[str,Any],
                              cases:Mapping[str,Any],
                              observed:Mapping[int,Any],
                              game:int,turn:int):
    """Outcome crosscheck *after* complete T-1 freeze, not selection."""
    fresh=v14.post_compare(cases,observed)
    if len(fresh["T_conditional_passenger_comparisons"]) != len(
        published.get("T_conditional_passenger_comparisons",[])):
        raise ValueError("pinned V14 passenger denominator changed for window")
    expected={(p["ship_id"],p["initiator_ship_id"],p["target_ship_id"],
               p["T_observation_status"]) for p in
              published["T_conditional_passenger_comparisons"]}
    actual={(p["ship_id"],p["initiator_ship_id"],p["target_ship_id"],
             p["T_observation_status"]) for p in
             fresh["T_conditional_passenger_comparisons"]}
    if expected!=actual:
        raise ValueError("V14 independently replayed passenger outcomes drift")
    expected_controls={(p["ship_id"],p["status"],
                        p["T_normal_control_baseline_match"])
                       for p in published["T_nonexposed_normal_control_comparisons"]}
    actual_controls={(p["ship_id"],p["status"],
                      p["T_normal_control_baseline_match"])
                     for p in fresh["T_nonexposed_normal_control_comparisons"]}
    if expected_controls!=actual_controls:
        raise ValueError("V14 independently replayed negative controls drift")


def build_report(conn:Any,v6:Mapping[str,Any],v9report:Mapping[str,Any],
                 v13report:Mapping[str,Any],v14report:Mapping[str,Any]):
    excluded=v14.verify_source(v6,v9report,v13report)
    windows,original=verify_v14(v14report,excluded)
    pre={}
    pre_errors=[]
    for i,(game,turn) in enumerate(windows,1):
        print(f"[c5-v15] PRE [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        try:pre[(game,turn)]=pre_window(conn,game,turn)
        except (ValueError,TypeError,KeyError) as exc:
            pre_errors.append({"game_id":game,"turn":turn,
                               "reason":f"{type(exc).__name__}:{exc}"})
            pre[(game,turn)]=None
    if pre_errors:raise ValueError("V14 exact Tminus1 pre-context not reproducible: "+repr(pre_errors))
    # HARD BARRIER: no owner-current T observed for ANY window before now.
    outcomes=[]
    all_actors=[]
    all_controls=[]
    for i,(game,turn) in enumerate(windows,1):
        print(f"[c5-v15] POST [{i}/{len(windows)}] G{game} T{turn}",flush=True)
        frozen=pre[game,turn]
        actual=v9.after_owner_current(conn,game=game,turn=turn)
        revalidate_v14_comparison(original[game,turn],
             frozen["conditional_cases"],actual,game,turn)
        actors=[actor_edge_after(e,actual,game,turn) for e in
                frozen["features"]["Tminus1_Firecloud_source_target_edges"]]
        controls=[
            negative_comparison(c,
                frozen["negative_control_Tminus1_features"][c["ship_id"]],
                actual,actors,game,turn)
            for c in frozen["features"]["Tminus1_negative_normal_controls"]]
        outcomes.append({
            "game_id":game,"turn":turn,
            "Tminus1_actor_edges":len(actors),
            "Tminus1_preselected_passengers":sum(
                a["Tminus1_preselected_passenger_count"] for a in actors),
            "Tminus1_negative_controls":len(controls),
            "Tminus1_frozen_before_T":True,
        })
        all_actors.extend(actors)
        all_controls.extend(controls)
    if len(all_actors)!=95 or len(all_controls)!=540:
        raise ValueError("V14 95-edge/540-control study denominator changed")
    counter=Counter(a["T_actor_observation_status"] for a in all_actors)
    fuel=Counter(
        "NET_50" if a["T_actor_net_delta_exactly_50"] is True else
        "NET_OTHER" if a["T_actor_net_delta_exactly_50"] is False else
        "NET_UNAVAILABLE" for a in all_actors)
    controls=Counter(c["status"] for c in all_controls)
    if controls!=Counter({
        "MATCH":526,"MISMATCH":8,
        "ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE":1,
        "ABSTAIN_T_HULL_IDENTITY_DRIFT":1,
        "ABSTAIN_T_OWNER_DRIFT":4,
    }):
        raise ValueError("V14 negative control observational denominator drift")
    bygame=defaultdict(Counter)
    for row in all_actors:
        bygame[str(row["game_id"])][row["T_actor_observation_status"]]+=1
        if row["Tminus1_preselected_passenger_count"]:
            bygame[str(row["game_id"])]["passenger_bearing_edges"]+=1
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v14_git_blob_sha1":V14_BLOB,
        "source_v6_git_blob_sha1":v14.V6_BLOB,
        "source_v9_git_blob_sha1":v14.V9_BLOB,
        "source_v13_git_blob_sha1":v14.V13_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_V14_metadata_windows":60,"frozen_V14_games":20,
            "V14_conditional_passenger_comparisons_rechecked":55,
            "Tminus1_actor_edges_rechecked":len(all_actors),
            "Tminus1_passenger_bearing_actor_edges":sum(
                bool(a["Tminus1_preselected_passenger_count"]) for a in all_actors),
            "Tminus1_all_actor_target_after_T_outcomes":dict(sorted(counter.items())),
            "T_actor_net_fuel_delta_categories":dict(sorted(fuel.items())),
            "Tminus1_negative_controls_rechecked":len(all_controls),
            "T_negative_control_statuses":dict(sorted(controls.items())),
            "T_negative_control_mismatch_count":sum(
                c["status"]=="MISMATCH" for c in all_controls),
            "source_context_errors":0,
            "Tminus1_frozen_before_all_T_observations":True,
            "new_Host_movement_or_combat_predictions":0,
            "Chunnel_activation_proven":False,
            "Nplus1_VCR_used":False,
        },
        "per_game_actor_observations":{
            g:dict(sorted(cnt.items())) for g,cnt in sorted(bygame.items())},
        "window_denominators":outcomes,
        "actor_target_T_observations":all_actors,
        "negative_control_T_outcome_mismatches":[
            c for c in all_controls if c["status"]=="MISMATCH"],
        "negative_control_T_abstentions":[
            c for c in all_controls if c["status"].startswith("ABSTAIN")],
        "boundary":(
            "Source cohort is the SAME pinned V14 historical public100 set, "
            "not new independent observations. Every actor edge and normal "
            "control freezes from Tminus1 before ANY T archive read. "
            "Full V14 independently replayed control and passenger results "
            "must agree, including eight ordinary control mismatches. "
            "Observed actor/target at destination and 50KT net fuel changes "
            "are observational posthost signatures, NOT proof of activation. "
            "Fuel net differences can reflect transfers/other phases. "
            "Some initiators can be displaced by another Chunnel in the "
            "same turn, so their end location is not necessarily their "
            "own first target. Official duplicate Chunnel-target IDs "
            "choose lowest eligible full ID; prior V13 ambiguity-abstain "
            "is conservative but incomplete and is not modified here. "
            "No canonical executor promotion, mine-hit RNG attribution, "
            "combat pair predictions or Nplus1 VCR comparisons."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    for name in ("frozen-v6","frozen-v9","frozen-v13","frozen-v14",
                 "corpus-db-root","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    try:
        v6=v13.pinned_json(a.frozen_v6,v14.V6_BLOB)
        v9report=v13.pinned_json(a.frozen_v9,v14.V9_BLOB)
        v13report=v13.pinned_json(a.frozen_v13,v14.V13_BLOB)
        v14report=pinned_v14(a.frozen_v14)
        excluded=v14.verify_source(v6,v9report,v13report)
        verify_v14(v14report,excluded)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 database missing")
        print("[c5-v15] verifying immutable SHA256",flush=True)
        t=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("immutable public100 SHA256 mismatch")
        print(f"[c5-v15] SHA verified in {time.monotonic()-t:.1f}s; read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(conn,v6,v9report,v13report,v14report)
        finally:conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temp=a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(a.output)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== V15 V14 FROZEN FIRECLOUD ACTOR/NEGATIVE CONTROLS =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
