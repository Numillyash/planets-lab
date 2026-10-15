"""V19: independent T-1 graph chaining controls and 25 LY anomaly tracing.

Retroactive V17/V18 source studies; this is NOT new heldout inference.
Construct graph-chain candidates exclusively from frozen V17 T-1 edges.
Only after graph freeze are V17 posthost fields accessed. Separately
freeze exact T-1 owner-current positions/orders of targeted ships in
two windows, then compare T owner-current for the same identities.

A short edge toward an eligible long-distance source may be a *candidate*
local/phase route; it DOES NOT prove that a sub-100LY Warp Chunnel fired.
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
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn
import combat_c5_short_chunnel_and_visibility_audit_v18 as v18
import combat_c5_disjoint_discriminative_chunnel_gates_v17 as v17
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-chunnel-chain-graph-audit.v19"
STATUS="V17_TMINUS1_SHORT_EDGE_CHAIN_AND_25LY_POSTHOC_NOT_EXECUTION_PROOF"
V17_BLOB=v18.V17_BLOB
V18_BLOB="88bd596534e5e7390c21d6a0a108c732e8a07150"
GENERATION=v18.GENERATION
SHA256=v18.SHA256
TARGET_WINDOWS=((338264,50),(467386,75))
TARGET_SHIPS={
    (338264,50):(204,116,129,234,308),
    (467386,75):(467,80,193,235,405),
}
SHORT_GATE="DISTANCE_BELOW_100_AT_TMINUS1"
LONG_COHORT="ALL_TMINUS1_GATES_PASS"


def iv(v:Any)->int|None:
    return v if type(v) is int else None


def xy(v:Any)->tuple[int,int]|None:
    return v17.point(v)


def pinned(path:Path,digest:str):
    raw=path.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if blob!=digest:raise ValueError("pinned Git blob changed: "+str(path))
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError("pinned report invalid")
    return value


def source_precheck(v17src:Mapping[str,Any],v18src:Mapping[str,Any]):
    old,wins=v18.frozen_v17(v17src)
    if (v18src.get("schema")!=v18.SCHEMA or
        v18src.get("status")!=v18.STATUS or
        v18src.get("source_v17_git_blob_sha1")!=V17_BLOB or
        v18src.get("source_db_sha256")!=SHA256):
        raise ValueError("V18 provenance differs")
    summary=v18src.get("summary")
    want={
        "V17_frozen_48_windows_16_games":True,
        "V17_frozen_113_candidates":113,
        "targeted_V17_positive_owner_current_abstentions":14,
        "targeted_V17_discriminative_negative_edges":6,
        "targeted_Tminus1_windows":6,
        "reverified_Tminus1_T_cases":20,
        "source_owner_T_perspective_missing_appearances":0,
        "actor_T_owner_current_unavailable_appearances":14,
        "posthoc_25ly_anomaly_cases":1,
        "new_Host_movement_or_combat_predictions":0,
        "Host_short_distance_Chunnel_or_activation_proven":False,
        "Nplus1_VCR_used":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in want.items()):
        raise ValueError("V18 original observational counts changed")
    if not all(w in {(r["game_id"],r["turn"]) for r in v17src["windows"]}
               for w in TARGET_WINDOWS):
        raise ValueError("targeted graph windows not in V17")
    return old,wins


def freeze_tminus1_graph(v17src:Mapping[str,Any]):
    """Construct all short->valid-long two-edge paths solely with T-1 fields."""
    graphs={}
    all_edges=0
    for window in v17src["windows"]:
        game,turn=window["game_id"],window["turn"]
        ed=[]
        for e in window["edges"]:
            start,dst=xy(e["source"]),xy(e["target"])
            if (None in (start,dst) or
                e["game_id"]!=game or e["turn"]!=turn or
                e["cohort"] not in (LONG_COHORT,"ONE_TMINUS1_GATE_FAILS")):
                raise ValueError("V17 graph source Tminus1 identity invalid")
            ed.append({
                "game_id":game,"turn":turn,
                "initiator_ship_id":e["initiator_ship_id"],
                "target_ship_id":e["target_ship_id"],
                "owner_id":e["owner_id"],
                "source":list(start),"target":list(dst),
                "cohort":e["cohort"],
                "failing_gate":e["single_failing_gate"],
                "discriminative":start!=dst,
                "distance_ly":e["Tminus1_distance_ly"],
                "Tminus1_graph_only":True,
            })
        all_edges+=len(ed)
        graphs[game,turn]=ed
    if all_edges!=113 or len(graphs)!=48:
        raise ValueError("V17 frozen 113/48 graph denominator drift")
    chains=[]
    for (game,turn),ed in sorted(graphs.items()):
        by_source=defaultdict(list)
        for edge in ed:
            if edge["cohort"]==LONG_COHORT:
                by_source[edge["initiator_ship_id"]].append(edge)
        for first in ed:
            if (first["cohort"]!="ONE_TMINUS1_GATE_FAILS" or
                first["failing_gate"]!=SHORT_GATE or
                not first["discriminative"]):
                continue
            for next_edge in by_source.get(first["target_ship_id"],[]):
                if (first["owner_id"]!=next_edge["owner_id"] or
                    xy(first["target"])!=xy(next_edge["source"]) or
                    next_edge["initiator_ship_id"]==next_edge["target_ship_id"]):
                    continue
                chains.append({
                    "game_id":game,"turn":turn,
                    "first_actor_id":first["initiator_ship_id"],
                    "intermediate_firecloud_id":first["target_ship_id"],
                    "second_target_id":next_edge["target_ship_id"],
                    "owner_id":first["owner_id"],
                    "first_source":first["source"],
                    "middle_Tminus1_site":first["target"],
                    "second_target":next_edge["target"],
                    "short_first_distance_ly":first["distance_ly"],
                    "second_eligible_distance_ly":next_edge["distance_ly"],
                    "graph_only_not_activation_evidence":True,
                })
    return graphs,chains


def posthoc_graph_comparison(chains,original:Mapping[tuple[int,...],Mapping[str,Any]]):
    outcomes=[]
    for c in chains:
        g,t=c["game_id"],c["turn"]
        key1=(g,t,c["first_actor_id"],c["intermediate_firecloud_id"])
        key2=(g,t,c["intermediate_firecloud_id"],c["second_target_id"])
        first=original.get(key1); second=original.get(key2)
        if first is None or second is None:raise ValueError("V17 posthost chained edge missing")
        end=xy(c["second_target"])
        first_after=xy(first["T_actor_position"]) if first["T_actor_position"] is not None else None
        second_after=xy(second["T_actor_position"]) if second["T_actor_position"] is not None else None
        outcomes.append({
            **c,
            "T_first_actor_status":first["T_actor_status"],
            "T_second_actor_status":second["T_actor_status"],
            "T_first_actor_position":list(first_after) if first_after else None,
            "T_second_actor_position":list(second_after) if second_after else None,
            "T_first_actor_at_downstream_target":first_after==end if first_after else None,
            "T_second_actor_at_downstream_target":second_after==end if second_after else None,
            "T_first_actor_net_fuel_delta_KT":first["T_actor_net_fuel_delta_KT"],
            "T_second_actor_net_fuel_delta_KT":second["T_actor_net_fuel_delta_KT"],
            "posthoc_correlation_not_chunnel_execution_proof":True,
        })
    return outcomes


def freeze_focus_tminus1(conn:Any,game:int,turn:int):
    """All selected ship state and model status come from exact T-1 only."""
    snapshots,raw=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),turn-1)
    ids=TARGET_SHIPS[game,turn]
    models=[]
    excluded={}
    try:
        preds,excluded,_seen=v9.forecast_pre_window(game,turn,snapshots,raw)
        models=preds
    except (ValueError,KeyError,TypeError) as err:
        excluded={"Tminus1_normal_planner_context_abstain":f"{type(err).__name__}:{err}"}
    forecast={r["ship_id"]:r for r in models}
    rows=[]
    for sid in ids:
        entry=roster.get(sid)
        if entry is None:
            rows.append({"ship_id":sid,"Tminus1_status":"ABSTAIN_OWNER_CURRENT_MISSING"})
            continue
        owner,record=entry
        start=xy((record.get("x"),record.get("y")))
        wp=xy((record.get("targetx"),record.get("targety")))
        if start is None:raise ValueError("missing targeted ship T-1 position")
        model=forecast.get(sid)
        rows.append({
            "ship_id":sid,"owner_id":owner,
            "Tminus1_status":"OWNER_CURRENT",
            "Tminus1_position":list(start),
            "Tminus1_waypoint":list(wp) if wp else None,
            "Tminus1_warp":iv(record.get("warp")),
            "Tminus1_mission":iv(record.get("mission")),
            "Tminus1_hull_id":iv(record.get("hullid",record.get("hull_id"))),
            "Tminus1_neutronium":iv(record.get("neutronium")),
            "Tminus1_normal_model_endpoint":model["conditional_or_model_endpoint"] if model else None,
            "Tminus1_normal_model_cohort":model["cohort"] if model else None,
            "Tminus1_no_model_is_not_evidence_of_no_movement":True,
        })
    return {
        "game_id":game,"turn":turn,"selected_ship_rows":rows,
        "Tminus1_normal_forecasts_in_window":len(models),
        "Tminus1_model_context_abstention":excluded,
        "Tminus1_all_rows_frozen_before_T":True,
    }


def post_focus(frozen:Mapping[str,Any],current:Mapping[int,Any]):
    lines=[]
    for row in frozen["selected_ship_rows"]:
        sid=row["ship_id"]
        if row["Tminus1_status"]!="OWNER_CURRENT":
            lines.append({**row,"T_status":"ABSTAIN_TMINUS1_SHIP_MISSING"})
            continue
        owner=row["owner_id"]
        status,raw=v16.v15.get_observation(current,sid,owner,row["Tminus1_hull_id"])
        end=xy((raw.get("x"),raw.get("y"))) if raw is not None else None
        base=xy(row["Tminus1_normal_model_endpoint"]) if row["Tminus1_normal_model_endpoint"] is not None else None
        lines.append({
            **row,
            "T_observation_status":status,
            "T_owner_current_position":list(end) if end else None,
            "T_match_to_normal_Tminus1_endpoint":end==base if end is not None and base is not None else None,
            "T_minus_Tminus1_fuel_KT":(row["Tminus1_neutronium"]-iv(raw.get("neutronium")))
                if raw is not None and iv(raw.get("neutronium")) is not None and
                   row["Tminus1_neutronium"] is not None else None,
            "causal_mechanism_proven":False,
        })
    return {
        "game_id":frozen["game_id"],"turn":frozen["turn"],
        "Tminus1_frozen_forecast_count":frozen["Tminus1_normal_forecasts_in_window"],
        "Tminus1_context_abstention":frozen["Tminus1_model_context_abstention"],
        "selected_ship_posthost_comparisons":lines,
    }


def build_report(conn,v17src,v18src):
    original,_=source_precheck(v17src,v18src)
    graphs,chains=freeze_tminus1_graph(v17src)
    if (338264,50,204,116) not in original or (467386,75,467,80) not in original:
        raise ValueError("frozen special-case identity changed")
    froze={}
    for i,(g,t) in enumerate(TARGET_WINDOWS,1):
        print(f"[c5-v19] PRE [{i}/2] G{g} T{t}",flush=True)
        froze[g,t]=freeze_focus_tminus1(conn,g,t)
    # NO T archive reads occurred before both windows are frozen.
    chain_post=posthoc_graph_comparison(chains,{
        (e["game_id"],e["turn"],e["initiator_ship_id"],e["target_ship_id"]):e
        for w in v17src["windows"] for e in w["edges"]
    })
    focus=[]
    for i,(g,t) in enumerate(TARGET_WINDOWS,1):
        print(f"[c5-v19] POST [{i}/2] G{g} T{t}",flush=True)
        current=v9.after_owner_current(conn,game=g,turn=t)
        focus.append(post_focus(froze[g,t],current))
    hit=next((e for e in chain_post
        if (e["game_id"],e["turn"],e["first_actor_id"],
            e["intermediate_firecloud_id"],e["second_target_id"])
        ==(338264,50,204,116,129)),None)
    isolated=next(e for e in v17src["windows"] if
                  (e["game_id"],e["turn"])==(467386,75))
    short=next(e for e in isolated["edges"] if
               (e["initiator_ship_id"],e["target_ship_id"])==(467,80))
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v17_git_blob_sha1":V17_BLOB,
        "source_v18_git_blob_sha1":V18_BLOB,
        "source_db_generation":GENERATION,
        "source_db_sha256":SHA256,
        "summary":{
            "frozen_V17_windows":len(graphs),
            "frozen_V17_candidate_edges":sum(map(len,graphs.values())),
            "Tminus1_eligible_short_to_long_graph_chains":len(chains),
            "Tminus1_eligible_short_to_long_distinct_windows":len({
                (c["game_id"],c["turn"]) for c in chains}),
            "posthoc_chain_first_actor_at_downstream_target":sum(
                c["T_first_actor_at_downstream_target"] is True for c in chain_post),
            "G338264_T50_204_to_116_to_129_graph_chain_preselected":hit is not None,
            "G467386_T75_467_to_80_has_outgoing_eligible_long_edge":any(
                c["game_id"]==467386 and c["turn"]==75 and
                c["first_actor_id"]==467 and c["intermediate_firecloud_id"]==80
                for c in chains),
            "targeted_Tminus1_windows":2,
            "targeted_ship_identity_appearances":sum(len(w["selected_ship_posthost_comparisons"])
                                                   for w in focus),
            "all_Tminus1_graph_and_rosters_frozen_before_T":True,
            "new_Host_movement_or_combat_predictions":0,
            "short_Chunnel_or_activation_proven":False,
            "Nplus1_VCR_used":False,
        },
        "G467386_T75_25LY_original_Tminus1_edge":{
            "initiator_ship_id":short["initiator_ship_id"],
            "target_ship_id":short["target_ship_id"],
            "source":short["source"],"target":short["target"],
            "distance_ly":short["Tminus1_distance_ly"],
            "posthost_actor":short["T_actor_position"],
            "actual_sub100LY_Chunnel_proven":False,
        },
        "Tminus1_graph_chain_posthoc_comparisons":chain_post,
        "targeted_focus_owner_current_Tminus1_T":focus,
        "boundary":(
            "V19 is intentionally posthoc on V17/V18, NOT an independent "
            "validation dataset. Only exact frozen Tminus1 graph edges and "
            "two targeted Tminus1 owner-current rosters create chains "
            "and passenger candidate features, before any T comparison. "
            "A short first edge ending at a second valid Firecloud actor "
            "is a graph association, not verified local transit; it could "
            "represent another process, and a source ship may move through "
            "other Host phases. The 25LY actor #467 case remains unexplained "
            "even if co-located warp9 ships move together. The normal planner "
            "can abstain on stationary/Chunnel sources; absence of a forecast "
            "is not proof of absence of movement. No archived T can reveal "
            "the actual pre-Chunnel phase or prove activation. No future VCR, "
            "mine event inference, or canonical movement/combat promotion."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    for option in ("frozen-v17","frozen-v18","corpus-db-root","output"):
        parser.add_argument("--"+option,type=Path,required=True)
    args=parser.parse_args()
    try:
        v17src=pinned(args.frozen_v17,V17_BLOB)
        v18src=pinned(args.frozen_v18,V18_BLOB)
        source_precheck(v17src,v18src)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 missing")
        print("[c5-v19] checking immutable public100 SHA256 once",flush=True)
        ts=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("pinned public100 checksum changed")
        print(f"[c5-v19] SHA verified in {time.monotonic()-ts:.1f}s; read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:report=build_report(conn,v17src,v18src)
        finally:conn.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=args.output.with_suffix(args.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError,StopIteration) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 V19 TMINUS1 SHORT-EDGE DOWNSTREAM CHUNNEL GRAPH =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
