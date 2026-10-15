"""V17 preregistered, outcome-blind, GAME-DISJOINT Chunnel gate discriminator.

Crucial V16 correction: if the T-1 Firecloud initiator and target
already share coordinates, "at target" is tautological and MUST NOT
count as Chunnel success. Freeze this geometric distinction at T-1.

Use 16 games excluded from all V6/V9/V13/V14 cohorts, selected from
source_members metadata alone. ALL 48 T-1 candidate lists freeze
before reading the first post-Host T archive. One-failed-gate labels
do not prove gate invalidity at later Host execution phase.
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
import combat_c5_chunnel_single_gate_controls_v16 as v16
import combat_c5_chunnel_actor_outcome_audit_v15 as v15
import combat_c5_conditional_chunnel_holdout_v14 as v14
import combat_c5_firecloud_disjoint_validation_v13 as v13
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-disjoint-discriminative-chunnel-gates.v17"
STATUS="TMINUS1_DISJOINT_CHUNNEL_SINGLE_GATE_DISCRIMINATIVE_NOT_ACTIVATION_PROOF"
V6_BLOB=v14.V6_BLOB
V9_BLOB=v14.V9_BLOB
V13_BLOB=v14.V13_BLOB
V14_BLOB=v15.V14_BLOB
V16_BLOB="9b12fde64ca175d3ac29b7135606cf2c73c24119"
GENERATION=v16.GENERATION
SHA256=v16.SHA256
GAMES=16
PAIRS=3


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def point(x:Any)->tuple[int,int]|None:
    return v16.xy(x)


def pinned(path:Path,blob:str)->dict[str,Any]:
    raw=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if digest!=blob:raise ValueError("published source Git blob drift: "+str(path))
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError("published source not JSON object")
    return value


def source_exclusions(v6:Mapping[str,Any],v9report:Mapping[str,Any],
                      v13report:Mapping[str,Any],v14report:Mapping[str,Any],
                      v16report:Mapping[str,Any])->frozenset[int]:
    excluded=set(v14.verify_source(v6,v9report,v13report))
    prior,orig=v15.verify_v14(v14report,frozenset(excluded))
    if len(orig)!=60:raise ValueError("V14 fixed 60 windows changed")
    excluded.update(g for g,_ in prior)
    if (v16report.get("schema")!=v16.SCHEMA or
        v16report.get("status")!=v16.STATUS or
        v16report.get("source_v15_git_blob_sha1")!=v16.V15_BLOB or
        v16report.get("source_db_sha256")!=SHA256):
        raise ValueError("V16 source provenance changed")
    summary=v16report.get("summary")
    wanted={
        "fixed_V14_windows":60,"fixed_V14_games":20,
        "frozen_original_V15_positive_actor_edges":95,
        "Tminus1_single_failed_gate_candidates":27,
        "all_forecasts_frozen_before_T":True,
        "future_VCR_used":False,"Host_Chunnel_activation_proven":False,
        "new_canonical_movement_or_combat_predictions":0,
    }
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in wanted.items()):
        raise ValueError("V16 frozen comparison changed")
    rows=v16report.get("negative_single_failed_gate_cases")
    if not isinstance(rows,list) or len(rows)!=27:
        raise ValueError("V16 27 negative cases missing")
    collocated=[r for r in rows if
                r.get("single_failing_gate")=="DISTANCE_BELOW_100_AT_TMINUS1" and
                point(r.get("source"))==point(r.get("target"))]
    if len(collocated)!=14:raise ValueError("V16 zero-distance guard source changed")
    if len(excluded)!=57:
        raise ValueError("expected distinct C5/V9/V13/V14 source games changed")
    return frozenset(excluded)


def freeze_pre_window(conn:Any,game:int,turn:int):
    snaps,_=v9.pre_snapshots(conn,game=game,before=turn-1)
    roster=_owner_rows_for_turn(group_perspective_records(snaps,"ship"),turn-1)
    candidates,reasons=v16.potential_stock_edges(roster)
    seen=set()
    edges=[]
    for e in candidates:
        key=(e["initiator_ship_id"],e["target_ship_id"])
        src,dst=point(e["source"]),point(e["target"])
        if (key in seen or src is None or dst is None or
            e.get("actual_Chunnel_activation_proven") is not False or
            e.get("cohort") not in ("ALL_TMINUS1_GATES_PASS","ONE_TMINUS1_GATE_FAILS")):
            raise ValueError("Tminus1 candidate identity/control drift")
        seen.add(key)
        discriminative=src!=dst
        if not discriminative and (e["single_failing_gate"]!="DISTANCE_BELOW_100_AT_TMINUS1" or
                                   e["cohort"]!="ONE_TMINUS1_GATE_FAILS"):
            raise ValueError("Tminus1 zero-distance mislabeled positive")
        edges.append({
            **e,
            "game_id":game,"turn":turn,
            "Tminus1_source_differs_from_target":discriminative,
            "Tminus1_scoring_population":(
                "DISCRIMINATIVE" if discriminative else
                "NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"),
            "T_outcome_not_used_to_choose_or_score_populations":True,
        })
    return {
        "game_id":game,"turn":turn,
        "Tminus1_candidate_edges":edges,
        "Tminus1_absence_and_gate_counts":reasons,
        "Tminus1_all_selected_before_T":True,
    }


def compare_one(edge:Mapping[str,Any],after:Mapping[int,Any])->dict[str,Any]:
    """Never turn coincident T-1 endpoints into a positive Chunnel case."""
    owner=edge["owner_id"]
    actor,receiver=edge["initiator_ship_id"],edge["target_ship_id"]
    actor_state,a=v16.v15.get_observation(after,actor,owner)
    target_state,t=v16.v15.get_observation(after,receiver,owner)
    source,dest=point(edge["source"]),point(edge["target"])
    apos=point((a.get("x"),a.get("y"))) if a is not None else None
    tpos=point((t.get("x"),t.get("y"))) if t is not None else None
    informative=edge["Tminus1_source_differs_from_target"]
    if not informative:
        status="NON_DISCRIMINATIVE_SOURCE_EQUALS_TARGET"
    elif a is None:
        status=actor_state
    elif apos==dest:
        status="T_ACTOR_AT_DISTINCT_FROZEN_TARGET"
    elif apos==source:
        status="T_ACTOR_AT_FROZEN_SOURCE"
    else:
        status="T_ACTOR_ELSEWHERE"
    fuel=integer(a.get("neutronium")) if a is not None else None
    delta=edge["actor_Tminus1_fuel"]-fuel if fuel is not None else None
    return {
        **edge,
        "T_actor_status":status,
        "T_actor_owner_current_status":actor_state,
        "T_target_owner_current_status":target_state,
        "T_actor_position":list(apos) if apos is not None else None,
        "T_target_position":list(tpos) if tpos is not None else None,
        "T_target_at_Tminus1_target":tpos==dest if tpos is not None else None,
        "T_actor_net_fuel_delta_KT":delta,
        "T_actor_net_fuel_delta_50KT":delta==50 if delta is not None else None,
        "T_coincident_actor_target_never_counted_as_positive":not informative,
        "Host_Chunnel_activation_or_inactivation_proven":False,
        "Nplus1_VCR_used":False,
    }


def build_report(conn:Any,v6:Mapping[str,Any],v9report:Mapping[str,Any],
                 v13report:Mapping[str,Any],v14report:Mapping[str,Any],
                 v16report:Mapping[str,Any]):
    excluded=source_exclusions(v6,v9report,v13report,v14report,v16report)
    # Metadata-only; these are NOT a new independently collected corpus.
    metadata=conn.execute(
        "SELECT DISTINCT game_id,archive_turn FROM source_members ORDER BY game_id,archive_turn"
    ).fetchall()
    selected=v13.choose_windows(metadata,excluded,game_count=GAMES)
    if len(selected)!=GAMES*PAIRS or len({g for g,_ in selected})!=GAMES:
        raise ValueError("V17 16 game x 3 metadata selection incomplete")
    print("[c5-v17] locked metadata-only game-turn windows:",selected,flush=True)
    frozen={}
    errors=[]
    for idx,(g,t) in enumerate(selected,1):
        print(f"[c5-v17] PRE [{idx}/{len(selected)}] G{g} T{t}",flush=True)
        try:frozen[g,t]=freeze_pre_window(conn,g,t)
        except (ValueError,TypeError,KeyError) as exc:
            errors.append({"game_id":g,"turn":t,"phase":"PRE",
                           "status":"ABSTAIN_TMINUS1_CONTEXT",
                           "reason":f"{type(exc).__name__}:{exc}"})
            frozen[g,t]=None
    # STRICT PHASE BARRIER: the first T archive read is below this line.
    compared=[]
    for idx,(g,t) in enumerate(selected,1):
        print(f"[c5-v17] POST [{idx}/{len(selected)}] G{g} T{t}",flush=True)
        if frozen[g,t] is None:continue
        try:
            after=v9.after_owner_current(conn,game=g,turn=t)
            compared.append({
                "game_id":g,"turn":t,
                "Tminus1_rejection_and_abstain_counts":frozen[g,t]["Tminus1_absence_and_gate_counts"],
                "edges":[compare_one(e,after) for e in frozen[g,t]["Tminus1_candidate_edges"]],
                "Tminus1_selected_before_all_T_observations":True,
            })
        except (ValueError,TypeError,KeyError) as exc:
            errors.append({"game_id":g,"turn":t,"phase":"POST",
                           "status":"ABSTAIN_T_ARCHIVE",
                           "reason":f"{type(exc).__name__}:{exc}"})
    if len(compared)<8:raise ValueError("insufficient V17 windows to report")
    flat=[e for w in compared for e in w["edges"]]
    groups=defaultdict(Counter)
    bygame=defaultdict(Counter)
    from_gate=Counter()
    for r in flat:
        from_gate[r["cohort"]]+=1
        gate=r["single_failing_gate"] or "ALL_GATES_PASS"
        groups[gate][r["T_actor_status"]]+=1
        bygame[str(r["game_id"])][gate]+=1
    discriminative=[e for e in flat if e["Tminus1_source_differs_from_target"]]
    coincident=[e for e in flat if not e["Tminus1_source_differs_from_target"]]
    neg=[e for e in discriminative if e["cohort"]=="ONE_TMINUS1_GATE_FAILS"]
    pos=[e for e in discriminative if e["cohort"]=="ALL_TMINUS1_GATES_PASS"]
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v6_git_blob_sha1":V6_BLOB,
        "source_v9_git_blob_sha1":V9_BLOB,
        "source_v13_git_blob_sha1":V13_BLOB,
        "source_v14_git_blob_sha1":V14_BLOB,
        "source_v16_git_blob_sha1":V16_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "frozen_selection":{
            "game_turns":[{"game_id":g,"turn":t} for g,t in selected],
            "excluded_V6_V9_V13_V14_game_ids":sorted(excluded),
            "protocol":"16 site/validation-disjoint games x 3 metadata-selected windows",
            "game_overlap_with_previous_studies":len({g for g,_ in selected}&excluded),
            "no_ship_outcomes_or_VCR_in_selection":True,
        },
        "summary":{
            "selected_game_count":GAMES,"selected_window_count":len(selected),
            "evaluated_windows":len(compared),"context_abstentions":len(errors),
            "candidate_stock_firecloud_edges":len(flat),
            "candidate_cohorts":dict(sorted(from_gate.items())),
            "discriminative_positive_Tminus1_edges":len(pos),
            "discriminative_single_failed_Tminus1_edges":len(neg),
            "non_discriminative_colocated_Tminus1_edges":len(coincident),
            "discriminative_positive_posthost_counts":dict(sorted(Counter(
                x["T_actor_status"] for x in pos).items())),
            "discriminative_negative_posthost_counts":dict(sorted(Counter(
                x["T_actor_status"] for x in neg).items())),
            "single_gate_posthost_counts":{
                g:dict(sorted(v.items())) for g,v in sorted(groups.items())},
            "negative_game_turn_clusters":len({(x["game_id"],x["turn"]) for x in neg}),
            "positive_game_turn_clusters":len({(x["game_id"],x["turn"]) for x in pos}),
            "positive_distinct_games":len({x["game_id"] for x in pos}),
            "negative_distinct_games":len({x["game_id"] for x in neg}),
            "Tminus1_all_windows_frozen_before_T":True,
            "new_Host_movement_or_combat_predictions_promoted":0,
            "Chunnel_activation_proven":False,
            "Nplus1_VCR_used":False,"independent_new_corpus":False,
        },
        "by_game_candidate_counts":{g:dict(sorted(v.items())) for g,v in sorted(bygame.items())},
        "windows":compared,"window_errors":errors,
        "boundary":(
            "Official Chunnel requires at least 100 LY. V16 erroneously "
            "counted 14 actor-at-target short-distance results that had "
            "identical Tminus1 source and target as if discriminatory; "
            "V17 declares coincident points NON_DISCRIMINATIVE at Tminus1, "
            "without using T outcomes. Exclude all prior V6/V9/V13/V14 "
            "game IDs, select 16 new games by source_members metadata only, "
            "freeze all 48 Tminus1 comparisons before any T archive reads. "
            "Single-gate tests at Tminus1 are not necessarily the actual "
            "conditions at the later Chunnel Host phase; Tow request is "
            "not evidence a tow locked. Owner-current T is posthost "
            "observational only; actor at target, source, elsewhere or "
            "fuel delta of 50KT cannot prove execution/inactivation. "
            "Custom hull abilities and ambiguous target suffixes "
            "are outside the stock, unambiguous scope. "
            "No new canonical movement/queue rules or Nplus1 VCR."
        ),
    }


def main()->int:
    a=argparse.ArgumentParser()
    for k in ("frozen-v6","frozen-v9","frozen-v13","frozen-v14",
              "frozen-v16","corpus-db-root","output"):
        a.add_argument("--"+k,type=Path,required=True)
    o=a.parse_args()
    try:
        v6=pinned(o.frozen_v6,V6_BLOB)
        v9report=pinned(o.frozen_v9,V9_BLOB)
        v13report=pinned(o.frozen_v13,V13_BLOB)
        v14report=pinned(o.frozen_v14,V14_BLOB)
        v16report=pinned(o.frozen_v16,V16_BLOB)
        source_exclusions(v6,v9report,v13report,v14report,v16report)
        db=o.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 corpus missing")
        print("[c5-v17] checking immutable public100 SHA256",flush=True)
        t=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("public100 SHA256 drift")
        print(f"[c5-v17] checked in {time.monotonic()-t:.1f}s; read-only",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,o.corpus_db_root)
        try:report=build_report(conn,v6,v9report,v13report,v14report,v16report)
        finally:conn.close()
        o.output.parent.mkdir(parents=True,exist_ok=True)
        temp=o.output.with_suffix(o.output.suffix+".tmp")
        temp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        temp.replace(o.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as err:
        print("ERROR:",err,file=sys.stderr)
        return 2
    print("===== C5 DISJOINT DISCRIMINATIVE CHUNNEL GATES V17 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",o.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
