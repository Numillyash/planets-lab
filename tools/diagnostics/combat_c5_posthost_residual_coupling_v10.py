"""V10 observational residual audit for the 13 fixed V9 endpoint misses.

Do not reselect outcomes: input is Git-blob-pinned V9 *mismatch examples*
(9 mine-risk + 4 ordinary). T-1 owner-current orders and colocation are read
separately from T owner-current post-Host observations. A tow order or a shared
endpoint is not an independent demonstration of successful Tow, Chunnel,
mine hit, capture, or another Host mechanism.

NO new predictions. This is intentionally a post-hoc diagnostic and cannot
be used to evaluate out-of-sample performance or promote a combat executor.
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
for x in (ROOT/"src",Path(__file__).resolve().parent):
    if str(x) not in sys.path:sys.path.insert(0,str(x))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn, TOW_MISSION_ID
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-posthost-residual-coupling.v10"
STATUS="V9_RESIDUALS_RECONCILED_AS_OBSERVATIONAL_PATTERNS_NOT_CAUSAL_MECHANICS"
V9_BLOB="4e7d707123586311456cc14e78ff774a851caa48"
V9_SCHEMA=v9.SCHEMA
V9_STATUS=v9.STATUS
GENERATION=v9.GENERATION
SHA256=v9.SHA256
COHORTS=(v9.MINE,v9.NORMAL)


def positive(v:Any)->int|None:
    return v if type(v) is int and v>0 else None


def xy(v:Any)->tuple[int,int]|None:
    if (not isinstance(v,(list,tuple)) or len(v)!=2
            or any(type(z) is not int for z in v)):
        return None
    return (v[0],v[1])


def read_frozen(path:Path)->dict[str,Any]:
    raw=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if sha!=V9_BLOB:raise ValueError("V9 immutable Git blob mismatch")
    report=json.loads(raw)
    if not isinstance(report,dict):raise ValueError("V9 report is not an object")
    return report


def freeze_v9_residuals(v9report:Mapping[str,Any]):
    """Lock exact cohort/multiplicity and posthost error accounting."""
    if (v9report.get("schema")!=V9_SCHEMA or
        v9report.get("status")!=V9_STATUS or
        v9report.get("source_db_sha256")!=SHA256):
        raise ValueError("V9 provenance/schema drift")
    summary=v9report.get("summary")
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in {
        "selected_games":8,"selected_windows":16,"selected_games_overlap_with_C5":0,
        "pre_forecast_rows":3191,"posthost_compared_rows":3191,
        "window_context_abstentions":2,
        "new_Host_combat_predictions":0,"Nplus1_VCR_read":False,
    }.items()):
        raise ValueError("V9 source denominator drift")
    counts=summary.get("cohort_posthost_status_counts")
    if not isinstance(counts,Mapping):raise ValueError("missing V9 status denominators")
    target_mismatches={v9.MINE:9,v9.NORMAL:4}
    if any(not isinstance(counts.get(c),Mapping) or
           counts[c].get("POSTHOST_ENDPOINT_MISMATCH")!=n
           for c,n in target_mismatches.items()):
        raise ValueError("V9 mismatch denominator drift")
    cohort_rows=v9report.get("mismatch_examples")
    selection=v9report.get("frozen_metadata_selection")
    if not isinstance(cohort_rows,Mapping) or not isinstance(selection,Mapping):
        raise ValueError("V9 frozen sample missing")
    if selection.get("no_VCR_selection") is not True:
        raise ValueError("V9 not metadata-only selected")
    windows=selection.get("selected_game_turns")
    if not isinstance(windows,list) or len(windows)!=16:
        raise ValueError("V9 original metadata window selection missing")
    windowset=set()
    for row in windows:
        if not isinstance(row,Mapping):raise ValueError("bad V9 selected window")
        g,t=positive(row.get("game_id")),positive(row.get("turn"))
        if None in (g,t) or (g,t) in windowset:
            raise ValueError("invalid/duplicate V9 metadata window")
        windowset.add((g,t))
    cases=[]
    identities=set()
    for cohort in COHORTS:
        rows=cohort_rows.get(cohort)
        if not isinstance(rows,list) or len(rows)!=target_mismatches[cohort]:
            raise ValueError("V9 mismatch example list truncated")
        for row in rows:
            if not isinstance(row,Mapping):raise ValueError("V9 residual row invalid")
            g,t,sid=(positive(row.get(x)) for x in ("game_id","after_turn","ship_id"))
            owner=positive(row.get("Tminus1_owner_id"))
            hull=positive(row.get("Tminus1_hull_id"))
            forecast=xy(row.get("conditional_or_model_endpoint"))
            observed=xy(row.get("T_owner_current_position"))
            identity=(g,t,sid)
            if (None in (g,t,sid,owner,hull,forecast,observed)
                    or (g,t) not in windowset
                    or identity in identities
                    or forecast==observed
                    or row.get("comparison_status")!="POSTHOST_ENDPOINT_MISMATCH"
                    or row.get("T_owner_current_owner_id")!=owner
                    or row.get("cohort")!=cohort
                    or row.get("Nplus1_vcr_used") is not False
                    or row.get("precombat_site_membership_proven") is not False
                    or row.get("mine_hit_or_nonhit_proven") is not False
                    or row.get("conditional_no_mine_only")!=(cohort==v9.MINE)
                    or not isinstance(row.get("Tminus1_source"),str)):
                raise ValueError("V9 residual example identity or proof boundary drift")
            identities.add(identity)
            cases.append({
                "game_id":g,"turn":t,"ship_id":sid,"owner_id":owner,
                "hull_id":hull,"cohort":cohort,"Tminus1_source":row["Tminus1_source"],
                "frozen_model_endpoint":list(forecast),
                "frozen_T_owner_current_endpoint":list(observed),
            })
    if len(cases)!=13 or len(windowset)!=16:
        raise ValueError("V9 source mismatch count incorrect")
    return tuple(sorted(cases,key=lambda c:(c["game_id"],c["turn"],c["ship_id"]))),windowset


def tminus1_orders(case:Mapping[str,Any],ship_rows:Mapping[int,Any]):
    """Read a SINGLE T-1 owner-current roster and no T/future comparator."""
    sid=case["ship_id"]
    source=ship_rows.get(sid)
    if source is None:
        return {"source_status":"ABSTAIN_TMINUS1_OWNER_CURRENT_SHIP_MISSING"}
    owner,raw=source
    hull=positive(raw.get("hullid",raw.get("hull_id")))
    if owner!=case["owner_id"] or hull!=case["hull_id"]:
        raise ValueError("V9 residual ship owner/hull changed in exact Tminus1 archive")
    start=xy((raw.get("x"),raw.get("y")))
    target=xy((raw.get("targetx"),raw.get("targety")))
    if start is None or target is None:
        return {"source_status":"ABSTAIN_TMINUS1_POSITION_OR_WAYPOINT_MISSING"}
    towers=[]
    start_copresent=0
    same_waypoint=0
    for other_id,(other_owner,other) in sorted(ship_rows.items()):
        if other_id==sid:continue
        other_xy=xy((other.get("x"),other.get("y")))
        if other_xy==start:
            start_copresent+=1
            if xy((other.get("targetx"),other.get("targety")))==target:
                same_waypoint+=1
        if (v9.integer(other.get("mission"))==TOW_MISSION_ID and
                v9.integer(other.get("mission1target"))==sid):
            towers.append({
                "tower_ship_id":other_id,"tower_owner_id":other_owner,
                "tower_colocated_in_Tminus1":other_xy==start,
                "tower_Tminus1_position":list(other_xy) if other_xy else None,
                "tow_order_seen_not_success_proven":True,
            })
    return {
        "source_status":"TMINUS1_OWNER_CURRENT_RECONSTRUCTED",
        "Tminus1_start":list(start),"Tminus1_waypoint":list(target),
        "Tminus1_mission":v9.integer(raw.get("mission")),
        "Tminus1_mission_target_id":v9.integer(raw.get("mission1target")),
        "Tminus1_warp":v9.integer(raw.get("warp")),
        "Tminus1_fuel":v9.integer(raw.get("neutronium")),
        "Tminus1_damage":v9.integer(raw.get("damage")),
        "Tminus1_same_start_other_ships":start_copresent,
        "Tminus1_same_start_same_waypoint_other_ships":same_waypoint,
        "Tminus1_tow_orders_targeting_ship":towers,
        "requested_Tminus1_route_is_factual_intent_only":True,
    }


def t_observational_check(case:Mapping[str,Any],pre:Mapping[str,Any],actual:Mapping[int,Any]):
    """Published T archive outcome must agree with separately retrieved T."""
    sid=case["ship_id"]
    entry=actual.get(sid)
    if entry is None:
        raise ValueError("published V9 T owner-current ship disappeared")
    owner,raw=entry
    if not isinstance(raw,Mapping) or owner!=case["owner_id"]:
        raise ValueError("V9 T owner identity no longer independently confirmed")
    pos=xy((raw.get("x"),raw.get("y")))
    if pos!=tuple(case["frozen_T_owner_current_endpoint"]):
        raise ValueError("V9 observed T endpoint mismatch with immutable archive")
    if positive(raw.get("hullid",raw.get("hull_id")))!=case["hull_id"]:
        raise ValueError("V9 T hull identity changed")
    before=pre.get("Tminus1_start")
    expected=case["frozen_model_endpoint"]
    return {
        "source_post_T_status":"OWNER_CURRENT_T_ENDPOINT_REVERIFIED",
        "T_posthost_position":list(pos),
        "T_posthost_fuel":v9.integer(raw.get("neutronium")),
        "T_posthost_damage":v9.integer(raw.get("damage")),
        "Tminus1_start_to_T_displacement_ly":round(hypot(pos[0]-before[0],pos[1]-before[1]),4)
             if before is not None else None,
        "frozen_model_to_T_residual_ly":round(
            hypot(pos[0]-expected[0],pos[1]-expected[1]),4),
        "T_damage_delta":(v9.integer(raw.get("damage"))-pre["Tminus1_damage"]
             if pre.get("Tminus1_damage") is not None and
                 v9.integer(raw.get("damage")) is not None else None),
        "mine_hit_or_tow_success_proven":False,
        "precombat_position_proven":False,
    }


def cross_case_groups(cases):
    """Post hoc clusters only; do not use groups to select forecasts."""
    index=defaultdict(list)
    for case in cases:
        key=(case["game_id"],case["turn"],case["cohort"],
             tuple(case["frozen_model_endpoint"]),
             tuple(case["frozen_T_owner_current_endpoint"]))
        index[key].append(case["ship_id"])
    groups=[]
    for key,sids in sorted(index.items()):
        if len(sids)<2:continue
        g,t,cohort,predicted,observed=key
        groups.append({
            "game_id":g,"turn":t,"cohort":cohort,
            "frozen_model_endpoint":list(predicted),
            "frozen_T_owner_current_endpoint":list(observed),
            "ship_ids":sorted(sids),"size":len(sids),
            "same_pair_of_endpoints_is_shared_effect_not_mechanic_proof":True,
        })
    return groups


def build_report(conn:Any,source:Mapping[str,Any]):
    cases,windows=freeze_v9_residuals(source)
    by_window=defaultdict(list)
    for case in cases:by_window[case["game_id"],case["turn"]].append(case)
    # PHASE ONE: freeze all available T-1 orders BEFORE ANY T archive read.
    pre_rows={}
    pre_errors=[]
    for i,((game,turn),items) in enumerate(sorted(by_window.items()),1):
        print(f"[c5-residual] PRE [{i}/{len(by_window)}] G{game} T{turn} cases={len(items)}",flush=True)
        try:
            snapshots,_=v9.pre_snapshots(conn,game=game,before=turn-1)
            ships=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
            for case in items:pre_rows[game,turn,case["ship_id"]]=tminus1_orders(case,ships)
        except (ValueError,KeyError,TypeError) as exc:
            pre_errors.append({"game_id":game,"turn":turn,"phase":"Tminus1",
                               "issue":f"{type(exc).__name__}:{exc}"})
            for case in items:pre_rows[game,turn,case["ship_id"]]={"source_status":"ABSTAIN_TMINUS1_CONTEXT_UNAVAILABLE"}
    # PHASE TWO: independently compare already-published T outcomes.
    results=[]
    for i,((game,turn),items) in enumerate(sorted(by_window.items()),1):
        print(f"[c5-residual] POST [{i}/{len(by_window)}] G{game} T{turn}",flush=True)
        try:actual=v9.after_owner_current(conn,game=game,turn=turn)
        except (ValueError,KeyError,TypeError) as exc:
            raise ValueError(f"V9 published posthost comparator unavailable for G{game} T{turn}: {exc}") from exc
        for case in items:
            pre=pre_rows[game,turn,case["ship_id"]]
            post=t_observational_check(case,pre,actual)
            results.append({
                **case,"Tminus1":pre,"T_after_Host":post,
                "mechanic_attribution":"ABSTAIN_INDEPENDENT_TERMINAL_OR_PHASE_EVIDENCE_MISSING",
                "Nplus1_VCR_used":False,
            })
    if len(results)!=13:raise ValueError("13-case V9 audit coverage changed")
    clusters=cross_case_groups(cases)
    status_counts=Counter(x["Tminus1"]["source_status"] for x in results)
    all_tows=[(x["game_id"],x["turn"],x["ship_id"],tow) for x in results
              for tow in x["Tminus1"].get("Tminus1_tow_orders_targeting_ship",[])]
    cluster_ships=sum(x["size"] for x in clusters)
    # Never let repeated correlated ships masquerade as independent causes.
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v9_git_blob_sha1":V9_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "V9_selected_games":8,"V9_selected_windows":16,
            "V9_source_window_context_abstentions":2,
            "V9_endpoint_mismatches":13,
            "mine_risk_conditional_mismatches":9,
            "normal_model_mismatches":4,
            "residual_game_turn_windows":len(by_window),
            "residual_distinct_games":len({g for g,_ in by_window}),
            "Tminus1_context_errors":len(pre_errors),
            "Tminus1_source_statuses":dict(sorted(status_counts.items())),
            "Tminus1_tow_order_witness_appearances":len(all_tows),
            "posthoc_same_endpoint_clusters":len(clusters),
            "posthoc_clustered_ship_count":cluster_ships,
            "standalone_residual_ship_count":13-cluster_ships,
            "new_Host_combat_or_movement_predictions":0,
            "mine_hits_attributed":0,"TOW_success_attributed":0,
            "Nplus1_VCR_used":False,
        },
        "posthoc_correlated_endpoint_groups":clusters,
        "case_evaluations":results,
        "Tminus1_errors":pre_errors,
        "boundary":(
            "Thirteen misses selected from V9 after inspecting its T outcomes: "
            "entirely post-hoc diagnostic; clusters of equal end positions are "
            "correlated, not separate confirmations of a Host rule. T-1 ship "
            "orders, tow requests, colocation, fuel and damage are FROZEN "
            "before reading T owner-current state. T is after Host; Tow order "
            "is not Tow success, negative residual is not mine hit, post-turn "
            "damage may be from battle, and game-wide actor state remains "
            "incomplete. Original V9 site-disjoint selection, 8/16 protocol, "
            "all failures and denominator remain unchanged. No VCRs, executor "
            "or mine RNG result used or promoted."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-v9",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    try:
        src=read_frozen(a.frozen_v9)
        freeze_v9_residuals(src)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 database unavailable")
        print("[c5-residual] verifying public100 SHA256 once",flush=True)
        start=time.monotonic()
        with db.open("rb") as fd:digest=hashlib.file_digest(fd,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("immutable public100 checksum changed")
        print(f"[c5-residual] read-only DB checked in {time.monotonic()-start:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(conn,src)
        finally:conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temp=a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(a.output)
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 POSTHOST V9 RESIDUAL COUPLING V10 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
