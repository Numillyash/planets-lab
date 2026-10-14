"""Ordinary C5 T-1 -> T spatial-site *error attribution*, not another predictor.

Input: frozen public100 preselection and frozen current-N conditional C5 v2.
For ALL 63 source transitions, examine the T-1 spatial predictions for the
ship identities factually seen in VCR N+1. These N+1 identities are revealed
ONLY as observational post-hoc comparators after the immutable V2 verdict:
they MUST NOT enter combat selection, candidate construction or repair.

Purpose: explain 25 V2 NO_PAIR and 8 UNRESOLVED cases by independently
calculated T-1 reachability and position provenance. No alternative Host
battle rules, no Horwasp, no next-VCR-oracle queue predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
import combat_c5_ordinary_parent_forward_v1 as strict
import combat_c5_current_n_roster_bridge_v2 as conditional
import combat_public_capture_o_layer_probe as o_layer
import combat_site_state_differential_v1 as site_diag

SCHEMA="planets-lab.combat-c5-tminus1-site-recall-attribution.v3"
STATUS="OBSERVATIONAL_TMINUS1_SITE_RECALL_NOT_QUEUE_PROMOTION"
CENSUS_BLOB="fda92475988d2f7dfbc7b93606de4f8cec909806"
CONDITIONAL_V2_BLOB="dd641864dc3bd541098ea2c21cf21fb8ff03d5ce"
GENERATION=strict.GENERATION
SHA256=strict.SHA256


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def read_frozen(path:Path,blob:str)->dict[str,Any]:
    raw=path.read_bytes()
    if strict.blob_sha1(raw)!=blob:
        raise ValueError("published Git blob SHA1 mismatch: "+str(path))
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("frozen source is not JSON object")
    return obj


def validate_sources(census:Mapping[str,Any],v2:Mapping[str,Any])->tuple[
    list[dict[str,Any]], dict[tuple[int,int,int,int], Mapping[str,Any]]]:
    sites=strict.freeze_sites(census)
    if (v2.get("schema")!=conditional.SCHEMA
        or v2.get("status")!=conditional.STATUS
        or v2.get("source_census_git_blob_sha1")!=CENSUS_BLOB
        or v2.get("source_db_sha256")!=SHA256):
        raise ValueError("frozen conditional V2 source/schema drift")
    summary=v2.get("summary")
    if not isinstance(summary,Mapping):
        raise ValueError("missing conditional V2 summary")
    for key,value in {
        "frozen_sites":27,"frozen_adjacent_ID_transitions":63,
        "attempted_transitions":56,"site_failure_transitions":7,
        "conditional_predictions_made":9,
        "conditional_pair_and_sides_exact":7,
        "conditional_pair_or_sides_mismatch":2,
    }.items():
        if summary.get(key)!=value:
            raise ValueError(f"frozen conditional V2 population drift: {key}")
    source_sites=v2.get("site_evaluations")
    if not isinstance(source_sites,list):
        raise ValueError("frozen V2 site list missing")
    index={}
    for site in source_sites:
        key=(site["game_id"],site["turn"],site["x"],site["y"])
        if key in index:raise ValueError("duplicate source site")
        index[key]=site
    if set(index)!={(s["game_id"],s["turn"],s["x"],s["y"]) for s in sites}:
        raise ValueError("frozen V2 sites differ from original census")
    for site in sites:
        key=(site["game_id"],site["turn"],site["x"],site["y"])
        prior=index[key]
        ids=[(r["from_vcr_id"],r["to_vcr_id"])
             for r in prior.get("transitions",[])]
        if sorted(ids)!=sorted(site["adjacent_pairs"]) and not (
            not ids and prior.get("missing")==len(site["adjacent_pairs"])
        ):
            raise ValueError("frozen V2 transition identities drift")
    return sites,index


def same_site(position:Any,x:int,y:int)->bool:
    return (isinstance(position,(list,tuple)) and len(position)==2
            and integer(position[0])==x and integer(position[1])==y)


def predicted_next_participant(
    *,ship_id:int,owner_id:int,site:tuple[int,int],
    predictions:Mapping[int,Mapping[str,Any]],
    current_ship_ids:frozenset[int],history_ship_ids:frozenset[int],
)->dict[str,Any]:
    """Post-verdict analysis ONLY, never calls queue selection."""
    if integer(ship_id) is None or ship_id<=0:
        raise ValueError("invalid factual next ship")
    result={"ship_id":ship_id,"actual_next_owner":owner_id,
            "in_prior_N":ship_id in current_ship_ids,
            "seen_at_site_before_or_during_N":ship_id in history_ship_ids,
            "factual_next_identity_used_only_for_posthoc_attribution":True}
    entry=predictions.get(ship_id)
    if not isinstance(entry,Mapping):
        return {**result,"Tminus1_position_class":"TMINUS1_SHIP_NOT_IN_OWNER_ARCHIVE",
                "source":None,"predicted_position":None,"owner_consistent":None,
                "raw_Tminus1_x_y":None}
    pos=entry.get("position")
    src=entry.get("source")
    owner=integer(entry.get("owner_id"))
    raw=entry.get("raw")
    if not isinstance(raw,Mapping):raw={}
    raw_x=integer(raw.get("x"))
    raw_y=integer(raw.get("y"))
    if owner!=owner_id:
        cls="TMINUS1_OWNER_DIFFERS_FROM_NEXT_VCR"
    elif same_site(pos,*site):
        cls="TMINUS1_PREDICTS_FACTUAL_SITE"
    elif pos is None:
        cls="TMINUS1_POSITION_UNRESOLVED"
    else:
        cls="TMINUS1_PREDICTS_DIFFERENT_SITE"
    return {
        **result,"Tminus1_position_class":cls,"source":str(src) if src is not None else None,
        "predicted_position":list(pos) if isinstance(pos,(list,tuple)) else None,
        "owner_consistent":owner==owner_id,
        "raw_Tminus1_x_y":[raw_x,raw_y] if raw_x is not None and raw_y is not None else None,
        "raw_Tminus1_warp":integer(raw.get("warp")),
        "raw_Tminus1_targetx":integer(raw.get("targetx")),
        "raw_Tminus1_targety":integer(raw.get("targety")),
    }


def outcome_class(rows:Sequence[Mapping[str,Any]])->str:
    statuses=[r["Tminus1_position_class"] for r in rows]
    if any(r=="TMINUS1_SHIP_NOT_IN_OWNER_ARCHIVE" for r in statuses):
        return "NEXT_PAIR_MISSING_TMINUS1_SHIP"
    if any(r=="TMINUS1_OWNER_DIFFERS_FROM_NEXT_VCR" for r in statuses):
        return "NEXT_PAIR_TMINUS1_OWNER_DRIFT"
    count=sum(r=="TMINUS1_PREDICTS_FACTUAL_SITE" for r in statuses)
    if count==2:return "NEXT_PAIR_BOTH_TMINUS1_AT_SITE"
    if count==1:return "NEXT_PAIR_ONE_TMINUS1_AT_SITE"
    return "NEXT_PAIR_NEITHER_TMINUS1_AT_SITE"


def inspect_after_v2_verdict(
    *,frozen_transition:Mapping[str,Any],
    current:Mapping[str,Any],next_row:Mapping[str,Any],
    site:tuple[int,int],context:Mapping[str,Any],
)->dict[str,Any]:
    """N+1 is permitted here because frozen V2 selection is ALREADY final."""
    predictions=context.get("predictions")
    if not isinstance(predictions,Mapping):
        raise ValueError("T-1 site prediction map unavailable")
    n=integer(frozen_transition.get("from_vcr_id"))
    future=integer(frozen_transition.get("to_vcr_id"))
    if n is None or future is None or future!=n+1:
        raise ValueError("invalid frozen adjacent VCR identity")
    if integer(current.get("vcr_id"))!=n or integer(next_row.get("vcr_id"))!=future:
        raise ValueError("site VCR chronology/member drift")
    current_ids=frozenset(int(current[k]) for k in ("left_ship_id","right_ship_id"))
    historic=context.get("factual_queue")
    if not isinstance(historic,Sequence):
        raise ValueError("site history unavailable")
    history_ids=frozenset(
        int(row[k]) for row in historic
        if isinstance(row,Mapping) and integer(row.get("vcr_id")) is not None
        and row["vcr_id"]<=n
        for k in ("left_ship_id","right_ship_id")
        if integer(row.get(k)) is not None
    )
    parties=[]
    for side in ("left","right"):
        ship=integer(next_row.get(side+"_ship_id"))
        if ship is None:raise ValueError("factual next participant missing")
        # Owner of N+1 is retrieved from the *factual* N+1 VCR payload;
        # never used to construct a prediction. Context baseline next
        # case is intentionally not passed to the predictor.
        owner_map=next_row.get("owners_by_ship_id")
        if not isinstance(owner_map,Mapping):
            raise ValueError("posthoc factual N+1 owner mapping unavailable")
        owner=integer(owner_map.get(ship))
        if owner is None or owner<=0:
            raise ValueError("posthoc N+1 owner unknown")
        item=predicted_next_participant(
            ship_id=ship,owner_id=owner,site=site,predictions=predictions,
            current_ship_ids=current_ids,history_ship_ids=history_ids)
        parties.append(item)
    return {
        "frozen_conditional_V2_status":frozen_transition["status"],
        "frozen_conditional_V2_prediction":frozen_transition.get("prediction"),
        "frozen_conditional_V2_accuracy":(
            frozen_transition.get("factual_comparison",{}).get("exact")),
        "from_VCR":n,"to_VCR":future,
        "posthoc_next_pair_Tminus1_class":outcome_class(parties),
        "posthoc_next_ship_Tminus1_positions":parties,
        "next_VCR_used_in_prediction":False,
        "posthoc_factual_Nplus1_dependent":True,
    }


def build_report(census:Mapping[str,Any],v2:Mapping[str,Any],conn:Any)->dict[str,Any]:
    selected,v2_index=validate_sources(census,v2)
    windows=defaultdict(list)
    for site in selected:
        windows[(site["game_id"],site["turn"])].append(site)
    evaluations=[]
    for i,((game,turn),sites) in enumerate(sorted(windows.items()),1):
        print(f"[c5-site-recall] [{i}/{len(windows)}] G{game} T{turn} sites={len(sites)}",flush=True)
        contexts={}
        context_error=None
        cases={}
        try:
            appearances,_=o_layer._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns={turn})
            o_layer._visit_targeted_site_contexts(
                connection=conn,game_id=game,
                targets={(game,turn,s["x"],s["y"]):() for s in sites},
                appearances=appearances,
                observer=lambda ctx:contexts.__setitem__(
                    (ctx["game_id"],ctx["battle_turn"],ctx["x"],ctx["y"]),dict(ctx))
            )
            # Used only after the published V2 choices are read.
            cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
        except (ValueError,TypeError,KeyError) as exc:
            context_error=f"{type(exc).__name__}:{exc}"
        for s in sites:
            key=(game,turn,s["x"],s["y"])
            frozen_site=v2_index[key]
            ctx=contexts.get(key)
            out=[]
            if ctx is not None:
                factual=ctx.get("factual_queue")
                predictions=ctx.get("predictions")
                if not isinstance(factual,Sequence) or not isinstance(predictions,Mapping):
                    ctx=None
                else:
                    lookup={r["vcr_id"]:r for r in factual}
                    if sorted(lookup)!=s["vcr_ids"]:
                        raise ValueError("published site and reconstituted factual VCR membership drift")
                    for tr in frozen_site.get("transitions",[]):
                        n,nplus1=tr["from_vcr_id"],tr["to_vcr_id"]
                        # Read N+1 owner identities only in this after-verdict
                        # reporting path, never in any forward selector.
                        curr,raw_next=lookup[n],lookup[nplus1]
                        case=cases.get((turn,nplus1))
                        if case is None or not isinstance(case.payload,Mapping):
                            raise ValueError("factual N+1 VCR payload absent for posthoc owner provenance")
                        game_vcr_owner={}
                        for side in ("left","right"):
                            body=case.payload.get(side)
                            owner=integer(case.payload.get(side+"ownerid"))
                            sid=integer(body.get("objectid")) if isinstance(body,Mapping) else None
                            if sid is None or owner is None or sid<=0 or owner<=0:
                                raise ValueError("posthoc factual N+1 owner/ship invalid")
                            expected=integer(raw_next.get(side+"_ship_id"))
                            if expected!=sid:
                                raise ValueError("posthoc factual N+1 identity diverges from frozen site queue")
                            game_vcr_owner[sid]=owner
                        x=inspect_after_v2_verdict(
                            frozen_transition=tr,current=curr,
                            next_row={**raw_next,"owners_by_ship_id":game_vcr_owner},
                            site=(s["x"],s["y"]),context=ctx)
                        out.append(x)
            if ctx is None:
                out=[]
            evaluations.append({
                "game_id":game,"turn":turn,"x":s["x"],"y":s["y"],
                "source_site_status":frozen_site["status"],
                "source_site_transition_count":len(frozen_site.get("transitions",[])),
                "source_site_missing_count":frozen_site.get("missing",0),
                "context_reconstructed":ctx is not None,
                "context_error":context_error if ctx is None else None,
                "transition_posthoc_evaluations":out,
            })
    inspected=[r for s in evaluations for r in s["transition_posthoc_evaluations"]]
    count=Counter(r["posthoc_next_pair_Tminus1_class"] for r in inspected)
    cross=defaultdict(Counter)
    sources=defaultdict(Counter)
    for r in inspected:
        key=r["frozen_conditional_V2_status"]
        cross[key][r["posthoc_next_pair_Tminus1_class"]]+=1
        for p in r["posthoc_next_ship_Tminus1_positions"]:
            if p["Tminus1_position_class"]!="TMINUS1_PREDICTS_FACTUAL_SITE":
                sources[key][p["source"] or "UNKNOWN_SOURCE"]+=1
    if len(evaluations)!=27:
        raise ValueError("coverage changed from 27 sites")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_census_git_blob_sha1":CENSUS_BLOB,
        "source_conditional_v2_git_blob_sha1":CONDITIONAL_V2_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_sites":27,"frozen_adjacent_transitions":63,
            "original_conditional_V2_predictions":9,
            "original_conditional_V2_exact":7,
            "posthoc_transitions_inspected":len(inspected),
            "posthoc_transitions_without_site_context":63-len(inspected),
            "posthoc_next_pair_site_position_counts":dict(sorted(count.items())),
            "by_original_V2_status":{k:dict(sorted(v.items())) for k,v in sorted(cross.items())},
            "failed_next_ship_Tminus1_position_sources_by_V2_status":{
                k:dict(sorted(v.items())) for k,v in sorted(sources.items())
            },
            "new_queue_predictions_made":0,
            "existing_predictions_changed":0,
            "future_Nplus1_used_to_select_queue":False,
            "full_Host_prediction_promoted":False,
        },
        "site_evaluations":evaluations,
        "boundary":(
            "Frozen 27 sites/63 transitions and 9/7 V2 conditional results "
            "remain unchanged. T-1 ship movement/position calculation is "
            "independent; factual N+1 ship IDs and owner identity are supplied "
            "ONLY inside a post-verdict diagnostic. This is a retrospective "
            "failure attribution, not selection or validation of a next "
            "pair, nor a demonstration of Host movement accuracy on all "
            "ships. Exact VCR order unproven. No race12, production, CURRENT, "
            "or combat executor changes."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-census",type=Path,required=True)
    p.add_argument("--frozen-conditional-v2",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        census=read_frozen(a.frozen_census,CENSUS_BLOB)
        v2=read_frozen(a.frozen_conditional_v2,CONDITIONAL_V2_BLOB)
        validate_sources(census,v2)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 missing")
        ts=time.monotonic()
        print("[c5-site-recall] verifying immutable public100 SHA256 once",flush=True)
        with db.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("pinned SHA256 drift")
        print(f"[c5-site-recall] SHA256 verified in {time.monotonic()-ts:.1f}s",flush=True)
        conn,path=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(census,v2,conn)
        finally:conn.close()
        report["database_path"]=str(path)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 T-1 SITE RECALL / NO-PAIR CAUSE ATTRIBUTION V3 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
