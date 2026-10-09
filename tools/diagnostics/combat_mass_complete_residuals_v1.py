"""Complete attribution of all long-survey mass residual VCR sides.

Replays ONLY the original survey classifier on 80-game checkpoint-selected
turns where the digest reports anomalies. It must reproduce exact original
per-class counts, then records EVERY residual identity (including the 27
whose first-N details were not saved). Observed current-VCR masses are only
used for numeric comparisons; this is NOT independent combat prediction.

Also assesses *candidate* ceiling rounding for odd-cost engines, separately
from the existing floor(cost/2) numeric classifier. Neither position nor
shield activation is established by T-1 observations.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter,defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for x in (ROOT/"src",Path(__file__).resolve().parent):
    if str(x) not in sys.path:
        sys.path.insert(0,str(x))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from combat_long_mass_survey_v1 import (
    _independent_hull_specs,_owner_records,_numeric_class,
    geometric_control,_int,
)
from combat_mass_phase_constraints_v1 import inverse_clan_interval

SCHEMA="planets-lab.combat-mass-complete-residuals.v1"
SURVEY_SCHEMA="planets-lab.combat-mass-long-survey.v1"
DIGEST_SCHEMA="planets-lab.combat-mass-long-survey-digest.v1"
UNRESOLVED={
    "unexplained_with_available_owner_geometry",
    "horwasp_other_or_catalog_conflict",
}
BOUNDARY=(
    "Observed VCR mass identifies unexplained cases and possible numeric "
    "engine rounding, not independent Host predictions. Current VCR side "
    "and T-1 owner snapshots may reflect different Host phases. Neither "
    "same-site T-1 nor common movement waypoints prove active generators "
    "in combat. Horwasp clan interpolation and alternate Brood mass145 "
    "are unverified; carrier +360 RNG branch is not predicted."
)


def selected_targets(survey:Mapping[str,Any], digest:Mapping[str,Any]):
    if survey.get("schema")!=SURVEY_SCHEMA or survey.get("status")!="COMPLETE_OBSERVATIONAL_NOT_PROMOTED":
        raise ValueError("incomplete source survey")
    if digest.get("schema")!=DIGEST_SCHEMA or digest.get("status")!="COMPLETE_DIGEST_OBSERVATIONAL_NOT_PROMOTED":
        raise ValueError("incomplete source digest")
    source=digest.get("source",{})
    if source.get("identity_sha256")!=survey.get("identity_sha256"):
        raise ValueError("survey/digest experiment identity conflict")
    if source.get("source_sha")!=survey.get("config",{}).get("source_sha"):
        raise ValueError("survey/digest source commit conflict")
    turns=digest.get("ranked_turns")
    if not isinstance(turns,list):
        raise ValueError("missing ranked turns")
    chosen={}
    for game,selected in survey["config"]["selection"]:
        chosen[game]=set(selected)
    targets={}
    for row in turns:
        game,turn,n=row.get("game_id"),row.get("turn"),row.get("unresolved")
        if any(type(x)!=int for x in (game,turn,n)) or n<0:
            raise ValueError("malformed ranked turn")
        if game not in chosen or turn not in chosen[game]:
            raise ValueError("ranked turn outside selected survey")
        if n>0:
            if (game,turn) in targets:
                raise ValueError("duplicate target")
            targets[(game,turn)]=n
    total=digest["counts"]["unresolved_mass_sides"]
    if sum(targets.values())!=total:
        raise ValueError("target anomalies do not reconcile with digest")
    if total<=0:
        raise ValueError("no residuals selected")
    return targets


def rounding_control(*,mass:int,base:int,side:str,left_bays:int,
                     geometry:Mapping[str,Any])->dict[str,Any]:
    cost=geometry.get("engine_cost_mc")
    if type(cost)!=int or cost<=0:
        return {"status":"UNKNOWN_ENGINE_COST","match_candidates":[]}
    floor=cost//2
    ceil=(cost+1)//2
    exact=geometry.get("exact_site_generators")
    convoy=geometry.get("same_origin_and_waypoint_generators")
    position="UNKNOWN_TMINUS1"
    if type(exact)==int and exact>0 and geometry.get("tminus1_participant_at_site") is True:
        position="TMINUS1_SITE_SUPPORT"
    elif type(convoy)==int and convoy>0:
        position="TMINUS1_COTRAVEL_ORDER"
    elif geometry.get("status")=="TMINUS1_OWNER_GEOMETRY_ONLY":
        position="NO_TMINUS1_SITE_OR_COTRAVEL"
    alternatives=[]
    for n in (1,2):
        for bonus in (0,360):
            if bonus and not (side=="right" and left_bays>0):
                continue
            if mass==base+n*ceil+bonus:
                alternatives.append({
                    "engine_cost_mc":cost,
                    "integer_rule_candidate":"CEIL_HALF_ENGINE_COST_PER_GENERATOR",
                    "one_generator_bonus":ceil,
                    "generator_count_assumed":n,
                    "carrier_plus360_branch_assumed":bonus,
                    "same_site_support_for_n":(
                        exact>=n if type(exact)==int else None
                    ),
                    "cotravel_order_support_for_n":(
                        convoy>=n if type(convoy)==int else None
                    ),
                })
    return {
        "status":position,
        "odd_engine_cost":cost%2==1,
        "per_generator_floor":floor,
        "per_generator_ceil":ceil,
        "match_candidates":alternatives,
        "boundary":"Numeric match alone does NOT establish rounding or active generator count",
    }


def horwasp_constraints(*,mass:int,hull_id:int,hullmass:int,
                         capacity:int,side:str,left_bays:int):
    scenarios=[("game_catalog",hullmass)]
    if hull_id==117 and hullmass!=145:
        scenarios.append(("EXTERNAL_REFERENCE_145_HYPOTHESIS",145))
    result=[]
    if capacity<=0:
        return result
    for label,base in scenarios:
        bonuses=[0]
        if side=="right" and left_bays>0 and 2*base>=140:
            bonuses.append(360)
        for bonus in bonuses:
            interval=inverse_clan_interval(mass,base,capacity,bonus)
            if interval is not None:
                result.append({
                    "base_source":label,"base_mass_assumed":base,
                    "carrier_plus360_assumed":bonus,
                    "clan_min":interval[0],"clan_max":interval[1],
                    "status":"UNVERIFIED_LINEAR_CLAN_INVERSION",
                })
    return result


def classify_target_turn(*,conn:Any,game:int,turn:int,cap:int,specs:Any):
    cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
    selected=[case for _,case in sorted(cases.items())[:cap]]
    owners={
        _int(case.payload.get(ownerkey))
        for case in selected for ownerkey in ("leftownerid","rightownerid")
    }
    owners.discard(None)
    owner_rows,conflicts,raw_stats=_owner_records(conn,game,turn,owners)
    counts=Counter()
    results=[];odd=[]
    for case in selected:
        payload=case.payload
        left,right=payload.get("left"),payload.get("right")
        if not isinstance(left,Mapping) or not isinstance(right,Mapping):
            counts["non_ship_vcr"]+=1
            continue
        if any(_int(s.get("hullid")) is None or _int(s.get("hullid"))<=0 for s in (left,right)):
            counts["non_ship_vcr"]+=1
            continue
        counts["ship_vcrs"]+=1
        left_bays=_int(left.get("baycount")) or 0
        x,y=_int(payload.get("x")),_int(payload.get("y"))
        site=(x,y) if x is not None and y is not None else None
        for name,side,ownerkey in (
            ("left",left,"leftownerid"),("right",right,"rightownerid")
        ):
            sid,hid,race,mass=(_int(side.get(k)) for k in (
                "objectid","hullid","raceid","mass"
            ))
            owner=_int(payload.get(ownerkey))
            if None in (sid,hid,race,mass) or hid not in specs.hulls:
                counts["missing_effective_side_or_hull_catalog"]+=1
                continue
            hull=specs.hulls[hid]
            base=hull.mass+(50 if race==1 else 0)
            own=owner_rows.get(owner,{})
            raw=own.get(sid)
            geo=geometric_control(participant=raw,same_owner=own,site=site,specs=specs)
            cls=_numeric_class(
                observed=mass,base=base,side=name,left_bays=left_bays,
                hull_mass=hull.mass,race=race,geo=geo,
            )
            counts["class:"+cls]+=1
            counts["side_observations"]+=1
            if cls in UNRESOLVED:
                result={
                    "game_id":game,"turn":turn,
                    "vcr_id":case.vcr_id,"ship_id":sid,
                    "owner_id":owner,"side":name,"race":race,
                    "hull_id":hid,"hull_name":hull.name,
                    "catalog_hull_mass":hull.mass,
                    "catalog_cargo_capacity":hull.cargo_capacity,
                    "federation_adjusted_base":base,
                    "observed_vcr_mass":mass,
                    "observed_delta_from_base":mass-base,
                    "original_class":cls,
                    "VCR_site":list(site) if site else None,
                    "VCR_left_baycount":left_bays,
                    "vcr_observation_count":case.observation_count,
                    "tminus1_owner_ship_available":raw is not None,
                    "tminus1_owner_conflict":owner in conflicts,
                    "tminus1_owner_clans":_int(raw.get("clans")) if raw else None,
                    "tminus1_owner_engine_id":_int(raw.get("engineid")) if raw else None,
                    "tminus1_owner_raw_position":[raw.get("x"),raw.get("y")] if raw else None,
                    "tminus1_owner_waypoint":[raw.get("targetx"),raw.get("targety")] if raw else None,
                    "geometry":geo,
                    "ceil_rounding_hypotheses":rounding_control(
                        mass=mass,base=base,side=name,left_bays=left_bays,geometry=geo,
                    ),
                    "horwasp_clan_inverse_hypotheses":(
                        horwasp_constraints(
                            mass=mass,hull_id=hid,hullmass=hull.mass,
                            capacity=hull.cargo_capacity,side=name,left_bays=left_bays,
                        ) if race==12 else []
                    ),
                }
                results.append(result)
            cost=geo.get("engine_cost_mc")
            if type(cost)==int and cost>0 and cost%2==1:
                check=rounding_control(
                    mass=mass,base=base,side=name,left_bays=left_bays,geometry=geo
                )
                odds={
                    "game_id":game,"turn":turn,"vcr_id":case.vcr_id,
                    "ship_id":sid,"side":name,"race":race,
                    "original_class":cls,"engine_cost_mc":cost,
                    "mass_delta":mass-base,
                    "ceil_matched":bool(check["match_candidates"]),
                    "phase_support":check["status"],
                }
                odd.append(odds)
    counts["non_ship_vcr"]+=0
    counts["unique_vcrs_examined"]=len(selected)
    return {
        "game_id":game,"turn":turn,
        "counts":dict(counts),
        "anomalies":results,
        "odd_engine_cost_side_controls":odd,
    }


def build_report(*,conn:Any,survey:Mapping[str,Any],digest:Mapping[str,Any],
                 checkpoint_dir:Path,db_path:str):
    targets=selected_targets(survey,digest)
    by_game=defaultdict(list)
    for (game,turn),expected in sorted(targets.items()):
        by_game[game].append((turn,expected))
    cap=survey["config"]["max_vcrs_per_turn"]
    all_cases=[];odd_controls=[];turn_index=[]
    for game,turns in by_game.items():
        saved=json.loads((checkpoint_dir/f"game-{game}.json").read_text(encoding="utf-8"))
        if saved.get("schema")!=SURVEY_SCHEMA or saved.get("identity")!=survey["identity_sha256"]:
            raise ValueError(f"source game checkpoint identity mismatch {game}")
        saved_turns={r["turn"]:r for r in saved["result"]["turns"]}
        specs=_independent_hull_specs(conn,game)
        for turn,expected in turns:
            source_counts=saved_turns[turn]["counts"]
            current=classify_target_turn(conn=conn,game=game,turn=turn,cap=cap,specs=specs)
            for key,value in source_counts.items():
                if key.startswith("class:") and current["counts"].get(key,0)!=value:
                    raise ValueError(f"reclassified mass count mismatch {game} T{turn} {key}")
            if current["counts"]["side_observations"]!=source_counts["side_observations"]:
                raise ValueError(f"reclassified side count mismatch {game} T{turn}")
            if current["counts"]["unique_vcrs_examined"]!=source_counts["unique_vcrs_examined"]:
                raise ValueError(f"VCR count mismatch {game} T{turn}")
            if len(current["anomalies"])!=expected:
                raise ValueError(f"residual identity count mismatch {game} T{turn}")
            saved_ids={
                (e["vcr_id"],e["ship_id"],e["side"])
                for e in saved_turns[turn]["examples"]
                if e.get("class") in UNRESOLVED
            }
            recovered_ids={
                (e["vcr_id"],e["ship_id"],e["side"])
                for e in current["anomalies"]
            }
            if not saved_ids<=recovered_ids:
                raise ValueError(f"original saved example not found in full rescan {game} T{turn}")
            current["recovered_beyond_first_n"]=len(recovered_ids-saved_ids)
            turn_index.append({
                "game_id":game,"turn":turn,
                "expected_residuals":expected,
                "verified_residuals":len(recovered_ids),
                "already_saved":len(saved_ids),
                "newly_recovered":len(recovered_ids-saved_ids),
                "odd_engine_controls":len(current["odd_engine_cost_side_controls"]),
            })
            all_cases.extend(current["anomalies"])
            odd_controls.extend(current["odd_engine_cost_side_controls"])
    all_cases.sort(key=lambda x:(x["game_id"],x["turn"],x["vcr_id"],x["side"]))
    if len(all_cases)!=digest["counts"]["unresolved_mass_sides"]:
        raise ValueError("not all 67 source residuals recovered")
    if len({(x["game_id"],x["turn"],x["vcr_id"],x["side"]) for x in all_cases})!=len(all_cases):
        raise ValueError("duplicate factual VCR-side identifiers")
    old=sum(x["already_saved"] for x in turn_index)
    if old != digest["counts"]["unresolved_VCR_details_saved"]:
        raise ValueError("first-N original saved ID total disagrees with digest")
    new=sum(x["newly_recovered"] for x in turn_index)
    if new != digest["counts"]["unresolved_VCR_details_unsaved"]:
        raise ValueError("missing ID reconstruction disagrees with digest")
    by_class=Counter(x["original_class"] for x in all_cases)
    by_race=Counter(str(x["race"]) for x in all_cases)
    by_engine=Counter(str(x["tminus1_owner_engine_id"]) for x in all_cases)
    by_ship=Counter((x["game_id"],x["turn"],x["ship_id"]) for x in all_cases)
    rounded=[
        x for x in all_cases
        if x["ceil_rounding_hypotheses"]["match_candidates"]
    ]
    return {
        "schema":SCHEMA,
        "status":"COMPLETE_ALL_67_RESIDUALS_RECONSTRUCTED_NOT_PROMOTED",
        "source":{
            "survey_commit":survey["config"]["source_sha"],
            "survey_experiment_id":survey["identity_sha256"],
            "digest_schema":digest["schema"],
            "database_generation":survey["config"]["db_generation"],
            "database_path":db_path,
            "original_per_turn_vcr_cap":cap,
        },
        "summary":{
            "original_unresolved":digest["counts"]["unresolved_mass_sides"],
            "all_residual_vcr_sides_recovered":len(all_cases),
            "previous_first_n_ids":old,
            "newly_recovered_ids":new,
            "distinct_game_turns":len(targets),
            "distinct_games":len(by_game),
            "distinct_ship_turn_groups":len(by_ship),
            "repeated_vcr_side_records":len(all_cases)-len(by_ship),
            "ceil_half_engine_cost_numeric_matches_in_residuals":len(rounded),
            "ceil_half_with_tminus1_site_support":sum(
                x["ceil_rounding_hypotheses"]["status"]=="TMINUS1_SITE_SUPPORT"
                for x in rounded
            ),
            "ceil_half_with_tminus1_cotravel_support":sum(
                x["ceil_rounding_hypotheses"]["status"]=="TMINUS1_COTRAVEL_ORDER"
                for x in rounded
            ),
            "odd_engine_cost_controls_in_target_turns":len(odd_controls),
            "odd_engine_cost_controls_ceil_matches":sum(x["ceil_matched"] for x in odd_controls),
        },
        "by_original_class":dict(sorted(by_class.items())),
        "by_race":dict(sorted(by_race.items())),
        "by_Tminus1_engine_id":dict(sorted(by_engine.items())),
        "turn_audit":turn_index,
        "all_residual_vcr_sides":all_cases,
        "odd_engine_cost_control_summary":dict(sorted(Counter(
            f"engine_cost={x['engine_cost_mc']} original={x['original_class']} ceil={x['ceil_matched']} phase={x['phase_support']}"
            for x in odd_controls).items())),
        "odd_engine_cost_controls_first_100":odd_controls[:100],
        "references":{
            "shield_generators":"https://help.planets.nu/abil-shield-generator",
            "horwasp":"https://help.planets.nu/horwasp-ships",
        },
        "evidence_boundary":BOUNDARY,
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--corpus-db-generation",required=True)
    p.add_argument("--survey-summary",type=Path,required=True)
    p.add_argument("--digest",type=Path,required=True)
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        survey=json.loads(a.survey_summary.read_text(encoding="utf-8"))
        digest=json.loads(a.digest.read_text(encoding="utf-8"))
        conn,path=connect_compact_generation_read_only(
            a.corpus_db_generation,a.corpus_db_root
        )
        try:
            if survey.get("config",{}).get("db_generation")!=a.corpus_db_generation:
                raise ValueError("survey DB generation identity mismatch")
            report=build_report(conn=conn,survey=survey,digest=digest,
                                checkpoint_dir=a.checkpoint_dir,db_path=str(path))
        finally:
            conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print("===== COMPLETE COMBAT MASS RESIDUAL VCR AUDIT =====")
        print("status:",report["status"])
        print("summary:",report["summary"])
        print("by_original_class:",report["by_original_class"])
        print("by_race:",report["by_race"])
        print("by_Tminus1_engine_id:",report["by_Tminus1_engine_id"])
        print("odd_cost_rounding_counts:",report["odd_engine_cost_control_summary"])
        for x in report["all_residual_vcr_sides"]:
            print(f"G{x['game_id']} T{x['turn']} V{x['vcr_id']} "
                  f"side={x['side']} ship={x['ship_id']} "
                  f"race={x['race']} engine={x['tminus1_owner_engine_id']} "
                  f"hullmass={x['catalog_hull_mass']} factual={x['observed_vcr_mass']} "
                  f"delta={x['observed_delta_from_base']} "
                  f"rounding_candidates={x['ceil_rounding_hypotheses']['match_candidates']}")
        print("output:",a.output)
        return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
