"""Bounded, resumable public100 combat mass evidence survey.

Processes many games and distinct VCR-heavy turns with per-game atomic
checkpoints and incremental published summaries. No observed VCR mass or
seed is used as input to a combat predictor. Numerical mass matches and
T-1 owner ship/Shield Generator geometry are observational controls ONLY.

A cached historical T-1 waypoint or co-location does not establish
combat-phase positions; Horwasp VCR masses cannot independently determine
the postcombat clan state. No Host rule or probability is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
DIAG=Path(__file__).resolve().parent
for path in (ROOT/"src",DIAG):
    if str(path) not in sys.path:
        sys.path.insert(0,str(path))

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,member_refs_for_turns,reconstruct_members,
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from combat_multigame_conditional_ensemble_v1 import _independent_hull_specs
from combat_mass_phase_constraints_v1 import inverse_clan_interval

SCHEMA="planets-lab.combat-mass-long-survey.v1"
EXCLUDE_KNOWN_SPECIAL=frozenset({591478})
ANCHORS=((400330,141),(217591,149),(253449,82),(371631,156))
SOURCE_BOUNDARY=(
    "Only factual current-VCR side IDs, race, hull, static modifier attributes, "
    "mass and appearance order are analyzed as OBSERVATIONS. A game-specific "
    "static hull catalog and owner-perspective T-1 raw ship/engine/generator "
    "rows are independent contextual evidence; they do not establish host-phase "
    "precombat state. Horwasp clan intervals are inverse constraints using "
    "an UNVERIFIED linear rule and are NOT predictions. The right-carrier +360 "
    "branch and Shield Generator activation are not predicted. No RNG, effective "
    "weapon setup, Horwasp attrition algorithm or combat rule is promoted."
)


def _int(x:Any)->int|None:
    return x if isinstance(x,int) and not isinstance(x,bool) else None


def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _digest(value:Any)->str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _write_atomic(path:Path, content:Mapping[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    with tmp.open("w",encoding="utf-8") as out:
        json.dump(content,out,sort_keys=True,ensure_ascii=False,indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp,path)


def _spread(values:list[int],n:int)->list[int]:
    if n<=0:
        return []
    if len(values)<=n:
        return values[:]
    return [values[min(len(values)-1,(2*i+1)*len(values)//(2*n))]
            for i in range(n)]


def choose_games_and_turns(
    conn:Any,*,max_games:int,turns_per_game:int,max_rows_per_turn:int,
)->list[tuple[int,list[int]]]:
    if min(max_games,turns_per_game,max_rows_per_turn)<1:
        raise ValueError("invalid survey selection bounds")
    records=conn.execute(
        """
        SELECT game_id, embedded_turn, COUNT(*) AS perspective_rows
        FROM vcrs
        GROUP BY game_id, embedded_turn
        HAVING COUNT(*) BETWEEN 2 AND 2000
        ORDER BY game_id, perspective_rows DESC, embedded_turn ASC
        """
    ).fetchall()
    grouped=defaultdict(list)
    for game,turn,count in records:
        if any(_int(x) is None for x in (game,turn,count)):
            raise ValueError("invalid public100 VCR grouping row")
        if turn<=0 or game in EXCLUDE_KNOWN_SPECIAL:
            continue
        grouped[game].append((turn,count))
    for game in grouped:
        grouped[game].sort(key=lambda x:(-x[1],x[0]))
    chosen=[]
    anchor_ids=[g for g,t in ANCHORS if g in grouped]
    chosen.extend(anchor_ids[:max_games])
    remaining=sorted(g for g in grouped if g not in chosen)
    chosen.extend(_spread(remaining,max_games-len(chosen)))
    answer=[]
    for g in chosen:
        ranked=[t for t,c in grouped[g]]
        anchor=[t for ag,t in ANCHORS if ag==g and t in ranked]
        selected=anchor[:]
        # Select high, median and low VCR-volume turns, not just one busy turn.
        priorities=ranked[:2]
        if ranked:
            priorities.extend([ranked[len(ranked)//2],ranked[-1]])
        priorities.extend(ranked)
        for t in priorities:
            if t not in selected and len(selected)<turns_per_game:
                selected.append(t)
        answer.append((g,selected[:turns_per_game]))
    return answer


def _owner_records(conn:Any,game:int,turn:int,owners:set[int])->tuple[dict[int,dict[int,Mapping[str,Any]]],set[int],Counter]:
    refs=member_refs_for_turns(conn,game_id=game,turns={turn-1},
                              include_embedded_turn=False)
    chosen=[r for r in refs if r.perspective_player_id in owners]
    records:dict[int,dict[int,Mapping[str,Any]]]=defaultdict(dict)
    bad_owners:set[int]=set()
    stats=Counter()
    for ref,member in reconstruct_members(conn,chosen):
        owner=ref.perspective_player_id
        ships=member.get("ships")
        if not isinstance(ships,list):
            stats["missing_owner_ship_list"]+=1
            continue
        stats["owner_perspective_source_members"]+=1
        for raw in ships:
            if not isinstance(raw,Mapping) or _int(raw.get("ownerid"))!=owner:
                continue
            ship_id=_int(raw.get("id"))
            if ship_id is None:
                continue
            reduced={k:raw.get(k) for k in (
                "id","hullid","ownerid","engineid","clans","x","y",
                "targetx","targety","warp","damage","neutronium","mission"
            )}
            previous=records[owner].get(ship_id)
            if previous is not None and previous!=reduced:
                bad_owners.add(owner)
                stats["conflicting_owner_ship_observation"]+=1
            else:
                records[owner][ship_id]=reduced
    for owner in bad_owners:
        records.pop(owner,None)
    return records,bad_owners,stats


def _site(raw:Mapping[str,Any])->tuple[int,int]|None:
    x,y=_int(raw.get("x")),_int(raw.get("y"))
    return (x,y) if x is not None and y is not None else None


def _waypoint(raw:Mapping[str,Any])->tuple[int,int]|None:
    x,y=_int(raw.get("targetx")),_int(raw.get("targety"))
    return (x,y) if x is not None and y is not None else None


def _generator(spec:Any)->bool:
    return spec is not None and (
        "shield generator" in (spec.name or "").casefold()
        or "shield generator" in (spec.special or "").casefold()
    )


def geometric_control(*,participant:Mapping[str,Any]|None,
                      same_owner:Mapping[int,Mapping[str,Any]],
                      site:tuple[int,int]|None,specs:Any)->dict[str,Any]:
    if participant is None or site is None:
        return {"status":"UNKNOWN_OWNER_OR_SITE","exact_site_generators":None,
                "co_travel_generators":None}
    engine_id=_int(participant.get("engineid"))
    engine=specs.engines.get(engine_id)
    base_xy=_site(participant)
    target=_waypoint(participant)
    exact=[]
    co_travel=[]
    nearby=[]
    for ship_id,raw in same_owner.items():
        if _int(raw.get("id"))==_int(participant.get("id")):
            continue
        hull=specs.hulls.get(_int(raw.get("hullid")))
        if not _generator(hull):
            continue
        current=_site(raw)
        if current==site:
            exact.append(ship_id)
        if base_xy is not None and target is not None and current==base_xy and _waypoint(raw)==target:
            co_travel.append(ship_id)
        if _waypoint(raw)==site:
            nearby.append(ship_id)
    waypoint_to_vcr_offset=[
        site[0]-target[0],site[1]-target[1]
    ] if target is not None else None
    return {
        "status":"TMINUS1_OWNER_GEOMETRY_ONLY",
        "participant_origin":list(base_xy) if base_xy is not None else None,
        "participant_waypoint":list(target) if target is not None else None,
        "vcr_site":list(site),
        "tminus1_participant_at_site":base_xy==site,
        "exact_site_generators":len(exact),
        "same_origin_and_waypoint_generators":len(co_travel),
        "generator_waypoints_to_site":len(nearby),
        "sample_exact_generator_ids":sorted(exact)[:4],
        "sample_co_travel_generator_ids":sorted(co_travel)[:4],
        "engine_id":engine_id,
        "engine_cost_mc":engine.cost.megacredits if engine else None,
        "per_generator_half_engine_cost":engine.cost.megacredits//2 if engine else None,
        "waypoint_to_vcr_offset":waypoint_to_vcr_offset,
        "waypoint_to_vcr_distance_sq":(
            waypoint_to_vcr_offset[0]**2+waypoint_to_vcr_offset[1]**2
            if waypoint_to_vcr_offset else None
        ),
        "boundary":"T-1 common orders or coordinates DO NOT establish combat-phase generator support",
    }


def _numeric_class(*,observed:int,base:int,side:str,left_bays:int,
                   hull_mass:int,race:int,geo:Mapping[str,Any])->str:
    if race==12:
        if observed==2*hull_mass:
            return "horwasp_catalog_full_load_endpoint"
        if side=="right" and left_bays>0 and observed==2*hull_mass+360:
            return "horwasp_catalog_full_plus360_arithmetic"
        if hull_mass<=observed<2*hull_mass:
            return "horwasp_partial_numeric_range"
        return "horwasp_other_or_catalog_conflict"
    if observed==base:
        return "classic_baseline"
    if side=="right" and left_bays>0 and observed==base+360:
        return "right_plus360_arithmetic"
    diff=observed-base
    engine_bonus=geo.get("per_generator_half_engine_cost")
    if _int(engine_bonus) is not None and engine_bonus>0:
        for n in (1,2):
            if diff==engine_bonus*n:
                return f"engine_shield_{n}_numeric_match"
            if side=="right" and left_bays>0 and diff==engine_bonus*n+360:
                return f"engine_shield_{n}_plus360_numeric_match"
    return "unexplained_with_available_owner_geometry"


def analyze_turn(*,conn:Any,game:int,turn:int,specs:Any,
                 max_vcrs:int,max_examples:int)->dict[str,Any]:
    cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
    bounded=[case for _,case in sorted(cases.items())[:max_vcrs]]
    owners={
        _int(case.payload.get(key))
        for case in bounded for key in ("leftownerid","rightownerid")
    }
    owners.discard(None)
    own,conflicts,source_stats=_owner_records(conn,game,turn,owners)
    stats=Counter(source_stats)
    stats["unique_vcrs_available"]=len(cases)
    stats["unique_vcrs_examined"]=len(bounded)
    horwasp_sequences=defaultdict(list)
    examples=[]
    for case in bounded:
        payload=case.payload
        left,right=payload.get("left"),payload.get("right")
        if not isinstance(left,Mapping) or not isinstance(right,Mapping):
            stats["non_ship_vcr"]+=1
            continue
        if any(_int(raw.get("hullid")) is None or _int(raw.get("hullid"))<=0 for raw in (left,right)):
            stats["non_ship_vcr"]+=1
            continue
        stats["ship_vcrs"]+=1
        left_bays=_int(left.get("baycount")) or 0
        x,y=_int(payload.get("x")),_int(payload.get("y"))
        site=(x,y) if x is not None and y is not None else None
        for side,raw,ownerkey in (
            ("left",left,"leftownerid"),("right",right,"rightownerid")
        ):
            ship_id,hull_id,race,mass=(
                _int(raw.get(key)) for key in (
                    "objectid","hullid","raceid","mass"
                )
            )
            owner=_int(payload.get(ownerkey))
            if None in (ship_id,hull_id,race,mass) or hull_id not in specs.hulls:
                stats["missing_effective_side_or_hull_catalog"]+=1
                continue
            hull=specs.hulls[hull_id]
            base=hull.mass+(50 if race==1 else 0)
            owner_ships=own.get(owner,{})
            raw_owner=owner_ships.get(ship_id)
            if raw_owner is not None:
                stats["participant_Tminus1_owner_seen"]+=1
            elif owner in conflicts:
                stats["participant_Tminus1_owner_conflict"]+=1
            else:
                stats["participant_Tminus1_owner_missing"]+=1
            geo=geometric_control(
                participant=raw_owner,same_owner=owner_ships,
                site=site,specs=specs
            )
            cls=_numeric_class(
                observed=mass,base=base,side=side,left_bays=left_bays,
                hull_mass=hull.mass,race=race,geo=geo,
            )
            stats["side_observations"]+=1
            stats["class:"+cls]+=1
            if geo.get("exact_site_generators",0) not in (None,0):
                stats["owner_Tminus1_generator_at_vcr_site"]+=1
            if geo.get("same_origin_and_waypoint_generators",0) not in (None,0):
                stats["owner_Tminus1_generator_co_travel_order"]+=1
            if race==12:
                candidates=[]
                for label,h in (
                    [("per_game_catalog",hull.mass)]+
                    ([("external_brood_reference_145",145)]
                     if hull_id==117 and hull.mass!=145 else [])
                ):
                    for bonus in ([0,360] if side=="right" and left_bays>0 and 2*h>=140 else [0]):
                        interval=inverse_clan_interval(mass,h,hull.cargo_capacity,bonus)
                        if interval is not None:
                            candidates.append({
                                "base_source":label,"base":h,
                                "right_bonus_hypothesis":bonus,
                                "possible_clans":interval,
                            })
                t1clans=_int(raw_owner.get("clans")) if raw_owner else None
                horwasp_sequences[ship_id].append({
                    "vcr_id":case.vcr_id,
                    "site":list(site) if site else None,
                    "side":side,"factual_mass":mass,
                    "start_fighters":_int(raw.get("fighters")),
                    "start_damage":_int(raw.get("damage")),
                    "tminus1_clans":t1clans,
                    "candidate_clan_intervals":candidates,
                    "boundary":"INVERSE using observed VCR, not an independent clan prediction",
                })
            interesting=(
                cls not in ("classic_baseline","right_plus360_arithmetic")
                or bool(geo.get("same_origin_and_waypoint_generators",0))
            )
            if interesting and len(examples)<max_examples:
                examples.append({
                    "game_id":game,"turn":turn,"vcr_id":case.vcr_id,
                    "ship_id":ship_id,"owner_id":owner,"race":race,"side":side,
                    "hull_id":hull_id,"hull_name":hull.name,
                    "catalog_mass":hull.mass,"base_mass":base,
                    "factual_mass":mass,"class":cls,
                    "left_observed_bays":left_bays,
                    "Tminus1_owner_clans":_int(raw_owner.get("clans")) if raw_owner else None,
                    "geometry":geo,
                })
    timeline_examples=[]
    for ship_id,seq in sorted(horwasp_sequences.items()):
        seq.sort(key=lambda s:s["vcr_id"])
        transitions=[]
        for prev,next_ in zip(seq,seq[1:]):
            changes=[]
            for a in prev["candidate_clan_intervals"]:
                for b in next_["candidate_clan_intervals"]:
                    if a["base_source"]!=b["base_source"] or a["base"]!=b["base"]:
                        continue
                    alo,ahi=a["possible_clans"]
                    blo,bhi=b["possible_clans"]
                    changes.append({
                        "base_source":a["base_source"],
                        "loss_min":alo-bhi,"loss_max":ahi-blo,
                        "nonnegative_loss_possible":blo<=ahi,
                        "before_bonus":a["right_bonus_hypothesis"],
                        "after_bonus":b["right_bonus_hypothesis"],
                    })
            stats["horwasp_same_ship_vcr_transitions"]+=1
            if next_["factual_mass"]!=prev["factual_mass"]:
                stats["horwasp_changed_mass_between_appearances"]+=1
            transitions.append({
                "from":prev["vcr_id"],"to":next_["vcr_id"],
                "same_site":prev["site"]==next_["site"],
                "mass_delta":next_["factual_mass"]-prev["factual_mass"],
                "fighter_start_delta":(
                    next_["start_fighters"]-prev["start_fighters"]
                    if next_["start_fighters"] is not None
                    and prev["start_fighters"] is not None else None
                ),
                "candidate_clan_changes":changes,
            })
        stats["horwasp_ship_timelines"]+=1
        if len(timeline_examples)<max_examples:
            timeline_examples.append({
                "game_id":game,"turn":turn,"ship_id":ship_id,
                "appearances":seq[:120],"transitions":transitions[:119],
                "truncated":len(seq)>120,
            })
    return {
        "game_id":game,"turn":turn,
        "counts":dict(sorted(stats.items())),
        "examples":examples,
        "horwasp_timelines":timeline_examples,
        "boundary":SOURCE_BOUNDARY,
    }


def analyze_game(*,conn:Any,game:int,turns:list[int],
                 max_vcrs:int,max_examples_per_turn:int)->dict[str,Any]:
    report={"game_id":game,"status":"ok","turns":[],"errors":[]}
    specs=_independent_hull_specs(conn,game)
    for turn in turns:
        try:
            report["turns"].append(analyze_turn(
                conn=conn,game=game,turn=turn,specs=specs,
                max_vcrs=max_vcrs,max_examples=max_examples_per_turn,
            ))
        except (OSError,ValueError,TypeError,KeyError) as exc:
            report["errors"].append({
                "turn":turn,"exception_type":type(exc).__name__,"reason":str(exc)[:400]
            })
    if report["errors"]:
        report["status"]="partial" if report["turns"] else "failed"
    return report


def publish_snapshot(*,checkpoint_dir:Path,summary_path:Path,
                     selection:list[tuple[int,list[int]]],
                     identity:str,config:Mapping[str,Any])->dict[str,Any]:
    global_counts=Counter()
    statuses=Counter()
    games=[]
    examples=[]
    timelines=[]
    failures=[]
    done=set()
    for game,turns in selection:
        path=checkpoint_dir/f"game-{game}.json"
        if not path.exists():
            continue
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema")!=SCHEMA or data.get("identity")!=identity:
            raise ValueError(f"stale or incompatible checkpoint: {path}")
        done.add(game)
        row=data["result"]
        statuses[row["status"]]+=1
        games.append({
            "game_id":game,"turns_done":[x["turn"] for x in row["turns"]],
            "errors":len(row["errors"]),"status":row["status"],
        })
        failures.extend([{"game_id":game,**err} for err in row["errors"]][:8])
        for turn in row["turns"]:
            global_counts.update(turn["counts"])
            if len(examples)<250:
                examples.extend(turn["examples"][:min(10,250-len(examples))])
            if len(timelines)<80:
                timelines.extend(turn["horwasp_timelines"][:min(3,80-len(timelines))])
    report={
        "schema":SCHEMA,"status":(
            "COMPLETE_OBSERVATIONAL_NOT_PROMOTED" if len(done)==len(selection)
            else "PARTIAL_CHECKPOINT_RESUMABLE_NOT_PROMOTED"
        ),
        "identity_sha256":identity,
        "config":dict(config),
        "completed_games":len(done),
        "target_games":len(selection),
        "not_completed_game_ids":[g for g,ts in selection if g not in done],
        "game_status_counts":dict(sorted(statuses.items())),
        "summary":dict(sorted(global_counts.items())),
        "game_index":games,
        "sample_observations":examples,
        "sample_horwasp_timelines":timelines,
        "sample_failures":failures[:100],
        "truncation":{
            "sample_observations_max":250,"sample_timeline_max":80,
            "individual_per_game_checkpoints_only_local":True,
        },
        "evidence_boundary":SOURCE_BOUNDARY,
    }
    _write_atomic(summary_path,report)
    return report


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--max-games",type=int,default=80)
    p.add_argument("--turns-per-game",type=int,default=4)
    p.add_argument("--max-vcrs-per-turn",type=int,default=150)
    p.add_argument("--max-examples-per-turn",type=int,default=20)
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--published-summary",type=Path,required=True)
    a=p.parse_args()
    try:
        if any(x<=0 for x in (
            a.max_games,a.turns_per_game,a.max_vcrs_per_turn,a.max_examples_per_turn
        )):
            raise ValueError("all survey limits must be positive")
        conn,path=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            selection=choose_games_and_turns(
                conn,max_games=a.max_games,turns_per_game=a.turns_per_game,
                max_rows_per_turn=a.max_vcrs_per_turn
            )
            if not selection:
                raise ValueError("no public100 games with VCRs were selected")
            config={
                "source_sha":a.source_sha,
                "db_generation":a.corpus_db_generation,
                "db_root":str(a.corpus_db_root),
                "max_games":a.max_games,
                "turns_per_game":a.turns_per_game,
                "max_vcrs_per_turn":a.max_vcrs_per_turn,
                "max_examples_per_turn":a.max_examples_per_turn,
                "selection":[[g,turns] for g,turns in selection],
            }
            identity=_digest({"schema":SCHEMA,**config})
            a.checkpoint_dir.mkdir(parents=True,exist_ok=True)
            report=publish_snapshot(
                checkpoint_dir=a.checkpoint_dir,summary_path=a.published_summary,
                selection=selection,identity=identity,config=config,
            )
            print("===== PUBLIC100 LONG COMBAT MASS SURVEY V1 =====",flush=True)
            print("identity:",identity,flush=True)
            print("games:",len(selection),"turn_targets:",sum(len(ts) for g,ts in selection),flush=True)
            print("already_completed:",report["completed_games"],flush=True)
            for index,(game,turns) in enumerate(selection,1):
                checkpoint=a.checkpoint_dir/f"game-{game}.json"
                if checkpoint.exists():
                    print(f"[{index}/{len(selection)}] RESUME_SKIP game={game}",flush=True)
                    continue
                try:
                    result=analyze_game(
                        conn=conn,game=game,turns=turns,
                        max_vcrs=a.max_vcrs_per_turn,
                        max_examples_per_turn=a.max_examples_per_turn
                    )
                except (OSError,TypeError,ValueError,KeyError) as exc:
                    result={
                        "game_id":game,"status":"failed","turns":[],
                        "errors":[{"turn":None,"exception_type":type(exc).__name__,
                                   "reason":str(exc)[:400]}],
                    }
                _write_atomic(checkpoint,{
                    "schema":SCHEMA,"identity":identity,"result":result,
                })
                report=publish_snapshot(
                    checkpoint_dir=a.checkpoint_dir,summary_path=a.published_summary,
                    selection=selection,identity=identity,config=config,
                )
                counts=Counter()
                for turn in result["turns"]:
                    counts.update(turn["counts"])
                print(
                    f"[{index}/{len(selection)}] game={game} "
                    f"status={result['status']} turns={len(result['turns'])}/{len(turns)} "
                    f"ship_vcrs={counts['ship_vcrs']} sides={counts['side_observations']} "
                    f"horwasp_transitions={counts['horwasp_same_ship_vcr_transitions']} "
                    f"completed={report['completed_games']}/{report['target_games']}",
                    flush=True,
                )
        finally:
            conn.close()
        print("===== LONG SURVEY FINAL =====",flush=True)
        print("status:",report["status"],flush=True)
        print("game_status:",report["game_status_counts"],flush=True)
        print("summary:",report["summary"],flush=True)
        print("published_summary:",a.published_summary,flush=True)
        print("local_checkpoints:",a.checkpoint_dir,flush=True)
        return 0 if report["game_status_counts"].get("ok",0)>0 else 2
    except (OSError,TypeError,ValueError,KeyError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr,flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
