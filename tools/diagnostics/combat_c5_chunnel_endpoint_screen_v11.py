"""V11 post-hoc Chunnel endpoint screen over the immutable V10 thirteen misses.

T-1 candidate actor/target edges are screened BEFORE T archive is loaded.
Official *necessary* conventional Chunnel constraints are checked (numerical
initiator FC, same-owner fuelled warp-0 target, >=100 ly separation).
The initiator/target hull's actual ability, host order, tow interruption,
custom rules and final outcome remain unproved. No inferred Host mechanism
or newly predicted ship endpoint may be promoted from this screen.
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
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn,TOW_MISSION_ID
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-chunnel-endpoint-screen.v11"
STATUS="V10_TMINUS1_CHUNNEL_ACTOR_SCREEN_OBSERVATIONAL_NOT_CAUSAL"
V10_BLOB="9f2fc93e189b264ebdd1d78b0cd0c39517bb2386"
V10_SCHEMA="planets-lab.combat-c5-posthost-residual-coupling.v10"
V10_STATUS="V9_RESIDUALS_RECONCILED_AS_OBSERVATIONAL_PATTERNS_NOT_CAUSAL_MECHANICS"
GENERATION=v9.GENERATION
SHA256=v9.SHA256


def number(v:Any)->int|None:
    return v if type(v) is int else None


def coordinate(v:Any)->tuple[int,int]|None:
    if not isinstance(v,(list,tuple)) or len(v)!=2:
        return None
    return tuple(v) if all(type(x) is int for x in v) else None


def fuel(v:Any)->int|None:
    n=number(v)
    return n if n is not None and n>=0 else None


def numeric_target(code:Any)->int|None:
    """Three numeric friendly-code digits; do not print arbitrary codes."""
    if not isinstance(code,str) or len(code)!=3 or not code.isascii() or not code.isdigit():
        return None
    return int(code)


def read_frozen(path:Path):
    raw=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if digest!=V10_BLOB:raise ValueError("V10 source Git blob SHA1 changed")
    doc=json.loads(raw)
    if not isinstance(doc,dict):raise ValueError("V10 source malformed")
    return doc


def frozen_cases(report:Mapping[str,Any]):
    if (report.get("schema")!=V10_SCHEMA or report.get("status")!=V10_STATUS
            or report.get("source_db_sha256")!=SHA256
            or report.get("source_v9_git_blob_sha1")!=
                "4e7d707123586311456cc14e78ff774a851caa48"):
        raise ValueError("V10 provenance/schema changed")
    summary=report.get("summary")
    checks={
        "V9_selected_games":8,"V9_selected_windows":16,
        "V9_source_window_context_abstentions":2,
        "V9_endpoint_mismatches":13,"mine_risk_conditional_mismatches":9,
        "normal_model_mismatches":4,"residual_game_turn_windows":6,
        "residual_distinct_games":4,
        "Tminus1_context_errors":0,"Tminus1_tow_order_witness_appearances":0,
        "posthoc_same_endpoint_clusters":2,"posthoc_clustered_ship_count":7,
        "standalone_residual_ship_count":6,
        "new_Host_combat_or_movement_predictions":0,
        "mine_hits_attributed":0,"TOW_success_attributed":0,
        "Nplus1_VCR_used":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in checks.items()):
        raise ValueError("frozen V10 control denominators changed")
    cases=report.get("case_evaluations")
    if not isinstance(cases,list) or len(cases)!=13:
        raise ValueError("V10 13-case source unavailable")
    seen=set()
    for case in cases:
        if not isinstance(case,Mapping):
            raise ValueError("malformed V10 residual")
        key=tuple(number(case.get(k)) for k in ("game_id","turn","ship_id"))
        owner,hull=number(case.get("owner_id")),number(case.get("hull_id"))
        pre,after=case.get("Tminus1"),case.get("T_after_Host")
        if (None in key or min(key)<=0 or key in seen
                or owner is None or owner<=0 or hull is None or hull<=0
                or not isinstance(pre,Mapping) or not isinstance(after,Mapping)
                or pre.get("source_status")!="TMINUS1_OWNER_CURRENT_RECONSTRUCTED"
                or after.get("source_post_T_status")!="OWNER_CURRENT_T_ENDPOINT_REVERIFIED"
                or coordinate(pre.get("Tminus1_start")) is None
                or coordinate(after.get("T_posthost_position")) is None
                or coordinate(case.get("frozen_model_endpoint")) is None
                or coordinate(case.get("frozen_T_owner_current_endpoint")) !=
                   coordinate(after.get("T_posthost_position"))
                or pre.get("Tminus1_tow_orders_targeting_ship")!=[]
                or case.get("mechanic_attribution")!=
                   "ABSTAIN_INDEPENDENT_TERMINAL_OR_PHASE_EVIDENCE_MISSING"
                or case.get("Nplus1_VCR_used") is not False):
            raise ValueError("V10 case identity or observational boundary changed")
        seen.add(key)
    groups=report.get("posthoc_correlated_endpoint_groups")
    if not isinstance(groups,list) or sorted(g.get("size") for g in groups)!=[3,4]:
        raise ValueError("V10 correlated groups changed")
    return tuple(sorted(cases,key=lambda c:(c["game_id"],c["turn"],c["ship_id"])))


def hull_name_inventory(raws):
    """Exact T-1 static hull name; names are a hint, NOT verified capability."""
    names={}
    for payload in raws:
        collection=payload.get("hulls")
        if not isinstance(collection,list) or not collection:
            raise ValueError("Tminus1 catalog hulls unavailable")
        for hull in collection:
            if not isinstance(hull,Mapping):raise ValueError("malformed archived hull catalog")
            hid=number(hull.get("id"))
            name=hull.get("name")
            if hid is None or hid<=0 or not isinstance(name,str):
                raise ValueError("invalid hull name provenance")
            if hid in names and names[hid]!=name:
                raise ValueError("conflicting Tminus1 hull naming across perspectives")
            names[hid]=name
    return names


def screen_tminus1_edges(ships:Mapping[int,tuple[int,Mapping[str,Any]]], names:Mapping[int,str]):
    """No V10 posthost endpoint or T archive is accepted by this function."""
    by_fc=defaultdict(list)
    sources=defaultdict(list)
    target_tow_orders=set()
    for sid,(owner,raw) in ships.items():
        if number(sid) is None or sid<=0 or number(owner) is None or owner<=0 or not isinstance(raw,Mapping):
            raise ValueError("bad Tminus1 owner-current roster")
        loc=coordinate((raw.get("x"),raw.get("y")))
        if loc is not None:
            sources[loc].append(sid)
        if number(raw.get("mission"))==TOW_MISSION_ID:
            tow_target=number(raw.get("mission1target"))
            if tow_target is not None and tow_target>0:target_tow_orders.add(tow_target)
        # The conventional FC is an ID's last 3 digits.
        by_fc[(owner,sid%1000)].append(sid)
    edges=[]
    rejections=Counter()
    for sid,(owner,raw) in sorted(ships.items()):
        code=numeric_target(raw.get("friendlycode",raw.get("friendly_code")))
        if code is None:
            rejections["INITIATOR_NO_NUMERIC_FC"]+=1;continue
        start=coordinate((raw.get("x"),raw.get("y")))
        fl=fuel(raw.get("neutronium"))
        if start is None or fl is None or fl<50:
            rejections["INITIATOR_START_OR_FUEL_GATE"]+=1;continue
        target_ids=by_fc.get((owner,code),[])
        if not target_ids:
            rejections["NO_SAME_OWNER_FC_TARGET"]+=1;continue
        for target_id in sorted(target_ids):
            if target_id==sid:continue
            t_owner,t_raw=ships[target_id]
            destination=coordinate((t_raw.get("x"),t_raw.get("y")))
            t_fuel=fuel(t_raw.get("neutronium"))
            if (destination is None or number(t_raw.get("warp"))!=0
                    or t_fuel is None or t_fuel<1):
                rejections["TARGET_WARP0_FUEL_POSITION_GATE"]+=1;continue
            distance=hypot(destination[0]-start[0],destination[1]-start[1])
            if distance<100:
                rejections["CHUNNEL_DISTANCE_BELOW_100_LY"]+=1;continue
            initiator_hull=number(raw.get("hullid",raw.get("hull_id")))
            target_hull=number(t_raw.get("hullid",t_raw.get("hull_id")))
            source_name=names.get(initiator_hull)
            target_name=names.get(target_hull)
            if source_name is None or target_name is None:
                rejections["HULL_ID_OR_NAME_UNAVAILABLE"]+=1;continue
            edges.append({
                "initiator_ship_id":sid,"initiator_owner_id":owner,
                "initiator_hull_id":initiator_hull,
                "initiator_hull_name":source_name,
                "initiator_name_mentions_firecloud":"firecloud" in source_name.casefold(),
                "initiator_start":list(start),
                "initiator_Tminus1_fuel":fl,
                "target_ship_id":target_id,"target_hull_id":target_hull,
                "target_hull_name":target_name,
                "target_name_mentions_firecloud":"firecloud" in target_name.casefold(),
                "target_Tminus1_position":list(destination),
                "target_Tminus1_warp":0,
                "target_Tminus1_fuel":t_fuel,
                "distance_ly":round(distance,4),
                "tow_order_on_initiator_or_target":sid in target_tow_orders or target_id in target_tow_orders,
                "possible_colocated_ship_ids":sorted(sources[start]),
                "numeric_FC_same_owner_fuel_distance_gates_only":True,
                "initiator_and_target_ability_independently_verified":False,
                "chunnel_execution_proven":False,
            })
    return tuple(edges),dict(sorted(rejections.items()))


def pre_window(conn:Any,game:int,turn:int):
    snapshots,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
    ships=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
    names=hull_name_inventory(raws)
    edges,rejections=screen_tminus1_edges(ships,names)
    return ships,edges,rejections


def observed_screen(case:Mapping[str,Any],ships:Mapping[int,Any],edges,observed_T):
    """Post-hoc destination comparison AFTER pre-window edge freeze."""
    sid=case["ship_id"]
    owner=case["owner_id"]
    start=coordinate(case["Tminus1"]["Tminus1_start"])
    after=coordinate(case["T_after_Host"]["T_posthost_position"])
    # Independently reread and validate immutable V10 T observation.
    owner_current=observed_T.get(sid)
    if owner_current is None or owner_current[0]!=owner or not isinstance(owner_current[1],Mapping):
        raise ValueError("V10 post-T owner-current perspective unavailable")
    actual=coordinate((owner_current[1].get("x"),owner_current[1].get("y")))
    if actual!=after:
        raise ValueError("V10 posthost T endpoint disagrees with archive")
    original=ships.get(sid)
    if original is None or original[0]!=owner or not isinstance(original[1],Mapping):
        raise ValueError("V10 Tminus1 owner-current ship missing")
    original_pos=coordinate((original[1].get("x"),original[1].get("y")))
    if original_pos!=start:
        raise ValueError("V10 Tminus1 start disagrees with archive")
    at_source=[e for e in edges if coordinate(e["initiator_start"])==start]
    at_owner_source=[e for e in at_source if e["initiator_owner_id"]==owner]
    endpoint_match=[e for e in at_owner_source
                    if coordinate(e["target_Tminus1_position"])==after]
    return {
        "game_id":case["game_id"],"turn":case["turn"],"ship_id":sid,
        "Tminus1_owner_id":owner,"cohort":case["cohort"],
        "Tminus1_start":list(start),
        "frozen_normal_model_endpoint":case["frozen_model_endpoint"],
        "published_posthost_T_endpoint":list(after),
        "source_preobserved_warp":case["Tminus1"]["Tminus1_warp"],
        "source_preobserved_fuel":case["Tminus1"]["Tminus1_fuel"],
        "source_preobserved_mission":case["Tminus1"]["Tminus1_mission"],
        "Tminus1_candidate_edges_at_source_all_owners":len(at_source),
        "Tminus1_candidate_edges_at_source_same_owner":len(at_owner_source),
        "Tminus1_candidate_edges_at_source_matching_T_endpoint":len(endpoint_match),
        "posthoc_endpoint_matching_edges":endpoint_match,
        "posthoc_screen_status":(
            "POSTHOC_T_ENDPOINT_MATCHES_TMINUS1_CONVENTIONAL_CHUNNEL_GATE"
            if endpoint_match else
            "NO_TMINUS1_SAME_OWNER_CONVENTIONAL_CHUNNEL_ENDPOINT_MATCH"),
        "canonical_chunnel_verified":False,
        "transport_or_mine_hit_attributed":False,
        "new_host_prediction":False,
        "Nplus1_VCR_used":False,
    }


def build_report(conn:Any,report:Mapping[str,Any]):
    cases=frozen_cases(report)
    groups=defaultdict(list)
    for row in cases:groups[(row["game_id"],row["turn"])].append(row)
    pre={}
    # First finish all six T-1 graphs; only then inspect any T archive.
    for i,(window,rows) in enumerate(sorted(groups.items()),1):
        game,turn=window
        print(f"[c5-chunnel] PRE [{i}/{len(groups)}] G{game} T{turn}",flush=True)
        pre[window]=pre_window(conn,game,turn)
    results=[]
    game_edges=[]
    source_control_counts=Counter()
    rejection_totals=Counter()
    for i,(window,rows) in enumerate(sorted(groups.items()),1):
        game,turn=window
        ships,edges,rejections=pre[window]
        rejection_totals.update(rejections)
        actual=v9.after_owner_current(conn,game=game,turn=turn)
        print(f"[c5-chunnel] POST [{i}/{len(groups)}] G{game} T{turn}",flush=True)
        for case in rows:
            results.append(observed_screen(case,ships,edges,actual))
        used_sources={tuple(x["Tminus1"]["Tminus1_start"]) for x in rows}
        nonresidual=[e for e in edges if coordinate(e["initiator_start"]) not in used_sources]
        source_control_counts["Tminus1_edges_outside_residual_start"]+=len(nonresidual)
        source_control_counts["Tminus1_edges_at_residual_start"]+=len(edges)-len(nonresidual)
        game_edges.append({
            "game_id":game,"turn":turn,
            "Tminus1_owner_current_ships":len(ships),
            "Tminus1_conventional_candidate_edges":len(edges),
            "Tminus1_edges_at_residual_source":len(edges)-len(nonresidual),
            "Tminus1_edges_elsewhere":len(nonresidual),
            "Tminus1_screen_rejections":rejections,
            "nonresidual_source_control_examples":list(nonresidual[:8]),
        })
    if len(results)!=13 or len(game_edges)!=6:
        raise ValueError("V10 frozen residual coverage changed")
    results.sort(key=lambda r:(r["game_id"],r["turn"],r["ship_id"]))
    status=Counter(x["posthoc_screen_status"] for x in results)
    clusters=report["posthoc_correlated_endpoint_groups"]
    cluster_views=[]
    for cluster in clusters:
        ids=set(cluster["ship_ids"])
        filtered=[r for r in results if
                  r["game_id"]==cluster["game_id"] and
                  r["turn"]==cluster["turn"] and
                  r["ship_id"] in ids]
        if len(filtered)!=cluster["size"]:
            raise ValueError("V10 frozen correlated cluster membership changed")
        cluster_views.append({
            "game_id":cluster["game_id"],"turn":cluster["turn"],
            "size":cluster["size"],"ship_ids":sorted(ids),
            "posthoc_endpoint_matching_candidates_for_all":all(
                r["Tminus1_candidate_edges_at_source_matching_T_endpoint"]>0
                for r in filtered),
            "posthoc_source_gate_counts":[
                r["Tminus1_candidate_edges_at_source_same_owner"] for r in filtered],
            "mechanism_independently_proven":False,
        })
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v10_git_blob_sha1":V10_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_v9_mismatches":13,
            "frozen_v10_distinct_windows":6,
            "frozen_v10_distinct_games":4,
            "frozen_v10_correlated_clusters":2,
            "frozen_v10_correlated_ships":7,
            "Tminus1_pre_context_failures":0,
            "posthoc_screen_status_counts":dict(sorted(status.items())),
            "Tminus1_screen_rejection_counts":dict(sorted(rejection_totals.items())),
            "Tminus1_graph_edge_controls":dict(sorted(source_control_counts.items())),
            "new_combat_or_movement_predictions":0,
            "chunnel_initiator_target_abilities_verified":False,
            "chunnel_execution_proven":False,
            "mine_hits_inferred":0,"Nplus1_VCR_read":False,
        },
        "cluster_screen":cluster_views,
        "window_evaluations":game_edges,
        "residual_case_evaluations":results,
        "boundary":(
            "The source residual set is post-hoc V9 and all 13 mismatches "
            "remain unchanged. T-1 conventional Chunnel screen checks only "
            "numeric friendly-code targeting, same-owner initiator fuel >=50, "
            "target warp0/fuel>0 and minimum 100-ly distance; archive static "
            "hull name is descriptive only, NOT proof of Chunnel ability. "
            "Tow on endpoint may prevent Chunnel. Actor/target candidate "
            "graph is frozen before any T archive read. Matching an edge "
            "to a post-Host observed destination is POSTHOC; cannot prove "
            "Chunnel execution or current precombat location. No RNG, "
            "VCR N+1, combat selection, canonical movement rule or production "
            "executor updated."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-v10",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        report=read_frozen(args.frozen_v10)
        frozen_cases(report)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 DB missing")
        print("[c5-chunnel] validating pinned immutable public100 SHA256",flush=True)
        t=time.monotonic()
        with db.open("rb") as fd:sha=hashlib.file_digest(fd,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("public100 DB hash drift")
        print(f"[c5-chunnel] SHA verified in {time.monotonic()-t:.1f}s; read-only",flush=True)
        connection,_=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:out=build_report(connection,report)
        finally:connection.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.output.with_suffix(args.output.suffix+".tmp")
        temporary.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temporary.replace(args.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 POSTHOST CHUNNEL SOURCE/TARGET SCREEN V11 =====")
    print("status:",out["status"])
    print("summary:",out["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
