"""V8: external T archive endpoint differential against frozen T-1 normal plans.

This is a retrospective *post-Host* positional observation, NOT a
precombat combat-site validation. VCR-site preselection was already open.
The forecast construction never reads T archive owner-current coordinates;
all comparisons happen only after T-1 forecast rows have been frozen.
Mine-risk rows use the conditional no-hit baseline, not a mine RNG prediction.
Never promote an inferred combat participant, position or Host queue pair.
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
for path in (ROOT/"src",Path(__file__).resolve().parent):
    if str(path) not in sys.path:
        sys.path.insert(0,str(path))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.corpus.movement_residual_context import _owner_record
import combat_public_capture_o_layer_probe as site_builder

SCHEMA="planets-lab.combat-c5-posthost-endpoint-controls.v8"
STATUS="EXPLORATORY_POSTHOST_POSITION_DIFFERENTIAL_NO_MINE_HIT_INFERENCE"
V6_BLOB="51d21132e4db89511be59805ebe2be14014b3e7a"
V7_BLOB="f551fc83b1725f7170aae210238ebae68c0e6eee"
V6_SCHEMA="planets-lab.combat-c5-tminus1-ingress-residence.v6"
V7_SCHEMA="planets-lab.combat-c5-pre-mine-route-counterfactual.v7"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
DB_SHA256="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
MINE="NORMAL_MINE_RISK_CONDITIONAL_NO_HIT"
NORMAL="NORMAL_MODEL_NO_INDEXED_MINE_RISK"
SITE_KEYS=("game_id","turn","x","y")


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def position(v:Any)->tuple[int,int]|None:
    if not isinstance(v,(tuple,list)) or len(v)!=2 or any(integer(x) is None for x in v):
        return None
    return tuple(v)


def read_pinned(path:Path,expected:str)->dict[str,Any]:
    raw=path.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if sha!=expected:
        raise ValueError("pinned Git blob SHA mismatch: "+str(path))
    document=json.loads(raw)
    if not isinstance(document,dict):
        raise ValueError("pinned report not JSON object")
    return document


def preselect(v6:Mapping[str,Any],v7:Mapping[str,Any]):
    """Freeze all 27 historical sites and twelve V7 witnesses before T access."""
    if (v6.get("schema")!=V6_SCHEMA or
        v6.get("status")!="PRE_N_SITE_INGRESS_VS_RESIDENCE_OBSERVATIONAL_NOT_PROMOTED" or
        v7.get("schema")!=V7_SCHEMA or
        v7.get("status")!="TMINUS1_PRE_MINE_NORMAL_ROUTE_CONDITIONAL_NOT_HOST_PREDICTION" or
        v7.get("source_v6_git_blob_sha1")!=V6_BLOB or
        v6.get("source_db_sha256")!=DB_SHA256 or
        v7.get("source_db_sha256")!=DB_SHA256):
        raise ValueError("V6/V7 schema/provenance mismatch")
    s6=v6.get("summary")
    s7=v7.get("summary")
    for summary,want in ((s6,{
        "frozen_sites":27,"frozen_adjacent_transitions":63,
        "evaluated_transitions":56,"source_uninspected":7,
        "NO_PAIR_transitions":25,"NO_PAIR_unique_unseen_site_ship_witnesses":42,
        "new_battle_predictions":0,"Nplus1_used":False,
    }),(s7,{
        "distinct_mine_risk_waypoint_only_witnesses":12,
        "observed_site_count":1,"context_errors":0,
        "full_Host_ship_positions_predicted":0,
        "new_combat_pair_predictions":0,
        "Nplus1_target_or_comparator_used":False,
    })):
        if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in want.items()):
            raise ValueError("V6/V7 frozen source summary drift")
    sites=v6.get("sites")
    if not isinstance(sites,list) or len(sites)!=27:
        raise ValueError("V6 frozen source site cohort missing")
    windows:dict[tuple[int,int],set[tuple[int,int,int,int]]]=defaultdict(set)
    for site in sites:
        if not isinstance(site,Mapping):
            raise ValueError("invalid V6 frozen site")
        key=tuple(integer(site.get(k)) for k in SITE_KEYS)
        if None in key or key[0]<=0 or key[1]<1 or key in windows[(key[0],key[1])]:
            raise ValueError("invalid/duplicate V6 site")
        windows[(key[0],key[1])].add(key)
    sources=v7.get("site_evaluations")
    if not isinstance(sources,list) or len(sources)!=1:
        raise ValueError("V7 single-site population drift")
    s=sources[0]
    key=tuple(integer(s.get(k)) for k in SITE_KEYS)
    if key not in windows.get((key[0],key[1]),set()):
        raise ValueError("V7 site does not belong to frozen V6")
    rows=s.get("witnesses")
    if not isinstance(rows,list) or len(rows)!=12:
        raise ValueError("V7 witness population drift")
    target={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("invalid V7 witness")
        sid,owner=integer(row.get("ship_id")),integer(row.get("owner_id"))
        if (sid is None or sid<=0 or owner is None or owner<=0 or sid in target or
            row.get("status")!="COUNTERFACTUAL_NO_MINE_ROUTE_ENDS_AT_SITE" or
            row.get("Tminus1_source")!="normal_mine_route_risk" or
            row.get("actual_N_position_proven") is not False or
            row.get("combat_eligibility_proven") is not False or
            position(row.get("conditional_no_mine_destination"))!=key[2:]):
            raise ValueError("frozen V7 conditional identity/position drift")
        target[sid]=owner
    if len(windows)!=21 or len(target)!=12:
        raise ValueError("frozen V6/V7 windows or target denominator changed")
    return windows,(key,target)


def freeze_tminus1_forecast(
    *,game:int,turn:int,
    predictions:Mapping[int,Mapping[str,Any]],
    v7_target:Mapping[int,int],
)->dict[int,dict[str,Any]]:
    """Does NOT take after-turn records or VCR payload as arguments."""
    if not isinstance(predictions,Mapping):
        raise ValueError("independent T-1 predictions missing")
    out={}
    for sid,entry in sorted(predictions.items()):
        if integer(sid) is None or sid<=0 or not isinstance(entry,Mapping):
            continue
        owner=integer(entry.get("owner_id"))
        raw=entry.get("raw")
        if (owner is None or owner<=0 or integer(entry.get("ship_id"))!=sid
                or not isinstance(raw,Mapping)
                or integer(raw.get("id"))!=sid
                or integer(raw.get("ownerid"))!=owner
                or entry.get("race_id")==12):
            if sid in v7_target:raise ValueError("frozen V7 witness T-1 identity unavailable")
            continue
        source=entry.get("source")
        if source=="normal_mine_route_risk":
            cohort=MINE
            if entry.get("position") is not None:
                raise ValueError("risk-masked T-1 position unexpectedly resolved")
            endpoint=position(entry.get("diagnostic_no_mine_hit_destination"))
            if endpoint is not None and not str(entry.get("diagnostic_no_mine_hit_source","")).startswith("normal_move"):
                raise ValueError("mine no-hit baseline has non-normal source")
        elif isinstance(source,str) and source.startswith("normal_move"):
            cohort=NORMAL
            endpoint=position(entry.get("position"))
        else:
            if sid in v7_target:raise ValueError("frozen V7 risk witness source changed")
            continue
        if sid in v7_target and (cohort!=MINE or v7_target[sid]!=owner):
            raise ValueError("frozen V7 owner/source changed")
        out[sid]={
            "game_id":game,"before_turn":turn-1,"after_turn":turn,
            "ship_id":sid,"Tminus1_owner_id":owner,
            "Tminus1_hull_id":integer(entry.get("hull_id")),
            "Tminus1_source":source,"cohort":cohort,
            "conditional_or_model_endpoint":list(endpoint) if endpoint else None,
            "frozen_v7_witness":sid in v7_target,
            "conditional_no_mine_only":cohort==MINE,
        }
    missing=set(v7_target)-set(out)
    if missing:raise ValueError("frozen V7 witness not present in T-1 predictions")
    return out


def compare_posthost(
    forecast:Mapping[str,Any],
    after_records:Mapping[int,Any],
)->dict[str,Any]:
    """T archive is COMPARATOR ONLY; current physical precombat state unknown."""
    sid=forecast["ship_id"]
    entry=after_records.get(sid)
    if entry is None:
        status="ABSTAIN_T_ARCHIVE_OWNER_CURRENT_UNAVAILABLE"
        after_owner=None;observed=None
    else:
        after_owner,raw=entry
        if (integer(after_owner) is None or after_owner<=0 or
            not isinstance(raw,Mapping)):
            status="ABSTAIN_T_ARCHIVE_OWNER_CURRENT_UNAVAILABLE"
            observed=None
        elif after_owner!=forecast["Tminus1_owner_id"]:
            status="ABSTAIN_OWNER_DRIFT_AT_T"
            observed=None
        elif (integer(forecast.get("Tminus1_hull_id")) is not None and
              integer(raw.get("hullid",raw.get("hull_id"))) != forecast["Tminus1_hull_id"]):
            status="ABSTAIN_HULL_IDENTITY_DRIFT_AT_T"
            observed=None
        else:
            observed=position((raw.get("x"),raw.get("y")))
            if observed is None:
                status="ABSTAIN_T_ARCHIVE_POSITION_UNAVAILABLE"
            else:
                planned=position(forecast.get("conditional_or_model_endpoint"))
                if planned is None:status="ABSTAIN_TMINUS1_NORMAL_ENDPOINT_UNAVAILABLE"
                else:status=("POSTHOST_ENDPOINT_MATCH" if planned==observed
                             else "POSTHOST_ENDPOINT_MISMATCH")
    return {
        **dict(forecast),"T_owner_current_owner_id":after_owner,
        "T_owner_current_position":list(observed) if observed else None,
        "comparison_status":status,
        "precombat_site_membership_proven":False,
        "mine_hit_or_nonhit_proven":False,
        "Nplus1_vcr_used":False,
    }


def owner_current_after_records(snapshots:Any,turn:int)->dict[int,tuple[int|None,Any]]:
    """Only owner-current T records. Never promote stale third-party sighting."""
    ships=group_perspective_records(snapshots,"ship")
    found={}
    for (record_turn,sid),records in sorted(ships.items()):
        if record_turn!=turn:continue
        owner,rec=_owner_record(records)
        found[sid]=(owner,rec.raw if rec is not None else None)
    return found


def build_report(conn:Any,v6:Mapping[str,Any],v7:Mapping[str,Any]):
    windows,target=preselect(v6,v7)
    target_key,target_ships=target
    by_game=defaultdict(dict)
    for (game,turn),sites in windows.items():
        by_game[game][turn]=sites
    comparisons=[]
    context_failures=[]
    population=Counter()
    for ix,(game,turn_sites) in enumerate(sorted(by_game.items()),1):
        print(f"[c5-posthost] [{ix}/{len(by_game)}] G{game} turns={sorted(turn_sites)}",flush=True)
        turns=set(turn_sites)
        contexts={}
        try:
            appearances,_=site_builder._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns=turns)
            site_builder._visit_targeted_site_contexts(
                connection=conn,game_id=game,
                targets={key:() for sites in turn_sites.values() for key in sites},
                appearances=appearances,
                observer=lambda ctx:contexts.__setitem__(
                    (ctx["game_id"],ctx["battle_turn"],ctx["x"],ctx["y"]),ctx),
                collect_pre_mine_counterfactual=True)
        except (ValueError,KeyError,TypeError) as exc:
            context_failures.append({"game_id":game,"phase":"Tminus1",
                                     "reason":f"{type(exc).__name__}:{exc}"})
        forecasts={}
        # Source rows are fixed solely by T-1 estimates. Group multiple
        # factual sites within one game/turn WITHOUT multiplying ships.
        for turn,sites in sorted(turn_sites.items()):
            row=next((contexts[k] for k in sorted(sites) if k in contexts),None)
            target_ids=target_ships if (game,turn)==target_key[:2] else {}
            if row is None:
                context_failures.append({"game_id":game,"turn":turn,
                                         "phase":"Tminus1","reason":"site_context_unavailable"})
                continue
            forecast=freeze_tminus1_forecast(
                game=game,turn=turn,predictions=row["predictions"],
                v7_target=target_ids)
            if target_ids:
                for sid in target_ids:
                    predicted=forecast[sid]
                    if position(predicted["conditional_or_model_endpoint"])!=target_key[2:]:
                        raise ValueError("V7 conditional no-hit site endpoint drift")
            forecasts[turn]=forecast
            population["Tminus1_forecast_rows"]+=len(forecast)
        # Only after ALL game forecasts have been fixed do we collect T
        # archive owner-current comparisons. T is AFTER Host, not precombat.
        try:
            observed=site_builder._targeted_db_context(
                connection=conn,game_id=game,battle_turns=turns)
            snapshots=observed["snapshots"]
        except (ValueError,KeyError,TypeError) as exc:
            context_failures.append({"game_id":game,"phase":"posthost",
                                     "reason":f"{type(exc).__name__}:{exc}"})
            snapshots=None
        for turn,forecast in sorted(forecasts.items()):
            records=owner_current_after_records(snapshots,turn) if snapshots is not None else {}
            for row in forecast.values():
                comparisons.append(compare_posthost(row,records))
    target_rows=[row for row in comparisons if row["frozen_v7_witness"]]
    if len(target_rows)!=12:
        raise ValueError("V7 twelve-witness posthost comparator coverage lost")
    summary_counts=defaultdict(Counter)
    clusters=defaultdict(set)
    examples=defaultdict(list)
    game_summary=defaultdict(lambda:defaultdict(Counter))
    for row in comparisons:
        cohort=row["cohort"];status=row["comparison_status"]
        summary_counts[cohort][status]+=1
        clusters[cohort].add((row["game_id"],row["after_turn"]))
        game_summary[str(row["game_id"])][cohort][status]+=1
        if len(examples[cohort])<12:examples[cohort].append(row)
    for row in target_rows:
        summary_counts["FROZEN_V7_MINE_WITNESSES"][row["comparison_status"]]+=1
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_BLOB,"source_v7_git_blob_sha1":V7_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":DB_SHA256,
        "summary":{
            "frozen_site_census":27,"frozen_adjacent_transitions":63,
            "frozen_game_turn_windows":21,
            "frozen_v7_mine_witnesses":12,
            "Tminus1_forecast_rows":len(comparisons),
            "source_context_failures":len(context_failures),
            "cohort_posthost_comparison_counts":{
                label:dict(sorted(cnt.items())) for label,cnt in sorted(summary_counts.items())},
            "cohort_distinct_game_turn_clusters":{
                label:len(value) for label,value in sorted(clusters.items())},
            "new_host_queue_or_position_predictions":0,
            "precombat_site_membership_proven":False,
            "mine_hits_inferred":0,"Nplus1_VCR_used":False,
        },
        "game_level_counts":{
            g:{cohort:dict(sorted(cnt.items())) for cohort,cnt in sorted(classes.items())}
            for g,classes in sorted(game_summary.items())},
        "frozen_v7_witness_posthost_comparisons":target_rows,
        "cohort_examples":dict(sorted(examples.items())),
        "context_errors":context_failures,
        "boundary":(
            "This retrospective C5-site-selected cohort compares independently "
            "generated T-1 normal-route model endpoints with owner-current "
            "ship coordinates in the T archive AFTER Host processing. It does "
            "NOT observe the precombat position, mine-hit rolls, combat queue, "
            "or physical site arrival. Mines remain a risk; NO_HIT is only a "
            "counterfactual. Owner drift, stale/missing records and incomplete "
            "endpoints are abstentions, never counted as misses or destroyed. "
            "Normal controls are model-based, not proven mine-free. No N+1 VCR "
            "is used to choose comparator ships. Historical first-static-spec "
            "context and source-site selection mean this is NOT holdout validation."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v6",type=Path,required=True)
    p.add_argument("--frozen-v7",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        v6=read_pinned(args.frozen_v6,V6_BLOB)
        v7=read_pinned(args.frozen_v7,V7_BLOB)
        preselect(v6,v7)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 missing")
        print("[c5-posthost] verifying public100 SHA256",flush=True)
        t=time.monotonic()
        with db.open("rb") as f:
            digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=DB_SHA256:raise ValueError("pinned public100 SHA256 changed")
        print(f"[c5-posthost] immutable DB verified in {time.monotonic()-t:.1f}s",flush=True)
        conn,path=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:report=build_report(conn,v6,v7)
        finally:conn.close()
        report["db_path"]=str(path)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(args.output.suffix+".tmp")
        temp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(args.output)
    except (OSError,TypeError,KeyError,ValueError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 POSTHOST ENDPOINT OBSERVATION V8 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
