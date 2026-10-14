"""Pre-registered public100 ordinary C5 multi-battle-site coverage gate.

Broad site/queue CASE DISCOVERY, not a combat encounter predictor.
Selection of games/turns uses only archive VCR-existence metadata with adjacent
T-1 archive availability; all VCR payloads are read strictly AFTER selection.
No selection on VCR result, mass, captured prize, success or residual. Every
selected window is reported, including zero in-scope sites.

Horwasp/race12 and malformed cases are kept as explicitly OUT-OF-SCOPE, not
counted as solved ordinary cases. Does not touch production or corpus CURRENT.
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
if str(ROOT/"src") not in sys.path:sys.path.insert(0,str(ROOT/"src"))
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only, member_refs_for_turns, reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA="planets-lab.combat-c5-public100-site-coverage.v1"
STATUS="PRESELECTED_ORDINARY_C5_SITE_CENSUS_NOT_A_QUEUE_PREDICTION"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SHA256="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DEFAULT_GAMES=48
MIN_TURNS=6
MIN_SPAN=20


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def info(s:str)->None:
    print("[c5-coverage] "+s,flush=True)


def candidate_metadata(conn:Any)->list[tuple[int,int]]:
    rows=conn.execute("""
    WITH archive_turns AS (
        SELECT DISTINCT game_id,archive_turn FROM source_members
    ), archived_vcr_turns AS (
        SELECT DISTINCT sm.game_id,sm.archive_turn
        FROM typed_vcrs AS v JOIN source_members AS sm USING(member_id)
    )
    SELECT v.game_id,v.archive_turn FROM archived_vcr_turns AS v
    JOIN archive_turns AS prev
        ON prev.game_id=v.game_id AND prev.archive_turn=v.archive_turn-1
    WHERE v.archive_turn>=1
    ORDER BY v.game_id,v.archive_turn
    """).fetchall()
    return [(int(g),int(t)) for g,t in rows]


def evenly_spaced(sorted_items:Sequence[int],max_count:int)->list[int]:
    if max_count<=0:raise ValueError("max_games must be positive")
    if len(sorted_items)<=max_count:return list(sorted_items)
    if max_count==1:return [sorted_items[0]]
    return [sorted_items[i*(len(sorted_items)-1)//(max_count-1)]
            for i in range(max_count)]


def freeze_windows(
    pairs:Sequence[tuple[int,int]],*,max_games:int=DEFAULT_GAMES,
)->tuple[list[dict[str,Any]],dict[str,Any]]:
    """Entire selection before looking at ANY VCR body; no excluded history."""
    by_game:dict[int,set[int]]=defaultdict(set)
    for game,turn in pairs:
        if (integer(game) is None or integer(turn) is None or
            game<=0 or turn<1):
            raise ValueError("malformed archive metadata")
        by_game[game].add(turn)
    eligible={game:sorted(turns) for game,turns in by_game.items()
              if len(turns)>=MIN_TURNS and
              max(turns)-min(turns)>=MIN_SPAN}
    selected=evenly_spaced(sorted(eligible),max_games)
    result=[]
    for g in selected:
        turns=eligible[g]
        for cohort,ix in (
            ("EARLY_QUINTILE",(len(turns)-1)//5),
            ("LATE_85TH_PERCENTILE",85*(len(turns)-1)//100),
        ):
            result.append({"game_id":g,"turn":turns[ix],"cohort":cohort,
                           "eligible_archived_turns":len(turns)})
    return result,{
        "eligible_games":len(eligible),"selected_games":selected,
        "selected_game_count":len(selected),
        "preselected_window_count":len(result),
        "selection_inputs":"source_members archive turns + typed_vcrs existence only",
        "selection_formula":"every game with >=6 consecutive-Tminus1 VCR-bearing archive turns and >=20 turn span; sorted game-ID even quantiles; each game 20th and 85th percentiles",
        "no_current_vcr_body_or_result_used":True,
    }


def classify_vcr(payload:Mapping[str,Any])->str:
    left,right=payload.get("left"),payload.get("right")
    if not isinstance(left,Mapping) or not isinstance(right,Mapping):
        return "ABSTAIN_MALFORMED_VCR_PARTICIPANTS"
    lo,ro=integer(payload.get("leftownerid")),integer(payload.get("rightownerid"))
    lh,rh=integer(left.get("hullid")),integer(right.get("hullid"))
    if lo is None or lo<=0 or lh is None or lh<=0:
        return "ABSTAIN_INVALID_LEFT_SHIP_IDENTITY"
    if integer(left.get("raceid"))==12 or integer(right.get("raceid"))==12:
        return "OUT_OF_SCOPE_HORWASP_RACE12"
    if rh is not None and rh>0:
        if ro is None or ro<=0:
            return "ABSTAIN_INVALID_RIGHT_SHIP_OWNER"
        return "ORDINARY_SHIP_VS_SHIP"
    if rh in (0,None):
        return "ORDINARY_SHIP_VS_PLANET_CANDIDATE"
    return "ABSTAIN_UNKNOWN_VCR_SHAPE"


def identity(payload:Mapping[str,Any],side:str)->tuple[int,int]|None:
    row=payload.get(side)
    owner=integer(payload.get(side+"ownerid"))
    ship=integer(row.get("objectid")) if isinstance(row,Mapping) else None
    if owner is None or owner<=0 or ship is None or ship<=0:return None
    return owner,ship


def site_population(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    """All VCRs preselected; observational site geometry and repeat-shapes."""
    site_map:dict[tuple[int,int],list[Mapping[str,Any]]]=defaultdict(list)
    unlocatable=[]
    for r in rows:
        x,y=integer(r["payload"].get("x")),integer(r["payload"].get("y"))
        if x is None or y is None:
            unlocatable.append(r["vcr_id"])
        else:site_map[(x,y)].append(r)
    sites=[]
    for (x,y),vcrs in sorted(site_map.items()):
        ordered=sorted(vcrs,key=lambda r:r["vcr_id"])
        ids=[r["vcr_id"] for r in ordered]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate VCR identity at site")
        types=Counter(r["shape"] for r in ordered)
        ship_rows=[r for r in ordered if r["shape"]=="ORDINARY_SHIP_VS_SHIP"]
        appearances:dict[tuple[int,int],list[int]]=defaultdict(list)
        for r in ship_rows:
            for side in ("left","right"):
                pair=identity(r["payload"],side)
                if pair is not None:appearances[pair].append(r["vcr_id"])
        repeated={f"{owner}:{sid}":vids
                  for (owner,sid),vids in sorted(appearances.items())
                  if len(vids)>=2}
        vcr_ids=[r["vcr_id"] for r in ship_rows]
        # A contiguous VCR-ID run is a purely descriptive opportunity:
        # it does not prove Host execution ordering or terminal carry.
        adjacent=sum(b==a+1 for a,b in zip(vcr_ids,vcr_ids[1:]))
        eligible=(len(ship_rows)>=2 and
                  all(r["shape"]=="ORDINARY_SHIP_VS_SHIP" for r in ordered))
        category=("ORDINARY_SHIP_ONLY_MULTIVCR_SITE" if eligible else
            "OUT_OF_SCOPE_HORWASP_SITE" if types["OUT_OF_SCOPE_HORWASP_RACE12"] else
            "ORDINARY_MIXED_SHIP_PLANET_SITE" if (types["ORDINARY_SHIP_VS_SHIP"]>0
              and types["ORDINARY_SHIP_VS_PLANET_CANDIDATE"]>0) else
            "SITE_NOT_BOUNDED_ORDINARY_SHIP_ONLY_MULTIVCR")
        sites.append({
            "x":x,"y":y,"category":category,
            "all_vcr_ids":[r["vcr_id"] for r in ordered],
            "ordinary_ship_vcr_ids":vcr_ids,
            "shape_counts":dict(sorted(types.items())),
            "observed_ship_VCR_ID_adjacent_pairs":adjacent,
            "repeated_same_owner_ship_by_VCR_ID":repeated,
            "candidate_multi_ship_site":eligible,
            "queue_pairs_predicted":0,
            "Host_combat_order_proven":False,
        })
    return {"sites":sites,"unlocatable_vcr_ids":unlocatable}


def tminus1_owner_coverage(
    conn:Any,*,game:int,turn:int,ships:Sequence[tuple[int,int]],
)->dict[str,Any]:
    """T-1 owner records are prestate; ship identities are VCR targets."""
    refs=member_refs_for_turns(
        conn,game_id=game,turns={turn-1},include_embedded_turn=False
    )
    hist=list(reconstruct_members(conn,refs))
    by_owner:dict[int,list[tuple[Any,Any]]]=defaultdict(list)
    for ref,member in hist:
        if (ref.game_id!=game or ref.archive_turn!=turn-1 or
            ref.embedded_turn!=turn-1 or
            not isinstance(member,Mapping) or
            not isinstance(member.get("game"),Mapping) or
            integer(member["game"].get("id"))!=game or
            integer(member["game"].get("turn"))!=turn-1):
            raise ValueError("T-1 archive provenance drift")
        by_owner[ref.perspective_player_id].append((ref,member))
    counts=Counter()
    details=[]
    for owner,sid in sorted(set(ships)):
        perspectives=by_owner.get(owner,[])
        if not perspectives:
            status="ABSTAIN_NO_TMINUS1_OWNER_PERSPECTIVE"
        else:
            observed=[]
            for ref,member in perspectives:
                raw=member.get("ships")
                if not isinstance(raw,list):
                    observed.append(None)
                    continue
                matching=[s for s in raw if
                          isinstance(s,Mapping) and
                          integer(s.get("id"))==sid and
                          integer(s.get("ownerid"))==owner]
                if len(matching)!=1:
                    observed.append(None)
                else:
                    row=matching[0]
                    observed.append((integer(row.get("hullid")),
                                    integer(row.get("mission")),
                                    integer(row.get("enemy")),
                                    str(row.get("friendlycode"))))
            status=("TMINUS1_OWNER_ORDER_CONSENSUS" if
                    observed and all(x is not None and x==observed[0]
                                     for x in observed)
                    else "ABSTAIN_OWNER_ORDER_MISSING_OR_CONFLICTING")
        counts[status]+=1
        details.append({"owner_id":owner,"ship_id":sid,
                        "Tminus1_input_status":status,
                        "owner_perspective_count":len(perspectives)})
    return {"member_perspectives":len(hist),
            "owner_ship_order_statuses":dict(sorted(counts.items())),
            "observed_ship_identity_targets":details}


def inspect_window(conn:Any,item:Mapping[str,Any])->dict[str,Any]:
    game,turn=item["game_id"],item["turn"]
    cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
    rows=[]
    for (_turn,vid),case in sorted(cases.items()):
        if _turn!=turn:continue
        payload=case.payload
        if not isinstance(payload,Mapping):raise ValueError("malformed case payload")
        rows.append({"vcr_id":vid,"shape":classify_vcr(payload),
                     "payload":payload})
    site=site_population(rows)
    targets=[]
    for r in rows:
        if r["shape"]=="ORDINARY_SHIP_VS_SHIP":
            for side in ("left","right"):
                v=identity(r["payload"],side)
                if v is not None:targets.append(v)
    # The input audit is computed for every preselected window, not just
    # favorable sites. It never predicts pair identities or target locations.
    tminus1=tminus1_owner_coverage(
        conn,game=game,turn=turn,ships=targets
    ) if targets else {
        "member_perspectives":0,
        "owner_ship_order_statuses":{},
        "observed_ship_identity_targets":[],
    }
    shapes=Counter(r["shape"] for r in rows)
    counts=Counter(s["category"] for s in site["sites"])
    return {
        "game_id":game,"turn":turn,"cohort":item["cohort"],
        "all_vcrs":len(rows),
        "shape_counts":dict(sorted(shapes.items())),
        "site_category_counts":dict(sorted(counts.items())),
        "sites":site["sites"],
        "unlocatable_vcr_ids":site["unlocatable_vcr_ids"],
        "Tminus1_owner_coverage":tminus1,
        "multi_ordinary_ship_site_count":sum(
            s["candidate_multi_ship_site"] for s in site["sites"]),
        "predicted_next_VCR_pairs":0,
        "selection_happened_before_all_VCR_payload_reads":True,
    }


def build_report(conn:Any,*,max_games:int,dbpath:str)->dict[str,Any]:
    info("preselecting game-turns using T-1 archive and VCR-existence metadata")
    candidate=candidate_metadata(conn)
    windows,selection=freeze_windows(candidate,max_games=max_games)
    if len(selection["selected_games"])<8:
        raise ValueError("insufficient distinct games for broad C5 coverage")
    info(f"preselected {len(windows)} windows / {selection['selected_game_count']} games")
    results=[]
    for i,w in enumerate(windows,1):
        info(f"[{i}/{len(windows)}] G{w['game_id']} T{w['turn']} {w['cohort']}")
        row=inspect_window(conn,w)
        results.append(row)
        info(f"[{i}/{len(windows)}] VCR={row['all_vcrs']} "
             f"ordinary_multi_sites={row['multi_ordinary_ship_site_count']}")
    sites=[s for row in results for s in row["sites"]]
    status=Counter(s["category"] for s in sites)
    shapes=Counter()
    owner=Counter()
    for r in results:
        shapes.update(r["shape_counts"])
        owner.update(r["Tminus1_owner_coverage"]["owner_ship_order_statuses"])
    summary={
        "games":selection["selected_game_count"],"windows":len(windows),
        "current_VCR_observations":sum(x["all_vcrs"] for x in results),
        "unique_sites":len(sites),
        "ordinary_ship_only_multi_VCR_sites":status["ORDINARY_SHIP_ONLY_MULTIVCR_SITE"],
        "ordinary_ship_vs_ship_VCRs":shapes["ORDINARY_SHIP_VS_SHIP"],
        "explicit_horwasp_out_of_scope_VCRs":shapes["OUT_OF_SCOPE_HORWASP_RACE12"],
        "ordinary_ship_planet_candidate_VCRs":shapes["ORDINARY_SHIP_VS_PLANET_CANDIDATE"],
        "site_classifications":dict(sorted(status.items())),
        "VCR_shape_classifications":dict(sorted(shapes.items())),
        "Tminus1_owner_ship_order_readiness":dict(sorted(owner.items())),
        "candidate_parent_queue_transition_sites":status["ORDINARY_SHIP_ONLY_MULTIVCR_SITE"],
        "full_NuHost_combat_queue_or_seed_predictions":0,
        "Horwasp_rules_promoted":False,
    }
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "db_path":dbpath,"selection":selection,"summary":summary,
        "preselected_window_evaluations":results,
        "research_next":"Extend ordinary C5 parent-queue held-out selection to these frozen sites; treat selected site outcomes as open/factual and reserve new games for genuine independent acceptance. Do not reinterpret this census as queue prediction.",
        "boundary":(
            "Preselection uses archive T-1 and VCR PRESENCE only. Current VCR "
            "identities, site coordinates and shapes enter observational "
            "coverage AFTER preselection. Owner T-1 ship orders are checked "
            "against the target IDs, not used to select them. Missing/conflict "
            "explicitly ABSTAIN. Horwasp race12 is out of scope. No combat "
            "pair, side, capture outcome, seed or Host execution order is "
            "predicted. No production/client/CURRENT modifications."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--max-games",type=int,default=DEFAULT_GAMES)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 DB missing")
        start=time.monotonic()
        info("verifying SHA256 once before read-only DuckDB open")
        with db.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("public100 SHA256 mismatch")
        info(f"SHA256 verified in {time.monotonic()-start:.1f}s")
        conn,dbpath=connect_compact_generation_read_only(
            GENERATION,args.corpus_db_root
        )
        try:result=build_report(conn,max_games=args.max_games,dbpath=str(dbpath))
        finally:conn.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(".json.tmp")
        temp.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
        temp.replace(args.output)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== INDEPENDENT PUBLIC100 ORDINARY C5 COVERAGE V1 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
