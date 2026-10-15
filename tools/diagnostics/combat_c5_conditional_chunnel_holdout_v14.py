"""V14: T-1-frozen CONDITIONAL Chunnel vs normal baseline, V13-game-disjoint.

The conditional Firecloud endpoint is NOT a prediction that Host will
activate Chunnel. The outcome T is post-Host; effect labels are observational.
All pre-Host cases selected before consulting ANY T owner-current archive.
Refuse multiple candidate Chunnel destinations for the same ship.
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
for p in (ROOT/"src", Path(__file__).resolve().parent):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-conditional-chunnel-holdout.v14"
STATUS="GAME_DISJOINT_PREOUTCOME_CHUNNEL_CONDITIONAL_VS_NORMAL_BASELINE"
V6_BLOB=v13.V6_BLOB
V9_BLOB=v13.V9_BLOB
V13_BLOB="29309650f770b60dab2ec9aaedba3bcbbb652982"
GENERATION=v13.GENERATION
SHA256=v13.SHA256
GAME_COUNT=20
WINDOWS_PER_GAME=3
NORMAL=v9.NORMAL
MINE=v9.MINE


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def point(v:Any)->tuple[int,int]|None:
    return v13.coordinate(v)


def verify_source(v6:Mapping[str,Any],v9report:Mapping[str,Any],v13report:Mapping[str,Any]):
    excluded=set(v13.excluded_games(v6,v9report))
    if (v13report.get("schema")!=v13.SCHEMA or
        v13report.get("status")!=v13.STATUS or
        v13report.get("source_v6_git_blob_sha1")!=V6_BLOB or
        v13report.get("source_v9_git_blob_sha1")!=V9_BLOB or
        v13report.get("source_db_sha256")!=SHA256):
        raise ValueError("pinned V13 provenance changed")
    s=v13report.get("summary")
    expected={
        "selected_game_count":12,"selected_window_count":36,
        "game_overlap_with_V6_and_V9":0,
        "pre_or_post_context_errors":0,
        "post_context_evaluated_windows":36,
        "Tminus1_stock_firecloud_edges":52,
        "Tminus1_candidate_passenger_appearances":28,
        "new_Host_position_or_combat_predictions_promoted":0,
        "Nplus1_VCR_used":False,
        "Chunnel_execution_proven":False,
        "independent_new_corpus":False,
    }
    if not isinstance(s,Mapping) or any(s.get(k)!=v for k,v in expected.items()):
        raise ValueError("frozen V13 validation summary changed")
    m=v13report.get("source_metadata_selection")
    if not isinstance(m,Mapping) or m.get("no_posthost_T_or_VCR_in_selection") is not True:
        raise ValueError("V13 was not metadata-selected")
    selected=m.get("selected_windows")
    if not isinstance(selected,list) or len(selected)!=36:
        raise ValueError("V13 source windows unavailable")
    windows=set()
    games=set()
    for w in selected:
        if not isinstance(w,Mapping):raise ValueError("V13 window malformed")
        g,t=integer(w.get("game_id")),integer(w.get("turn"))
        if None in (g,t) or g<=0 or t<2 or (g,t) in windows or g in excluded:
            raise ValueError("V13 game/window overlap or duplicate")
        windows.add((g,t));games.add(g)
    if len(games)!=12:raise ValueError("V13 games not distinct")
    return frozenset(excluded|games)


def freeze_conditional_cases(pre:Mapping[str,Any]):
    """No T archive accepted; treat candidate edges as conditional hypotheses."""
    window=(pre.get("game_id"),pre.get("turn"))
    if (pre.get("status")!="TMINUS1_PREOUTCOME_FROZEN" or
        not all(integer(v) is not None for v in window) or
        pre.get("T_archive_not_read_for_selection") is not True):
        raise ValueError("Tminus1 pre-outcome feature freeze missing")
    edges=pre.get("Tminus1_Firecloud_source_target_edges")
    controls=pre.get("Tminus1_negative_normal_controls")
    if not isinstance(edges,list) or not isinstance(controls,list):
        raise ValueError("frozen Firecloud source candidate/control list unavailable")
    candidates=defaultdict(list)
    keys=set()
    for e in edges:
        if not isinstance(e,Mapping):raise ValueError("preoutcome edge malformed")
        initiator,target,owner=[integer(e.get(k)) for k in
            ("initiator_ship_id","target_ship_id","owner_id")]
        source,dest=point(e.get("initiator_Tminus1_source")),point(e.get("target_Tminus1_destination"))
        key=(initiator,target,owner)
        if (None in key or min(key)<=0 or key in keys or source is None or dest is None
            or source==dest or e.get("execution_proven") is not False
            or e.get("stock_hulls_verified_from_Tminus1") is not True
            or e.get("initiator_Tminus1_warp")!=0):
            raise ValueError("Tminus1 conditional source graph invalid")
        keys.add(key)
        rows=e.get("Tminus1_passenger_candidates")
        if not isinstance(rows,list):raise ValueError("source prepassenger list unavailable")
        for p in rows:
            if not isinstance(p,Mapping):raise ValueError("prepassenger malformed")
            sid=integer(p.get("ship_id"))
            powner=integer(p.get("Tminus1_owner_id"))
            phull=integer(p.get("Tminus1_hull_id"))
            baseline=point(p.get("Tminus1_model_prechunnel_endpoint"))
            planned=point(p.get("Tminus1_predicted_transport_destination"))
            if (sid is None or sid<=0 or powner!=owner or
                phull is None or phull<=0 or baseline!=source or
                planned!=dest or p.get("Tminus1_inferred_actual_arrival") is not False or
                p.get("Tminus1_model_cohort") not in (NORMAL,MINE) or
                p.get("conditional_on_no_mine_interference") !=
                    (p.get("Tminus1_model_cohort")==MINE)):
                raise ValueError("invalid Tminus1 passenger identity/route")
            candidates[sid].append({
                "ship_id":sid,"owner_id":owner,"hull_id":phull,
                "initiator_ship_id":initiator,"target_ship_id":target,
                "game_id":window[0],"turn":window[1],
                "cohort":p["Tminus1_model_cohort"],
                "normal_no_chunnel_baseline":list(source),
                "conditional_chunnel_endpoint":list(dest),
                "mine_exposure_requires_no_hit_assumption":p["conditional_on_no_mine_interference"],
                "activation_proven":False,
            })
    ambiguity=set()
    frozen=[]
    for sid,rows in sorted(candidates.items()):
        if len(rows)>1:
            ambiguity.add(sid)
            continue
        frozen.extend(rows)
    seen_control=set()
    for c in controls:
        sid=integer(c.get("ship_id")) if isinstance(c,Mapping) else None
        if (sid is None or sid<=0 or sid in seen_control or sid in candidates
            or point(c.get("Tminus1_model_endpoint")) is None):
            raise ValueError("invalid/duplicate Tminus1 negative control")
        seen_control.add(sid)
    return {
        "game_id":window[0],"turn":window[1],
        "preoutcome_eligible_edges":len(edges),
        "preoutcome_unambiguous_passenger_cases":frozen,
        "preoutcome_ambiguous_passenger_ids":sorted(ambiguity),
        "preoutcome_nonexposed_negative_controls":controls,
        "all_candidates_selected_without_T":True,
    }


def post_compare(frozen:Mapping[str,Any],actual:Mapping[int,Any]):
    """Score a *conditional* transport target vs no-transport normal baseline."""
    rows=[]
    for case in frozen["preoutcome_unambiguous_passenger_cases"]:
        sid,owner,hull=case["ship_id"],case["owner_id"],case["hull_id"]
        state,raw=v13._current_ship(actual,sid,owner,hull)
        observed=point((raw.get("x"),raw.get("y"))) if raw is not None else None
        dst=point(case["conditional_chunnel_endpoint"])
        baseline=point(case["normal_no_chunnel_baseline"])
        if raw is None:outcome=state
        elif observed==dst:outcome="T_MATCHES_CONDITIONAL_CHUNNEL_ONLY"
        elif observed==baseline:outcome="T_MATCHES_NORMAL_BASELINE_ONLY"
        else:outcome="T_MATCHES_NEITHER_BASELINE"
        rows.append({
            **case,
            "T_owner_current_position":list(observed) if observed is not None else None,
            "T_conditional_chunnel_match":observed==dst if observed is not None else None,
            "T_normal_baseline_match":observed==baseline if observed is not None else None,
            "T_observation_status":outcome,
            "Chunnel_execution_proven":False,
        })
    controls=[]
    for control in frozen["preoutcome_nonexposed_negative_controls"]:
        sid,owner,hull=[control.get(k) for k in
            ("ship_id","Tminus1_owner_id","Tminus1_hull_id")]
        state,raw=v13._current_ship(actual,sid,owner,hull)
        observed=point((raw.get("x"),raw.get("y"))) if raw is not None else None
        baseline=point(control["Tminus1_model_endpoint"])
        controls.append({
            "ship_id":sid,"status":state,
            "T_normal_control_baseline_match":observed==baseline if observed is not None else None,
        })
    return {
        "game_id":frozen["game_id"],"turn":frozen["turn"],
        "preoutcome_eligible_edges":frozen["preoutcome_eligible_edges"],
        "preoutcome_ambiguous_passenger_ids":frozen["preoutcome_ambiguous_passenger_ids"],
        "T_conditional_passenger_comparisons":rows,
        "T_nonexposed_normal_control_comparisons":controls,
        "no_VCR_or_T_used_to_select_cases":True,
    }


def build_report(conn:Any,v6:Mapping[str,Any],v9report:Mapping[str,Any],v13report:Mapping[str,Any]):
    excluded=verify_source(v6,v9report,v13report)
    metadata=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    selected=v13.choose_windows(metadata,excluded,game_count=GAME_COUNT)
    if (len(selected)!=GAME_COUNT*WINDOWS_PER_GAME or
        len({g for g,_ in selected})!=GAME_COUNT or
        any(g in excluded for g,_ in selected)):
        raise ValueError("heldout V14 metadata cohort protocol changed")
    print("[c5-v14] frozen metadata-only game-turn cohort:",selected,flush=True)
    pre={}
    errors=[]
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-v14] PRE [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        try:
            snaps,raws=v9.pre_snapshots(conn,game=game,before=turn-1)
            features=v13.freeze_window(game,turn,snaps,raws)
            pre[game,turn]=freeze_conditional_cases(features)
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"Tminus1",
                           "status":"ABSTAIN_PRE_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
            pre[game,turn]=None
    # CRITICAL CAUSAL BARRIER: absolutely no post-T archive read above.
    records=[]
    for i,(game,turn) in enumerate(selected,1):
        print(f"[c5-v14] POST [{i}/{len(selected)}] G{game} T{turn}",flush=True)
        if pre[game,turn] is None:continue
        try:
            actual=v9.after_owner_current(conn,game=game,turn=turn)
            records.append(post_compare(pre[game,turn],actual))
        except (ValueError,TypeError,KeyError) as exc:
            errors.append({"game_id":game,"turn":turn,"phase":"posthost",
                           "status":"ABSTAIN_POST_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
    if len(records)<6:raise ValueError("insufficient completed post-T windows")
    rows=[p for w in records for p in w["T_conditional_passenger_comparisons"]]
    negatives=[c for w in records for c in w["T_nonexposed_normal_control_comparisons"]]
    count=Counter(r["T_observation_status"] for r in rows)
    by_cohort=defaultdict(Counter)
    by_game=defaultdict(Counter)
    exposed={(w["game_id"],w["turn"]) for w in records if w["T_conditional_passenger_comparisons"]}
    for row in rows:
        by_cohort[row["cohort"]][row["T_observation_status"]]+=1
        by_game[str(row["game_id"])][row["T_observation_status"]]+=1
    negcounts=Counter("MATCH" if c["T_normal_control_baseline_match"] is True
        else "MISMATCH" if c["T_normal_control_baseline_match"] is False else
        c["status"] for c in negatives)
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_BLOB,"source_v9_git_blob_sha1":V9_BLOB,
        "source_v13_git_blob_sha1":V13_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "frozen_selection":{
            "protocol":"20 games x 3 adjacent windows, metadata only, exclude entire V6/V9/V13 game sets",
            "excluded_game_ids":sorted(excluded),
            "selected_game_turns":[{"game_id":g,"turn":t} for g,t in selected],
            "no_VCR_or_T_outcome_selection":True,
        },
        "summary":{
            "selected_game_count":GAME_COUNT,"selected_window_count":len(selected),
            "V6_V9_V13_game_overlap":len({g for g,_ in selected}&excluded),
            "completed_windows":len(records),"context_abstentions":len(errors),
            "eligible_Tminus1_Firecloud_edges_in_completed_windows":
                sum(w["preoutcome_eligible_edges"] for w in records),
            "frozen_unambiguous_candidate_passengers":len(rows),
            "ambiguous_passenger_exclusions":sum(
                len(w["preoutcome_ambiguous_passenger_ids"]) for w in records),
            "passenger_exposure_game_turns":len(exposed),
            "passenger_exposure_distinct_games":len({g for g,_ in exposed}),
            "T_passenger_conditional_vs_baseline_counts":dict(sorted(count.items())),
            "T_passenger_counts_by_Tminus1_mine_risk":{
                k:dict(sorted(v.items())) for k,v in sorted(by_cohort.items())},
            "T_negative_normal_control_counts":dict(sorted(negcounts.items())),
            "new_production_Host_movement_or_combat_predictions":0,
            "Chunnel_execution_independently_proven":False,
            "Nplus1_VCR_used":False,"new_independent_corpus":False,
        },
        "by_game_counts":{k:dict(sorted(v.items())) for k,v in sorted(by_game.items())},
        "window_evaluations":records,
        "window_errors":errors,
        "boundary":(
            "Conditional inference only: a valid Tminus1 conventional stock "
            "Firecloud pair does NOT guarantee execution, and Tminus1 pre-move "
            "normal endpoints (especially mine-risk cases) do NOT prove arrival. "
            "The model emits both a hypothetical Chunnel destination and a "
            "no-Chunnel normal endpoint BEFORE reading any T observation. "
            "All candidate game IDs are excluded from earlier V6, V9, V13 "
            "research and chosen using archival metadata only. Missing, owner "
            "or hull drift, duplicate eligible Firecloud sources and any "
            "post-T interruptions abstain. After-Host T matching does not "
            "isolate the Chunnel phase or rule out other movement and fuel "
            "operations. No production executor changes or N+1 VCR comparisons. "
            "Same public100 corpus is NOT a freshly collected independent dataset."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    for flag in ("frozen-v6","frozen-v9","frozen-v13","corpus-db-root","output"):
        parser.add_argument("--"+flag,type=Path,required=True)
    args=parser.parse_args()
    try:
        v6=v13.pinned_json(args.frozen_v6,V6_BLOB)
        v9report=v13.pinned_json(args.frozen_v9,V9_BLOB)
        v13report=v13.pinned_json(args.frozen_v13,V13_BLOB)
        verify_source(v6,v9report,v13report)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 missing")
        print("[c5-v14] verifying read-only public100 SHA256 once",flush=True)
        started=time.monotonic()
        with db.open("rb") as fd:digest=hashlib.file_digest(fd,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 checksum drift")
        print(f"[c5-v14] verified in {time.monotonic()-started:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:result=build_report(conn,v6,v9report,v13report)
        finally:conn.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(args.output.suffix+".tmp")
        temp.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(args.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== CONDITIONAL CHUNNEL VS NORMAL HELDOUT V14 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
