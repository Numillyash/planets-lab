"""V12: phase-aware Firecloud Chunnel screen for thirteen frozen V9 residuals.

V11 screened sources at T-1 vessel starts and accidentally treated *any*
numeric-FC ship as an initiator. V12 requires STOCK Firecloud hull 56
and uses independent pre-movement normal endpoint of the residual vessel.
This detects the documented "move most, then Chunnel" ordering, but DOES
NOT prove its execution. V11 is pinned, no new cases are selected.

All six T-1 actor/target edge inventories freeze BEFORE any T observation
is consulted. Afterward, existing V11 published T endpoints are only
comparators, along with optional owner-current T actor/target evidence.
Non-Firecloud numerical-FC ships are deliberately NEGATIVE controls.
No N+1 VCR and no production changes.
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
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
import combat_c5_chunnel_endpoint_screen_v11 as v11
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-phase-aware-firecloud-screen.v12"
STATUS="TMINUS1_PREMOVE_FIRECLOUD_ENDPOINT_CONCORDANCE_OBSERVATIONAL_ONLY"
V11_BLOB="98e31ff87b615af1e60d9e120317cbbe8c756d4e"
V11_SCHEMA=v11.SCHEMA
V11_STATUS=v11.STATUS
GENERATION=v11.GENERATION
SHA256=v11.SHA256
FIRECLOUD_HULL=56


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def point(x:Any)->tuple[int,int]|None:
    return v11.coordinate(x)


def read_pinned(path:Path)->dict[str,Any]:
    b=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\x00"+b).hexdigest()
    if sha!=V11_BLOB:raise ValueError("V11 frozen report Git blob changed")
    value=json.loads(b)
    if not isinstance(value,dict):raise ValueError("V11 frozen report root invalid")
    return value


def freeze_cases(v11_report:Mapping[str,Any]):
    """Frozen 13 posthoc V11 case IDs; no discovery from outcomes."""
    if (v11_report.get("schema")!=V11_SCHEMA or
        v11_report.get("status")!=V11_STATUS or
        v11_report.get("source_v10_git_blob_sha1")!=v11.V10_BLOB or
        v11_report.get("source_db_sha256")!=SHA256):
        raise ValueError("V11 source identity/provenance drift")
    summary=v11_report.get("summary")
    expected={
        "frozen_v9_mismatches":13,"frozen_v10_distinct_windows":6,
        "frozen_v10_distinct_games":4,"frozen_v10_correlated_clusters":2,
        "frozen_v10_correlated_ships":7,"Tminus1_pre_context_failures":0,
        "new_combat_or_movement_predictions":0,
        "chunnel_execution_proven":False,"Nplus1_VCR_read":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in expected.items()):
        raise ValueError("V11 source cohort/movement boundary drift")
    cases=v11_report.get("residual_case_evaluations")
    windows=v11_report.get("window_evaluations")
    if not isinstance(cases,list) or len(cases)!=13 or not isinstance(windows,list) or len(windows)!=6:
        raise ValueError("V11 frozen residual/window list incomplete")
    windowset=set()
    for window in windows:
        if not isinstance(window,Mapping):raise ValueError("V11 malformed window")
        g,t=integer(window.get("game_id")),integer(window.get("turn"))
        if g is None or t is None or g<=0 or t<=1 or (g,t) in windowset:
            raise ValueError("V11 duplicate/invalid window")
        windowset.add((g,t))
    identities=set()
    for case in cases:
        if not isinstance(case,Mapping):raise ValueError("V11 malformed residual")
        g,t,sid=[integer(case.get(k)) for k in ("game_id","turn","ship_id")]
        model=point(case.get("frozen_normal_model_endpoint"))
        observed=point(case.get("published_posthost_T_endpoint"))
        start=point(case.get("Tminus1_start"))
        if (None in (g,t,sid,model,observed,start) or
            (g,t) not in windowset or (g,t,sid) in identities or
            integer(case.get("Tminus1_owner_id")) is None or
            model==observed or
            case.get("canonical_chunnel_verified") is not False or
            case.get("transport_or_mine_hit_attributed") is not False or
            case.get("Nplus1_VCR_used") is not False):
            raise ValueError("V11 residual identity/prediction boundary drift")
        identities.add((g,t,sid))
    if len(windowset)!=6 or len(identities)!=13:
        raise ValueError("V11 frozen denominator lost")
    return tuple(sorted(cases,key=lambda c:(c["game_id"],c["turn"],c["ship_id"]))),tuple(sorted(windowset))


def freeze_tminus1_window(conn:Any,game:int,turn:int):
    """Independent from current T: only exact T-1 owner-current roster."""
    ships,edges,rejections=v11.pre_window(conn,game,turn)
    stock=[]
    excluded=Counter()
    for edge in edges:
        if not isinstance(edge,Mapping):raise ValueError("malformed V11 candidate")
        src,tgt=edge.get("initiator_ship_id"),edge.get("target_ship_id")
        if src not in ships or tgt not in ships:raise ValueError("unbacked candidate ship")
        source_owner,source_raw=ships[src]
        target_owner,target_raw=ships[tgt]
        if source_owner!=target_owner or source_owner!=edge.get("initiator_owner_id"):
            raise ValueError("T-1 actor/target owner drift")
        if (integer(edge.get("initiator_hull_id"))!=FIRECLOUD_HULL or
            integer(edge.get("target_hull_id"))!=FIRECLOUD_HULL):
            excluded["NON_FIRECLOUD_NUMERIC_FC_EDGE"]+=1
            continue
        start=point(edge.get("initiator_start"))
        destination=point(edge.get("target_Tminus1_position"))
        if (start is None or destination is None or
            edge.get("numeric_FC_same_owner_fuel_distance_gates_only") is not True or
            integer(target_raw.get("warp"))!=0):
            raise ValueError("T-1 Firecloud edge provenance changed")
        src_warp=integer(source_raw.get("warp"))
        actor_fuel=integer(source_raw.get("neutronium"))
        target_fuel=integer(target_raw.get("neutronium"))
        if (src_warp is None or actor_fuel is None or actor_fuel<50 or
            target_fuel is None or target_fuel<1):
            raise ValueError("Firecloud warp/fuel gate unresolved")
        stock.append({
            "initiator_ship_id":src,"target_ship_id":tgt,
            "owner_id":source_owner,
            "initiator_Tminus1_position":list(start),
            "target_Tminus1_position":list(destination),
            "initiator_Tminus1_warp":src_warp,
            "target_Tminus1_warp":0,
            "initiator_Tminus1_fuel":actor_fuel,
            "target_Tminus1_fuel":target_fuel,
            "Tminus1_tow_order_on_endpoints":edge["tow_order_on_initiator_or_target"],
            "documented_stock_hulls_but_game_custom_capability_unverified":True,
            "Tminus1_conventional_actor_target_gate_passed":True,
        })
    return {
        "game_id":game,"turn":turn,
        "Tminus1_ship_count":len(ships),
        "Tminus1_all_numeric_fc_edges":len(edges),
        "Tminus1_stock_firecloud_edges":tuple(stock),
        "Tminus1_nonstock_numeric_fc_edges":excluded["NON_FIRECLOUD_NUMERIC_FC_EDGE"],
        "Tminus1_raw_v11_gate_rejections":rejections,
    }


def pre_join(
    cases:list[Mapping[str,Any]]|tuple[Mapping[str,Any],...],
    windows:Mapping[tuple[int,int],Mapping[str,Any]],
):
    """Join current-N pre-movement model endpoints ONLY to frozen T-1 graph."""
    rows=[]
    for c in cases:
        g,t,sid=(c[k] for k in ("game_id","turn","ship_id"))
        window=windows.get((g,t))
        if window is None:raise ValueError("missing frozen T-1 actor graph")
        proposed=point(c["frozen_normal_model_endpoint"])
        if proposed is None:raise ValueError("missing T-1 pre-movement model endpoint")
        owner=c["Tminus1_owner_id"]
        all_firecloud=[e for e in window["Tminus1_stock_firecloud_edges"]
                       if point(e["initiator_Tminus1_position"])==proposed]
        same_owner=[e for e in all_firecloud if e["owner_id"]==owner]
        no_tow=[e for e in same_owner
                if e["Tminus1_tow_order_on_endpoints"] is False]
        status=("PREMOVE_MODEL_ENDPOINT_AT_STOCK_FIRECLOUD_SOURCE"
                if no_tow else
                "ABSTAIN_ONLY_TOW_BLOCKED_FIRECLOUD_SOURCE" if same_owner else
                "NO_STOCK_FIRECLOUD_SOURCE_AT_PREMOVE_MODEL_ENDPOINT")
        rows.append({
            "game_id":g,"turn":t,"ship_id":sid,"Tminus1_owner_id":owner,
            "frozen_Tminus1_pre_move_normal_endpoint":list(proposed),
            "frozen_posthost_T_comparator":c["published_posthost_T_endpoint"],
            "frozen_Tminus1_start":c["Tminus1_start"],
            "source_risk_cohort":c["cohort"],
            "Tminus1_stock_firecloud_source_candidates":list(no_tow),
            "Tminus1_all_same_owner_firecloud_sources":len(same_owner),
            "Tminus1_without_T_observation_status":status,
            "T_archive_not_used_to_construct_candidates":True,
        })
    if len(rows)!=13:raise ValueError("frozen 13 V11 residuals missing")
    return rows


def post_compare(row:Mapping[str,Any],ships_T:Mapping[int,Any]):
    """Only now check T observed endpoint and optional actor/target deltas."""
    sid=row["ship_id"]
    entry=ships_T.get(sid)
    expected=point(row["frozen_posthost_T_comparator"])
    if (entry is None or entry[0]!=row["Tminus1_owner_id"] or
        not isinstance(entry[1],Mapping) or
        point((entry[1].get("x"),entry[1].get("y")))!=expected):
        raise ValueError("published V11 posthost ship/position cannot be independently reverified")
    matched=[]
    for candidate in row["Tminus1_stock_firecloud_source_candidates"]:
        actorid,targetid=candidate["initiator_ship_id"],candidate["target_ship_id"]
        actor=ships_T.get(actorid)
        target=ships_T.get(targetid)
        expected_dst=point(candidate["target_Tminus1_position"])
        actor_observed=(point((actor[1].get("x"),actor[1].get("y")))
                        if actor is not None and isinstance(actor[1],Mapping) and
                           actor[0]==candidate["owner_id"] else None)
        target_observed=(point((target[1].get("x"),target[1].get("y")))
                        if target is not None and isinstance(target[1],Mapping) and
                           target[0]==candidate["owner_id"] else None)
        actor_fuel=(integer(actor[1].get("neutronium"))
                    if actor is not None and isinstance(actor[1],Mapping) and
                       actor[0]==candidate["owner_id"] else None)
        delta=(candidate["initiator_Tminus1_fuel"]-actor_fuel
               if actor_fuel is not None else None)
        matched.append({
            **candidate,
            "T_ship_endpoint_agrees_with_Tminus1_target":expected==expected_dst,
            "T_actor_owner_current_endpoint":list(actor_observed) if actor_observed else None,
            "T_target_owner_current_endpoint":list(target_observed) if target_observed else None,
            "T_actor_at_preselected_target":actor_observed==expected_dst if actor_observed else None,
            "T_target_still_at_Tminus1_endpoint":target_observed==expected_dst if target_observed else None,
            "T_actor_fuel_delta_KT":delta,
            "T_actor_fuel_delta_exactly_50":delta==50 if delta is not None else None,
            "chunnel_execution_proven":False,
        })
    destination_matched=any(a["T_ship_endpoint_agrees_with_Tminus1_target"] for a in matched)
    status=("POSTHOC_T_ENDPOINT_CONCORDANT_WITH_PREMOVE_FIRECLOUD_EDGE" if destination_matched
            else "PREMOVE_FIRECLOUD_EDGE_BUT_POSTHOST_T_DESTINATION_DIFFERS" if matched
            else row["Tminus1_without_T_observation_status"])
    return {
        **row,"T_observation_comparison_status":status,
        "T_actor_target_comparisons":matched,
        "documented_Firecloud_rule_still_requires_independent_execution_evidence":True,
        "new_host_position_prediction":False,"Nplus1_VCR_used":False,
    }


def build_report(conn:Any,source:Mapping[str,Any])->dict[str,Any]:
    cases, windows=freeze_cases(source)
    pre={}
    for ix,(game,turn) in enumerate(windows,1):
        print(f"[c5-firecloud] PRE [{ix}/6] G{game} T{turn}",flush=True)
        pre[(game,turn)]=freeze_tminus1_window(conn,game,turn)
    frozen=pre_join(cases,pre)
    output=[]
    for ix,(game,turn) in enumerate(windows,1):
        print(f"[c5-firecloud] POST [{ix}/6] G{game} T{turn}",flush=True)
        t_records=v9.after_owner_current(conn,game=game,turn=turn)
        output.extend(post_compare(row,t_records)
                      for row in frozen if (row["game_id"],row["turn"])==(game,turn))
    if len(output)!=13:raise ValueError("incomplete thirteen case report")
    summaries=Counter(row["T_observation_comparison_status"] for row in output)
    clusters=[]
    for cluster in source.get("cluster_screen",[]):
        member=set(cluster["ship_ids"])
        items=[row for row in output if row["game_id"]==cluster["game_id"] and
               row["turn"]==cluster["turn"] and row["ship_id"] in member]
        if len(items)!=cluster["size"]:raise ValueError("V11 cluster identity changed")
        clusters.append({
            "game_id":cluster["game_id"],"turn":cluster["turn"],
            "ship_ids":sorted(member),"size":cluster["size"],
            "all_phase_aware_firecloud_target_concordant":all(
                row["T_observation_comparison_status"]==
                "POSTHOC_T_ENDPOINT_CONCORDANT_WITH_PREMOVE_FIRECLOUD_EDGE"
                for row in items),
            "mechanism_proven":False,
        })
    controls=Counter()
    for win in pre.values():
        controls["Tminus1_all_numeric_fc_edges"]+=win["Tminus1_all_numeric_fc_edges"]
        controls["Tminus1_stock_firecloud_edges"]+=len(win["Tminus1_stock_firecloud_edges"])
        controls["Tminus1_nonstock_numeric_fc_edges"]+=win["Tminus1_nonstock_numeric_fc_edges"]
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v11_git_blob_sha1":V11_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_V9_endpoint_mismatches":13,
            "frozen_V11_windows":6,"frozen_V11_games":4,
            "frozen_V11_clustered_ships":7,
            "frozen_Tminus1_firecloud_graph_controls":dict(sorted(controls.items())),
            "phase_aware_posthost_status_counts":dict(sorted(summaries.items())),
            "posthoc_firecloud_target_concordant_cases":summaries[
                "POSTHOC_T_ENDPOINT_CONCORDANT_WITH_PREMOVE_FIRECLOUD_EDGE"],
            "new_host_combat_or_movement_predictions":0,
            "Tminus1_graphs_frozen_before_T":True,
            "mine_hits_or_Chunnel_execution_proven":False,
            "Nplus1_VCR_used":False,
        },
        "cluster_screen":clusters,
        "window_Tminus1_controls":[{
            "game_id":win["game_id"],"turn":win["turn"],
            "Tminus1_all_numeric_fc_edges":win["Tminus1_all_numeric_fc_edges"],
            "Tminus1_stock_firecloud_edges":len(win["Tminus1_stock_firecloud_edges"]),
            "Tminus1_nonstock_numeric_fc_edges":win["Tminus1_nonstock_numeric_fc_edges"],
        } for win in pre.values()],
        "case_evaluations":output,
        "boundary":(
            "Frozen thirteen V9 misses, not an unseen holdout. Exact Tminus1 "
            "documented STOCK hull56 Firecloud source/target necessary gate "
            "does not establish custom game capability or Chunnel activation. "
            "Only frozen independent V9 Tminus1 normal model endpoint is "
            "matched to a candidate initiator location; candidate inventory "
            "built across all six windows BEFORE any T archive read. "
            "Matching posthost T ship, actor and target state is observational "
            "and potentially confounded by other Host phases. Numeric-FC "
            "non-Firecloud false positives explicitly excluded. "
            "No precombat position, fuel roll, mine hit, combat queue, "
            "Nplus1 VCR or executor promotion inferred."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v11",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        src=read_pinned(a.frozen_v11)
        freeze_cases(src)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned immutable public100 unavailable")
        print("[c5-firecloud] checking immutable public100 SHA256",flush=True)
        t=time.monotonic()
        with db.open("rb") as fd:sha=hashlib.file_digest(fd,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("immutable DB checksum changed")
        print(f"[c5-firecloud] verified in {time.monotonic()-t:.1f}s; read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:out=build_report(conn,src)
        finally:conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temp=a.output.with_suffix(a.output.suffix+".tmp")
        temp.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 PHASE AWARE FIRECLOUD V12 =====")
    print("status:",out["status"])
    print("summary:",out["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
