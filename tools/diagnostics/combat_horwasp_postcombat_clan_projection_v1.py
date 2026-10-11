"""Research-only Horwasp N->N+1 clan/mass projection from documented rules.

T-1 clans/capacity/mass: immutable Horwasp V1 evidence. VCR N's fighter
start count: current N payload. Combat N terminal damage/fighters: frozen
Classic replay V1 evidence. Documentation supplies damage-heals-by-clans,
fighter feedback kills, and fighter regeneration formulas. Calculate
new clans and next mass/fighter counts BEFORE opening N+1 comparator.

A derived Classic replay is NOT an independently verified Host terminal,
and VCR-ID order is NOT independently established. Results are falsifiable
conditional phase hypotheses, NEVER full NuHost predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
import combat_horwasp_terminal_continuity_v1 as continuity

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only

SCHEMA="planets-lab.combat-horwasp-postcombat-clan-projection.v1"
STATUS="DOCUMENTED_RULE_CONDITIONAL_HOST_PHASE_NOT_PROMOTED"
TERMINAL_V1_BLOB="04144af2d862a5040d822648f93bfeca8d22c1eb"
HORWASP_V1_BLOB="358c354d424907488dffd3665e6d6d07c8d04f64"
HULL_FIGHTER_CAP={115:(70,10),117:(70,10),119:(40,10)}
HULL_FIGHTER_CLAN_KILL={115:20,117:2,119:2,210:2}
GENERATION=continuity.GENERATION
GENERATION_SHA256=continuity.GENERATION_SHA256


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def progress(x:str)->None:
    print(f"[horwasp-postcombat] {x}",flush=True)


def read_verified(path:Path,sha:str)->dict[str,Any]:
    raw=path.read_bytes()
    if continuity.blob_sha1(raw)!=sha:
        raise ValueError(f"frozen evidence Git blob SHA mismatch: {path}")
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise ValueError("frozen source must be a JSON object")
    return data


def validate_sources(
    terminal:Mapping[str,Any],horwasp:Mapping[str,Any],
)->tuple[dict[tuple[int,int,int,int],list[dict[str,Any]]],
        dict[tuple[int,int,int,int],list[dict[str,Any]]]]:
    chains=continuity.frozen_horwasp_chains(horwasp)
    if (terminal.get("schema")!=continuity.SCHEMA or
        terminal.get("status")!=continuity.STATUS or
        terminal.get("source_frozen_horwasp_git_blob_sha1")!=HORWASP_V1_BLOB or
        terminal.get("source_db_sha256")!=GENERATION_SHA256 or
        terminal.get("summary",{}).get("frozen_horwasp",{}).get("transitions")!=5 or
        terminal.get("summary",{}).get("same_game_turn_non_horwasp_controls",{}).get("transitions")!=15):
        raise ValueError("frozen completed terminal V1 status/population drift")
    raw_windows=terminal.get("window_results")
    if not isinstance(raw_windows,list) or len(raw_windows)!=3:
        raise ValueError("three frozen windows required")
    target={}
    control={}
    for w in raw_windows:
        for row in w.get("transitions",[]):
            key=(row.get("game_id"),row.get("turn"),row.get("owner_id"),row.get("ship_id"))
            if not all(integer(v) is not None and v>0 for v in key):
                raise ValueError("invalid source transition identity")
            kind=row.get("cohort")
            if kind=="FROZEN_HORWASP_REPEAT":
                target.setdefault(key,[]).append(row)
            elif kind=="SAME_GAME_TURN_CONTROL":
                control.setdefault(key,[]).append(row)
            else:
                raise ValueError("unknown frozen transition cohort")
    if set(target)!=set(chains) or sum(map(len,target.values()))!=5 or sum(map(len,control.values()))!=15:
        raise ValueError("frozen chain control identities drift")
    for key,seq in chains.items():
        wanted=[(x["vcr_id"],y["vcr_id"]) for x,y in zip(seq,seq[1:])]
        got=[(r["prior_VCR_id"],r["next_VCR_id"]) for r in target[key]]
        if sorted(wanted)!=sorted(got):
            raise ValueError("frozen VCR pair identity mismatch")
        if any(row["raceid"]!=12 or
               row.get("prior_replay",{}).get("status")!="CLASSIC_CURRENT_VCR_REPLAY_AVAILABLE"
               for row in target[key]):
            raise ValueError("target classic replay status/race drift")
    return target,control


def from_tminus1(
    horwasp:Mapping[str,Any],key:tuple[int,int,int,int],
)->dict[str,Any]:
    rows=horwasp["frozen_horwasp_side_evaluations"]
    matches=[r for r in rows if
             (r["game_id"],r["turn"],r["owner_id"],r["ship_id"])==key]
    if not matches:
        raise ValueError("frozen T-1 owner ship missing")
    tuples={
        (r["hull_id"],r["independent_Tminus1_clans"],
         r["independent_Tminus1_cargo_capacity"],
         r["Tminus1_static_hull_mass_KT"],r["Tminus1_owner_ship_status"])
        for r in matches
    }
    if len(tuples)!=1:
        raise ValueError("conflicting frozen T-1 ship prestate")
    hull,clans,cap,mass,status=next(iter(tuples))
    if (status!="RESOLVED_TMINUS1_OWNER_SHIP" or
        any(integer(v) is None for v in (hull,clans,cap,mass)) or
        clans<0 or clans>cap or cap<=0 or mass<=0):
        raise ValueError("invalid frozen Horwasp T-1 clans/capacity")
    return {"hull_id":hull,"clans":clans,"cargo_capacity":cap,"hull_mass_KT":mass}


def documented_damage_and_fighter_loss_candidate(
    *,previous_clans:int,capacity:int,hull_id:int,
    current_vcr_start_fighters:Any,classic_replay_terminal_fighters:Any,
    classic_replay_terminal_damage:Any,
    classic_replay_destroyed:Any,classic_replay_captured:Any,
    previous_vcr_start_damage:Any,
)->dict[str,Any]:
    """No N+1 values accepted; documented rules under Classic-terminal assumption."""
    def abstain(why:str,detail:dict[str,Any]|None=None)->dict[str,Any]:
        return {"status":why,"projected_clans":None,
                "projected_next_mass_KT":None,
                "projected_next_fighters":None,
                "detail":detail or {},"full_combat_mass_prediction":False}
    args=(previous_clans,capacity,hull_id)
    if any(integer(x) is None for x in args) or previous_clans<0 or capacity<=0 or previous_clans>capacity:
        return abstain("ABSTAIN_INVALID_PRESTATE")
    start=integer(current_vcr_start_fighters)
    terminal=integer(classic_replay_terminal_fighters)
    damage=integer(classic_replay_terminal_damage)
    start_damage=integer(previous_vcr_start_damage)
    if any(x is None for x in (start,terminal,damage,start_damage)):
        return abstain("ABSTAIN_UNSUPPORTED_CLASSIC_FIELDS")
    if classic_replay_destroyed is True or classic_replay_captured is True:
        return abstain("ABSTAIN_CLASSIC_REPLAY_TERMINAL_DEFEAT")
    if (start<0 or terminal<0 or terminal>start or damage<0 or damage>100
            or start_damage!=0):
        return abstain("ABSTAIN_NONBASELINE_VCR_DAMAGE_OR_FIGHTER_COUNTS")
    kill_per_fighter=HULL_FIGHTER_CLAN_KILL.get(hull_id)
    if kill_per_fighter is None:
        return abstain("ABSTAIN_UNDOCUMENTED_HULL_FIGHTER_FEEDBACK")
    fighter_lost=start-terminal
    fighter_clans=fighter_lost*kill_per_fighter
    # Source states damage percent of cargo capacity; truncation is an explicit
    # numeric hypothesis, not independently demonstrated Host rounding.
    damage_clans=capacity*damage//100
    total=fighter_clans+damage_clans
    detail={"fighter_start":start,"fighter_replay_terminal":terminal,
            "lost_fighters_from_Classic_replay":fighter_lost,
            "clan_loss_per_lost_fighter":kill_per_fighter,
            "hypothetical_fighter_clans_killed":fighter_clans,
            "classic_terminal_damage_percent":damage,
            "hypothetical_damage_clans_killed":damage_clans,
            "total_hypothetical_clan_loss":total,
            "floor_damage_rounding_unverified":True,
            "assuming_classic_replay_matches_host_terminal":True}
    if total>previous_clans:
        return abstain("ABSTAIN_INSUFFICIENT_CLANS_FOR_FULL_REPAIR",detail)
    remaining=previous_clans-total
    return {"status":"CONDITIONAL_DOCUMENTED_POSTCOMBAT_CLAN_PROJECTION",
            "projected_clans":remaining,"detail":detail,
            "full_combat_mass_prediction":False,
            "projected_next_fighters":None,
            "clan_phase_order_independently_proven":False}


def next_mass_and_fighters(
    projection:dict[str,Any], *,hull_mass:int,hull_id:int,
    capacity:int,
)->dict[str,Any]:
    result=dict(projection)
    clans=result.get("projected_clans")
    if integer(clans) is None:
        return result
    if (integer(hull_mass) is None or hull_mass<=0 or
        integer(capacity) is None or capacity<=0 or
        clans<0 or clans>capacity):
        raise ValueError("invalid mass projection input")
    result["projected_next_mass_KT"]=hull_mass+hull_mass*clans//capacity
    fighter_specs=HULL_FIGHTER_CAP.get(hull_id)
    result["projected_next_fighters"]=(
        fighter_specs[1]+clans*(fighter_specs[0]-fighter_specs[1])//capacity
        if fighter_specs is not None else None
    )
    return result


def field_reset_signature(r:Mapping[str,Any])->dict[str,Any]:
    """Descriptive only; terminal/next fields existed in frozen V1."""
    fields=r.get("terminal_next_continuity",{}).get("fields",{})
    if set(fields)!=set(continuity.CARRY_FIELDS):
        raise ValueError("missing frozen five-field carry comparator")
    result={}
    for name,value in fields.items():
        terminal=integer(value.get("previous_replay_terminal"))
        nxt=integer(value.get("next_factual_start"))
        if terminal is None or nxt is None:
            raise ValueError("frozen carry comparator truncated")
        result[name]={"equal":terminal==nxt,
                      "terminal":terminal,"next_start":nxt,
                      "increased_from_classic_terminal":nxt>terminal,
                      "next_reset_zero":nxt==0 and terminal!=0,
                      "next_reset_10000":nxt==10000 and terminal!=10000}
    return result


def audit(
    horwasp:Mapping[str,Any],terminal:Mapping[str,Any],conn:Any,
)->dict[str,Any]:
    targets,controls=validate_sources(terminal,horwasp)
    groups={}
    for key in sorted(targets):
        game,turn,owner,ship=key
        if (game,turn) not in groups:
            progress(f"G{game} T{turn}: loading factual current VCRs, not T+1 ship snapshots")
            groups[(game,turn)]=combat_vcr_cases_for_turns(
                conn,game_id=game,battle_turns={turn})
    rows=[]
    for key,transitions in sorted(targets.items()):
        initial=from_tminus1(horwasp,key)
        clans=initial["clans"]
        for i,tr in enumerate(sorted(transitions,key=lambda x:x["prior_VCR_id"])):
            cases=groups[key[:2]]
            prior=cases.get((key[1],tr["prior_VCR_id"]))
            if prior is None:
                raise ValueError("frozen prior VCR missing")
            p=prior.payload.get(tr["prior_side"])
            if not isinstance(p,Mapping) or integer(p.get("objectid"))!=key[3] or integer(prior.payload.get(tr["prior_side"]+"ownerid"))!=key[2]:
                raise ValueError("prior VCR ship/owner identity drift")
            if integer(p.get("hullid"))!=initial["hull_id"] or integer(p.get("raceid"))!=12:
                raise ValueError("prior VCR hull/race identity drift")
            fields=tr["terminal_next_continuity"]["fields"]
            flags=tr["terminal_next_continuity"]
            # Do not read next VCR until all candidate fields are calculated.
            model=next_mass_and_fighters(
                documented_damage_and_fighter_loss_candidate(
                    previous_clans=clans,capacity=initial["cargo_capacity"],
                    hull_id=initial["hull_id"],
                    current_vcr_start_fighters=p.get("fighters"),
                    previous_vcr_start_damage=p.get("damage"),
                    classic_replay_terminal_fighters=fields["fighters"]["previous_replay_terminal"],
                    classic_replay_terminal_damage=fields["damage"]["previous_replay_terminal"],
                    classic_replay_destroyed=flags.get("terminal_destroyed"),
                    classic_replay_captured=flags.get("terminal_captured"),
                ),
                hull_mass=initial["hull_mass_KT"],hull_id=initial["hull_id"],
                capacity=initial["cargo_capacity"],
            )
            next_case=cases.get((key[1],tr["next_VCR_id"]))
            if next_case is None:
                raise ValueError("frozen later VCR missing")
            next_side=next_case.payload.get(tr["next_side"])
            if not isinstance(next_side,Mapping) or integer(next_side.get("objectid"))!=key[3] or integer(next_side.get("hullid"))!=initial["hull_id"] or integer(next_side.get("raceid"))!=12 or integer(next_case.payload.get(tr["next_side"]+"ownerid"))!=key[2]:
                raise ValueError("next VCR identity drift")
            observed_mass=integer(next_side.get("mass"))
            observed_fighters=integer(next_side.get("fighters"))
            if observed_mass is None or observed_fighters is None:
                raise ValueError("missing next VCR mass/fighters comparator")
            if observed_mass!=tr["terminal_next_continuity"].get("next_mass_is_only_observational") or observed_fighters!=fields["fighters"]["next_factual_start"]:
                raise ValueError("frozen next VCR comparator changed")
            rows.append({
                "game_id":key[0],"turn":key[1],"owner_id":key[2],
                "ship_id":key[3],"hull_id":initial["hull_id"],
                "transition_index_by_VCR_ID":i,
                "from_VCR":tr["prior_VCR_id"],"to_VCR":tr["next_VCR_id"],
                "source_clans_Tminus1":initial["clans"],
                "hypothesized_clans_before_N":clans,
                "model_before_next_VCR_comparison":model,
                "after_forecast_observed": {
                    "mass_KT":observed_mass,"fighters":observed_fighters,
                    "mass_candidate_matches":(
                        observed_mass==model["projected_next_mass_KT"]
                        if model["projected_next_mass_KT"] is not None else None
                    ),
                    "fighters_candidate_matches":(
                        observed_fighters==model["projected_next_fighters"]
                        if model["projected_next_fighters"] is not None else None
                    ),
                    "mass_residual_KT":(
                        observed_mass-model["projected_next_mass_KT"]
                        if model["projected_next_mass_KT"] is not None else None
                    )
                },
                "reset_signature_observation_only":field_reset_signature(tr),
                "VCR_ID_execution_order_proven":False,
                "terminal_clans_true_Host_reconstruction":False,
            })
            # Never repair a bad forecast by solving actual clans from N+1 mass.
            if model["projected_clans"] is not None:
                clans=model["projected_clans"]
            else:
                # No model state for N+1: subsequent transition abstains.
                clans=None
    # Controls from same immutable terminal evidence; no model on non-Horwasp.
    control_rows=[r for seq in controls.values() for r in seq]
    all_rows=[r for seq in targets.values() for r in seq]
    if len(rows)!=5 or len(control_rows)!=15:
        raise ValueError("frozen 5+15 transitions not reproduced")
    def signatures(items):
        return {
            "transitions":len(items),
            "field_changed_counts":dict(sorted(Counter(
                field for r in items
                for field,data in field_reset_signature(r).items()
                if not data["equal"]
            ).items())),
            "terminal_damage_resets_to_zero":sum(
                field_reset_signature(r)["damage"]["next_reset_zero"]
                for r in items
            ),
            "terminal_torpedoes_resets_to_10000":sum(
                field_reset_signature(r)["torpedoes"]["next_reset_10000"]
                for r in items
            ),
            "fighters_increase_over_Classic_terminal":sum(
                field_reset_signature(r)["fighters"]["increased_from_classic_terminal"]
                for r in items
            ),
        }
    evals=[r for r in rows if r["model_before_next_VCR_comparison"]["projected_next_mass_KT"] is not None]
    fighter_evals=[r for r in rows if r["model_before_next_VCR_comparison"]["projected_next_fighters"] is not None]
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_terminal_v1_git_blob_sha1":TERMINAL_V1_BLOB,
        "source_horwasp_v1_git_blob_sha1":HORWASP_V1_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":GENERATION_SHA256,
        "summary":{
            "original_horwasp_transitions":len(rows),
            "ordinary_controls":signatures(control_rows),
            "horwasp_reset_observations":signatures(all_rows),
            "documented_rule_candidate_statuses":dict(sorted(Counter(
                r["model_before_next_VCR_comparison"]["status"] for r in rows
            ).items())),
            "model_mass_evaluable":len(evals),
            "model_mass_numeric_equal":sum(r["after_forecast_observed"]["mass_candidate_matches"] is True for r in evals),
            "model_mass_numeric_nonequal":sum(r["after_forecast_observed"]["mass_candidate_matches"] is False for r in evals),
            "model_fighters_evaluable":len(fighter_evals),
            "model_fighters_numeric_equal":sum(r["after_forecast_observed"]["fighters_candidate_matches"] is True for r in fighter_evals),
            "model_input_uses_later_VCR_mass_or_fighters":False,
            "Host_execution_order_proven":False,
            "true_host_terminal_clans_reconstructed":False,
        },
        "all_five_horwasp_forward_transition_audits":rows,
        "boundary":(
            "Published Classic replay N terminal damage/fighters and factual N "
            "start fighters, with independently archived T-1 clans, generate "
            "conditional official-rule clan/mass/fighter candidate BEFORE N+1 "
            "is used only as comparator. N payload/seed and previous derived "
            "replay are observed, not independently predicted. Fighter-loss "
            "proxy (start minus terminal), integer rounding and order of loss "
            "are hypotheses. A model mismatch is reported rather than tuned. "
            "No VCR ID timing proof, Host replay equivalence, or production "
            "executor promotion."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-terminal-v1",type=Path,required=True)
    parser.add_argument("--frozen-horwasp-v1",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    try:
        terminal=read_verified(a.frozen_terminal_v1,TERMINAL_V1_BLOB)
        horwasp=read_verified(a.frozen_horwasp_v1,HORWASP_V1_BLOB)
        validate_sources(terminal,horwasp)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("explicit pinned public100 DB missing")
        t=time.monotonic()
        progress(f"verifying immutable corpus SHA256: {db.name}")
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=GENERATION_SHA256:raise ValueError("pinned corpus sha mismatch")
        progress(f"SHA256 verified in {time.monotonic()-t:.1f}s; opening read-only")
        conn,path=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=audit(horwasp,terminal,conn)
        finally:conn.close()
        report["db_path"]=str(path)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2
    print("===== DOCUMENTED HORWASP POSTCOMBAT PHASE CONDITIONAL V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
