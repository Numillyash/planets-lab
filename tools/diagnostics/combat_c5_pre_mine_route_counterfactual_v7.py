"""C5 V7: independent T-1 normal-movement endpoint *conditional on no mine hit*.

Takes 12 archived-waypoint-only mine-risk witnesses in the frozen V6 cohort,
reconstructs pre-mine normal-movement planner output using the existing
T-1 site context builder's opt-in diagnostic field, and compares endpoint
with the PRESELECTED current-N site, not any future VCR N+1 opponent.
A no-hit destination is a counterfactual, NEVER a factual Host position.
This is already-open exploratory data concentrated in ONE game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
import combat_public_capture_o_layer_probe as site_builder

SCHEMA="planets-lab.combat-c5-pre-mine-route-counterfactual.v7"
STATUS="TMINUS1_PRE_MINE_NORMAL_ROUTE_CONDITIONAL_NOT_HOST_PREDICTION"
V6_SHA1="51d21132e4db89511be59805ebe2be14014b3e7a"
V6_SCHEMA="planets-lab.combat-c5-tminus1-ingress-residence.v6"
V6_STATUS="PRE_N_SITE_INGRESS_VS_RESIDENCE_OBSERVATIONAL_NOT_PROMOTED"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SHA256="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
NO_PAIR="ABSTAIN_PARENT_STANDARD_NO_PAIR"
WAYPOINT_ONLY="UNSEEN_TMINUS1_WAYPOINT_AT_SITE_ONLY"


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def pinned(path:Path)->dict[str,Any]:
    raw=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    if digest!=V6_SHA1:
        raise ValueError("published V6 Git blob SHA1 mismatch")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("V6 report root invalid")
    return obj


def freeze_mine_targets(v6:Mapping[str,Any])->dict[tuple[int,int,int,int],dict[int,dict[str,Any]]]:
    """Preselect T-1 source cases; no current/future VCR participant query."""
    if v6.get("schema")!=V6_SCHEMA or v6.get("status")!=V6_STATUS:
        raise ValueError("frozen V6 identity/status changed")
    summary=v6.get("summary")
    expected={
        "frozen_sites":27,"frozen_adjacent_transitions":63,
        "evaluated_transitions":56,"source_uninspected":7,
        "NO_PAIR_transitions":25,
        "NO_PAIR_unique_unseen_site_ship_witnesses":42,
        "NO_PAIR_unseen_prior_site_witness_appearances":107,
        "new_battle_predictions":0,
        "changed_original_V2_predictions":0,
        "Nplus1_used":False,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in expected.items()):
        raise ValueError("frozen V6 source coverage/proof boundary changed")
    sites=v6.get("sites")
    if not isinstance(sites,list) or len(sites)!=27:
        raise ValueError("V6 frozen site list incomplete")
    seen_sites=set()
    selected:dict[tuple[int,int,int,int],dict[int,dict[str,Any]]]={}
    all_transitions=0
    no_pair=0
    for site in sites:
        if not isinstance(site,Mapping):
            raise ValueError("invalid V6 site")
        vals=tuple(integer(site.get(k)) for k in ("game_id","turn","x","y"))
        if None in vals or vals[0]<=0 or vals[1]<1 or vals in seen_sites:
            raise ValueError("duplicate or invalid V6 site identity")
        seen_sites.add(vals)
        rows=site.get("transition_evaluations")
        if not isinstance(rows,list):
            raise ValueError("V6 transition list missing")
        ids=set()
        for row in rows:
            n=integer(row.get("from_vcr_id")) if isinstance(row,Mapping) else None
            if n is None or n<=0 or n in ids:
                raise ValueError("duplicate or invalid V6 transition N")
            ids.add(n)
            all_transitions+=1
            if row.get("Nplus1_used") is not False or row.get("new_pair_predictions")!=0:
                raise ValueError("V6 post-N leakage or prediction promotion")
            if row.get("original_v2_status")!=NO_PAIR:
                continue
            no_pair+=1
            evidence=row.get("Tminus1_witnesses")
            if not isinstance(evidence,list):
                raise ValueError("V6 witnesses unavailable")
            for w in evidence:
                if not isinstance(w,Mapping):
                    raise ValueError("V6 witness invalid")
                if w.get("class")!=WAYPOINT_ONLY or w.get("position_source")!="normal_mine_route_risk":
                    continue
                sid=integer(w.get("ship_id"))
                owner=integer(w.get("owner_id"))
                if (sid is None or sid<=0 or owner is None or owner<=0 or
                    w.get("first_prior_site_vcr_id") is not None or
                    w.get("Tminus1_start_at_site") is not False or
                    w.get("Tminus1_waypoint_at_site") is not True):
                    raise ValueError("V6 mine-waypoint identity/geometry invalid")
                target=selected.setdefault(vals,{})
                if sid in target and target[sid]["owner_id"]!=owner:
                    raise ValueError("same site-ship has conflicting T-1 owner")
                target[sid]={"ship_id":sid,"owner_id":owner,
                             "source":"normal_mine_route_risk"}
    if (len(seen_sites)!=27 or all_transitions!=56 or no_pair!=25 or
            sum(map(len,selected.values()))!=12):
        raise ValueError("frozen V6 mine-risk population changed")
    return selected


def _position(x:Any)->tuple[int,int]|None:
    if (not isinstance(x,(tuple,list)) or len(x)!=2 or
            any(integer(v) is None for v in x)):
        return None
    return (x[0],x[1])


def evaluate_site(
    *, context:Mapping[str,Any],
    site_key:tuple[int,int,int,int],
    target_ships:Mapping[int,Mapping[str,Any]],
    max_controls_per_class:int=5,
)->dict[str,Any]:
    """Only T-1 prediction map + frozen V6 ship/owner/site are read.

    The context also carries factual current/future VCR queues for other
    research paths. They are deliberately NEVER accessed in this function.
    """
    if max_controls_per_class<1:
        raise ValueError("invalid control sampling bound")
    game,turn,x,y=site_key
    for name,value in (("game_id",game),("battle_turn",turn),("x",x),("y",y)):
        if context.get(name)!=value:
            raise ValueError("T-1 context/site identity mismatch")
    predictions=context.get("predictions")
    if not isinstance(predictions,Mapping):
        raise ValueError("T-1 predictions unavailable")
    witnesses=[]
    for sid,identity in sorted(target_ships.items()):
        entry=predictions.get(sid)
        if not isinstance(entry,Mapping):
            witnesses.append({"ship_id":sid,"status":"ABSTAIN_TMINUS1_SHIP_MISSING",
                              "conditional_no_mine_destination":None})
            continue
        raw=entry.get("raw")
        if (entry.get("owner_id")!=identity["owner_id"] or
                entry.get("ship_id")!=sid or
                entry.get("source")!="normal_mine_route_risk" or
                entry.get("position") is not None or
                not isinstance(raw,Mapping) or raw.get("id")!=sid or
                raw.get("ownerid")!=identity["owner_id"]):
            raise ValueError("frozen V6 mine-risk source disagrees with reconstructed T-1")
        if ((raw.get("x"),raw.get("y"))==(x,y) or
                (raw.get("targetx"),raw.get("targety"))!=(x,y)):
            raise ValueError("reconstructed T-1 site start/waypoint identity drift")
        endpoint=_position(entry.get("diagnostic_no_mine_hit_destination"))
        pre_mine_source=entry.get("diagnostic_no_mine_hit_source")
        if endpoint is None or not isinstance(pre_mine_source,str) or not pre_mine_source.startswith("normal_move"):
            status="ABSTAIN_PRE_MINE_PLANNER_OUTPUT_UNAVAILABLE"
        else:
            status=("COUNTERFACTUAL_NO_MINE_ROUTE_ENDS_AT_SITE" if endpoint==(x,y)
                    else "COUNTERFACTUAL_NO_MINE_ROUTE_ENDS_ELSEWHERE")
        witnesses.append({
            "ship_id":sid,"owner_id":identity["owner_id"],
            "Tminus1_source":"normal_mine_route_risk",
            "pre_mine_normal_planner_source":pre_mine_source,
            "conditional_no_mine_destination":list(endpoint) if endpoint else None,
            "site_match_without_mine_interference":endpoint==(x,y) if endpoint else None,
            "status":status,
            "actual_N_position_proven":False,
            "combat_eligibility_proven":False,
        })
    controls={"Tminus1_normal_route_ends_at_site":[],
              "Tminus1_normal_route_ends_elsewhere":[]}
    all_counts=Counter()
    for sid,entry in sorted(predictions.items()):
        if (sid in target_ships or not isinstance(entry,Mapping)
                or not isinstance(entry.get("source"),str)
                or not entry["source"].startswith("normal_move")):
            continue
        pos=_position(entry.get("position"))
        if pos is None:continue
        cls=("Tminus1_normal_route_ends_at_site" if pos==(x,y)
             else "Tminus1_normal_route_ends_elsewhere")
        all_counts[cls]+=1
        if len(controls[cls])<max_controls_per_class:
            controls[cls].append({"ship_id":sid,
                                  "Tminus1_model_endpoint":list(pos),
                                  "Tminus1_source":entry["source"]})
    return {
        **dict(zip(("game_id","turn","x","y"),site_key)),
        "status":"CONDITIONAL_NO_MINE_RECONSTRUCTION_NO_HOST_POSITION_CLAIM",
        "witnesses":witnesses,
        "Tminus1_normal_route_controls_sample":controls,
        "Tminus1_normal_route_controls_total_counts":dict(sorted(all_counts.items())),
        "controls_are_model_checks_not_Host_presence_labels":True,
        "future_VCR_accessed_in_evaluation":False,
    }


def build_report(conn:Any, frozen:Mapping[str,Any])->dict[str,Any]:
    targets=freeze_mine_targets(frozen)
    windows=defaultdict(dict)
    for key,ships in targets.items():
        windows[(key[0],key[1])][key]=ships
    results=[]
    errors=[]
    for i,((game,turn),sites) in enumerate(sorted(windows.items()),1):
        print(f"[c5-pre-mine] [{i}/{len(windows)}] G{game} T{turn} sites={len(sites)}",flush=True)
        contexts={}
        try:
            appearances,_=site_builder._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns={turn})
            site_builder._visit_targeted_site_contexts(
                connection=conn,game_id=game,
                targets={key:() for key in sites},
                appearances=appearances,
                observer=lambda ctx:contexts.__setitem__(
                    (ctx["game_id"],ctx["battle_turn"],ctx["x"],ctx["y"]),ctx),
                collect_pre_mine_counterfactual=True,
            )
        except (ValueError,TypeError,KeyError) as exc:
            errors.append({"game_id":game,"turn":turn,
                           "reason":f"{type(exc).__name__}:{exc}"})
        for key,ships in sorted(sites.items()):
            if key not in contexts:
                results.append({**dict(zip(("game_id","turn","x","y"),key)),
                                "status":"ABSTAIN_SITE_CONTEXT_UNAVAILABLE",
                                "witnesses":[{"ship_id":sid,"status":"ABSTAIN_SITE_CONTEXT_UNAVAILABLE"}
                                             for sid in sorted(ships)],
                                "future_VCR_accessed_in_evaluation":False})
            else:
                results.append(evaluate_site(
                    context=contexts[key],site_key=key,target_ships=ships))
    rows=[w for s in results for w in s["witnesses"]]
    if len(rows)!=12 or len(results)!=len(targets):
        raise ValueError("frozen 12 witness completeness lost")
    c=Counter(w["status"] for w in rows)
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_SHA1,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "original_frozen_sites":27,
            "original_adjacent_transitions":63,
            "original_NO_PAIR_transitions":25,
            "V6_waypoint_only_witnesses_all_sources":18,
            "distinct_mine_risk_waypoint_only_witnesses":12,
            "distinct_game_turn_windows":len(windows),
            "observed_site_count":len(results),
            "conditional_no_hit_endpoint_status_counts":dict(sorted(c.items())),
            "context_errors":len(errors),
            "full_Host_ship_positions_predicted":0,
            "new_combat_pair_predictions":0,
            "Nplus1_target_or_comparator_used":False,
            "frozen_V2_queue_score_unchanged":True,
        },
        "site_evaluations":results,
        "context_errors":errors,
        "boundary":(
            "Only preselected V6 T-1 ship identity/owner/waypoint and independent "
            "T-1 normal planner position BEFORE mine-risk gating are used. The "
            "counterfactual removes ONLY the uncertainty mask from the computed "
            "normal endpoint; it is NOT a model of mine-hit survival or fuel "
            "loss, and is NOT the actual final Host position. Controls are "
            "T-1 normal-route model positives/negatives with respect to a "
            "site, NOT factual Host present/absent labels. Selected cases are "
            "already-open and concentrated in a single game. No future VCR "
            "N+1 enters the evaluator, no pair prediction, no production change."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v6",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        frozen=pinned(args.frozen_v6)
        targets=freeze_mine_targets(frozen)
        dbfile=args.corpus_db_root/GENERATION
        if not dbfile.is_file():
            raise ValueError("pinned public100 missing")
        print("[c5-pre-mine] checking pinned immutable public100 SHA256 once",flush=True)
        t=time.monotonic()
        with dbfile.open("rb") as f:
            digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:
            raise ValueError("immutable public100 SHA256 mismatch")
        print(f"[c5-pre-mine] verified {len(targets)} sites in {time.monotonic()-t:.1f}s; read-only DB",flush=True)
        conn,path=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:report=build_report(conn,frozen)
        finally:conn.close()
        report["db_path"]=str(path)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=args.output.with_suffix(args.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        tmp.replace(args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 PRE-MINE NORMAL ROUTE COUNTERFACTUAL V7 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
