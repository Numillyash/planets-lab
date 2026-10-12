"""Research-only version-gated Horwasp postcombat model falsification.

Re-evaluates *both fixed* counterfactual branches (fighter-feedback OFF/ON)
using immutable T-1 clans and previous-VCR Classic replay. No coefficients,
branches or game periods are selected to improve factual VCR-mass agreement.

Official rule: fighter-kill feedback starts for games generated on/after
2021-01-01. Historical archive metadata may not expose an authoritative
game-creation timestamp: missing/ambiguous records ABSTAIN; do NOT infer
it from game ID, current turn, observations or a release date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
import combat_horwasp_terminal_continuity_v1 as continuity
import combat_horwasp_postcombat_clan_projection_v1 as previous

from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,member_refs_for_turns,reconstruct_members
)
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns

SCHEMA="planets-lab.combat-horwasp-fighter-feedback-gate.v1"
STATUS="HORWASP_2021_FEEDBACK_GATE_COUNTERFACTUAL_NOT_PROMOTED"
SOURCE_BLOB="d58fc71d414a08f2a60618981ee3c550b7d7bf2a"
TERMINAL_BLOB=previous.TERMINAL_V1_BLOB
HORWASP_BLOB=previous.HORWASP_V1_BLOB
DB_GENERATION=previous.GENERATION
DB_SHA256=previous.GENERATION_SHA256
CUTOFF=dt.date(2021,1,1)
AUTHORITATIVE_KEYS=("datecreated","creationdate","createdate","gamecreatedat")
AMBIGUOUS_KEYS=("created","createdat","created_at","startdate")


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def progress(s:str)->None:
    print(f"[feedback-gate] {s}",flush=True)


def read_frozen(path:Path,blob:str)->dict[str,Any]:
    raw=path.read_bytes()
    if continuity.blob_sha1(raw)!=blob:
        raise ValueError(f"immutable published JSON blob mismatch: {path}")
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError("frozen report is not JSON object")
    return obj


def parse_date(x:Any)->dt.date|None:
    """Parse only explicit ISO UTC dates; never mistake Nu year or turn for UTC."""
    if not isinstance(x,str):return None
    s=x.strip()
    try:
        if len(s)>=10 and s[4]=="-" and s[7]=="-":
            return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None
    return None


def game_creation_provenance(historical:list[tuple[Any,Mapping[str,Any]]],
                             *,game:int,turn:int)->dict[str,Any]:
    """Direct T-1 game metadata only; never use inferred game ID chronology."""
    fields=[]
    if not historical:
        return {"status":"ABSTAIN_NO_TMINUS1_ARCHIVE",
                "rule_applies_since_2021":None,"observations":[]}
    for ref,member in historical:
        record=member.get("game")
        if (ref.game_id!=game or ref.archive_turn!=turn-1 or
            ref.embedded_turn!=turn-1 or not isinstance(record,Mapping) or
            integer(record.get("id"))!=game or
            integer(record.get("turn"))!=turn-1):
            return {"status":"ABSTAIN_TMINUS1_PROVENANCE_INVALID",
                    "rule_applies_since_2021":None,"observations":[]}
        keys={str(k).lower().replace("_",""):v for k,v in record.items()}
        candidates=[]
        for key in (*AUTHORITATIVE_KEYS,*AMBIGUOUS_KEYS):
            norm=key.replace("_","")
            if norm in keys:
                candidates.append({"field":key,"raw_value":keys[norm],
                    "iso_date":str(parse_date(keys[norm]))
                        if parse_date(keys[norm]) else None,
                    "semantically_authoritative":key in AUTHORITATIVE_KEYS})
        fields.append({"member_id":ref.member_id,
                       "player_id":ref.perspective_player_id,
                       "date_candidates":candidates})
    dates={x["iso_date"] for row in fields
           for x in row["date_candidates"]
           if x["semantically_authoritative"] and x["iso_date"] is not None}
    unknown=sum(not any(x["semantically_authoritative"] and x["iso_date"]
                        for x in row["date_candidates"])
                for row in fields)
    if len(dates)!=1 or unknown:
        status=("ABSTAIN_GAME_CREATED_DATE_CONFLICT" if len(dates)>1 else
                "ABSTAIN_GAME_CREATED_DATE_NOT_AUTHENTICATED")
        return {"status":status,"rule_applies_since_2021":None,
                "observations":fields}
    date=dt.date.fromisoformat(next(iter(dates)))
    return {"status":"ARCHIVED_GAME_CREATION_DATE_CANDIDATE",
            "rule_applies_since_2021":date>=CUTOFF,
            "creation_date_candidate":str(date),"observations":fields,
            "source_is_game_metadata_not_independent_host_executable":True}


def branch_step(*,clans:Any,capacity:Any,hull_mass:Any,hull_id:Any,
                start_fighters:Any,terminal_fighters:Any,terminal_damage:Any,
                start_damage:Any,terminal_destroyed:Any,terminal_captured:Any,
                feedback_enabled:bool)->dict[str,Any]:
    """Prior-only branch. OFF/ON chosen before seeing any next VCR observations."""
    def abstain(label:str)->dict[str,Any]:
        return {"status":label,"projected_clans":None,
                "projected_mass_KT":None,"projected_fighters":None}
    nums=(clans,capacity,hull_mass,hull_id,start_fighters,
          terminal_fighters,terminal_damage,start_damage)
    if any(integer(x) is None for x in nums):
        return abstain("ABSTAIN_MISSING_PRECOMBAT_OR_CLASSIC_FIELDS")
    if (clans<0 or capacity<=0 or clans>capacity or hull_mass<=0 or hull_id<=0 or
        start_fighters<0 or terminal_fighters<0 or terminal_fighters>start_fighters or
        terminal_damage<0 or terminal_damage>100 or start_damage!=0):
        return abstain("ABSTAIN_INVALID_MODEL_PRESTATE")
    if terminal_destroyed is True or terminal_captured is True:
        return abstain("ABSTAIN_CLASSIC_TERMINAL_DEFEAT")
    factor=previous.HULL_FIGHTER_CLAN_KILL.get(hull_id)
    if factor is None and feedback_enabled:
        return abstain("ABSTAIN_FIGHTER_FEEDBACK_HULL_UNKNOWN")
    lost=start_fighters-terminal_fighters
    damage_loss=capacity*terminal_damage//100
    feedback_loss=lost*(factor or 0) if feedback_enabled else 0
    after=clans-damage_loss-feedback_loss
    if after<0:
        return abstain("ABSTAIN_INSUFFICIENT_CLANS_FULL_REPAIR")
    mass=hull_mass+hull_mass*after//capacity
    spec=previous.HULL_FIGHTER_CAP.get(hull_id)
    fighters=(spec[1]+after*(spec[0]-spec[1])//capacity
              if spec is not None else None)
    return {
        "status":"COUNTERFACTUAL_FIGHTER_FEEDBACK_"+("ON" if feedback_enabled else "OFF"),
        "feedback_enabled":feedback_enabled,
        "prior_clans":clans,"fighter_start":start_fighters,
        "classic_terminal_fighters":terminal_fighters,
        "classic_terminal_damage":terminal_damage,
        "fighter_loss_proxy":lost,
        "damage_clans_lost_floor_assumption":damage_loss,
        "feedback_clans_lost_hypothesis":feedback_loss,
        "projected_clans":after,"projected_mass_KT":mass,
        "projected_fighters":fighters,
        "classic_replay_host_terminal_equivalence_proven":False,
        "factual_next_mass_used":False,
    }


def candidate_pair(prestate:Mapping[str,Any],tr:Mapping[str,Any],
                   prior_party:Mapping[str,Any],
                   old_clans:dict[str,int|None])->dict[str,dict[str,Any]]:
    """Never accesses next start, next mass or next fighters."""
    fields=tr["terminal_next_continuity"]["fields"]
    flag=tr["terminal_next_continuity"]
    answer={}
    for mode in ("OFF","ON"):
        answer[mode]=branch_step(
            clans=old_clans[mode],
            capacity=prestate["cargo_capacity"],
            hull_mass=prestate["hull_mass_KT"],
            hull_id=prestate["hull_id"],
            start_fighters=prior_party.get("fighters"),
            terminal_fighters=fields["fighters"]["previous_replay_terminal"],
            terminal_damage=fields["damage"]["previous_replay_terminal"],
            start_damage=prior_party.get("damage"),
            terminal_destroyed=flag.get("terminal_destroyed"),
            terminal_captured=flag.get("terminal_captured"),
            feedback_enabled=mode=="ON")
    return answer


def evaluate_only_after(candidates:Mapping[str,Mapping[str,Any]],
                        *,actual_mass:int,actual_fighters:int)->dict[str,Any]:
    r={}
    for mode,item in candidates.items():
        mass=item["projected_mass_KT"]
        fighters=item["projected_fighters"]
        r[mode]={
            "factual_next_mass_KT":actual_mass,
            "factual_next_fighters":actual_fighters,
            "mass_error_factual_minus_candidate_KT":(
                actual_mass-mass if mass is not None else None),
            "mass_exact":mass==actual_mass if mass is not None else None,
            "fighters_exact":fighters==actual_fighters if fighters is not None else None}
    return r


def run_audit(horwasp:Mapping[str,Any],terminal:Mapping[str,Any],conn:Any)->dict[str,Any]:
    targets,controls=previous.validate_sources(terminal,horwasp)
    game_turns=sorted({key[:2] for key in targets})
    if len(game_turns)!=3:raise ValueError("frozen game-turn coverage drift")
    archives={}
    cases={}
    dates={}
    for i,(game,turn) in enumerate(game_turns,1):
        progress(f"[{i}/{len(game_turns)}] G{game} T{turn}: archived creation-date provenance and VCR data")
        refs=member_refs_for_turns(conn,game_id=game,turns={turn-1},
                                  include_embedded_turn=False)
        historical=list(reconstruct_members(conn,refs))
        dates[str(game)]=game_creation_provenance(
            historical,game=game,turn=turn)
        cases[(game,turn)]=combat_vcr_cases_for_turns(
            conn,game_id=game,battle_turns={turn})
    rows=[]
    for key,chain in sorted(targets.items()):
        start=previous.from_tminus1(horwasp,key)
        state={"OFF":start["clans"],"ON":start["clans"]}
        game,turn,owner,ship=key
        for tr in sorted(chain,key=lambda r:r["prior_VCR_id"]):
            previous_case=cases[(game,turn)].get((turn,tr["prior_VCR_id"]))
            next_case=cases[(game,turn)].get((turn,tr["next_VCR_id"]))
            if previous_case is None or next_case is None:
                raise ValueError("missing frozen VCR source")
            side=tr["prior_side"]
            party=previous_case.payload.get(side)
            if (not isinstance(party,Mapping) or
                integer(party.get("objectid"))!=ship or
                integer(party.get("hullid"))!=start["hull_id"] or
                integer(previous_case.payload.get(side+"ownerid"))!=owner):
                raise ValueError("prior VCR identity drift")
            # Forbid reading next comparator before candidate construction.
            candidates=candidate_pair(start,tr,party,state)
            nxt=next_case.payload.get(tr["next_side"])
            if (not isinstance(nxt,Mapping) or
                integer(nxt.get("objectid"))!=ship or
                integer(nxt.get("hullid"))!=start["hull_id"] or
                integer(next_case.payload.get(tr["next_side"]+"ownerid"))!=owner):
                raise ValueError("next VCR identity drift")
            mass,fighters=integer(nxt.get("mass")),integer(nxt.get("fighters"))
            if (mass is None or fighters is None or
                mass!=tr["terminal_next_continuity"]["next_mass_is_only_observational"] or
                fighters!=tr["terminal_next_continuity"]["fields"]["fighters"]["next_factual_start"]):
                raise ValueError("frozen next comparator drift")
            comparisons=evaluate_only_after(
                candidates,actual_mass=mass,actual_fighters=fighters)
            date=dates[str(game)]
            allowed_mode=("ON" if date["rule_applies_since_2021"] else "OFF"
                          if date["rule_applies_since_2021"] is False else None)
            rows.append({
                "game_id":game,"turn":turn,"ship_id":ship,"hull_id":start["hull_id"],
                "from_VCR":tr["prior_VCR_id"],"to_VCR":tr["next_VCR_id"],
                "historical_game_creation_date_gate":date["status"],
                "historical_gate_rule_enabled":date["rule_applies_since_2021"],
                "gate_selected_mode":allowed_mode,
                "prior_only_counterfactual_candidates":candidates,
                "after_forecast_comparisons":comparisons,
                "gate_selected_candidate_is_exact":(
                    comparisons[allowed_mode]["mass_exact"]
                    if allowed_mode is not None else None),
                "VCR_ID_order_independently_proven":False,
                "Classic_terminal_equals_Host_terminal_proven":False})
            # Always carry MODEL state, never actual inverted clans.
            state={m:candidates[m]["projected_clans"] for m in ("ON","OFF")}
    if len(rows)!=5 or sum(len(x) for x in controls.values())!=15:
        raise ValueError("frozen 5+15 population drift")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_postcombat_git_blob_sha1":SOURCE_BLOB,
        "source_terminal_git_blob_sha1":TERMINAL_BLOB,
        "source_horwasp_git_blob_sha1":HORWASP_BLOB,
        "source_db_sha256":DB_SHA256,
        "historical_creation_date_provenance":dates,
        "summary":{
            "horwasp_transitions":5,
            "ordinary_controls":15,
            "creation_date_gate_statuses":dict(sorted(Counter(
                x["historical_game_creation_date_gate"] for x in rows
            ).items())),
            "game_creation_dates_authoritatively_proven":False,
            "branch_OFF_mass_exact":sum(
                x["after_forecast_comparisons"]["OFF"]["mass_exact"] is True for x in rows),
            "branch_ON_mass_exact":sum(
                x["after_forecast_comparisons"]["ON"]["mass_exact"] is True for x in rows),
            "branch_OFF_fighters_exact":sum(
                x["after_forecast_comparisons"]["OFF"]["fighters_exact"] is True for x in rows),
            "branch_ON_fighters_exact":sum(
                x["after_forecast_comparisons"]["ON"]["fighters_exact"] is True for x in rows),
            "gate_selected_mass_exact":sum(
                x["gate_selected_candidate_is_exact"] is True for x in rows),
            "gate_unresolved_sides":sum(x["gate_selected_mode"] is None for x in rows),
            "full_Host_mass_or_clan_loss_reconstructed":False},
        "all_five_transition_version_controls":rows,
        "boundary":(
            "2021-era feedback documented as conditional on game generation, "
            "not the turn date or game ID. Historical date keys, if any, "
            "are only metadata candidates and require provenance verification. "
            "Fixed ON/OFF branches are exploratory counterfactuals, not an "
            "oracle-selected model. Classic terminal outcomes, damage rounding, "
            "battle order and fighter-loss proxy are not independently verified. "
            "Never use N+1 mass/fighters to generate any candidate. "
            "No production, executor, corpus CURRENT or engine rule changes.")
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-postcombat",type=Path,required=True)
    p.add_argument("--frozen-terminal",type=Path,required=True)
    p.add_argument("--frozen-horwasp",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        frozen=read_frozen(a.frozen_postcombat,SOURCE_BLOB)
        terminal=read_frozen(a.frozen_terminal,TERMINAL_BLOB)
        horwasp=read_frozen(a.frozen_horwasp,HORWASP_BLOB)
        if (frozen.get("schema")!=previous.SCHEMA or
            frozen.get("status")!=previous.STATUS or
            frozen.get("summary",{}).get("original_horwasp_transitions")!=5 or
            frozen.get("summary",{}).get("model_mass_numeric_equal")!=1 or
            frozen.get("summary",{}).get("model_mass_numeric_nonequal")!=4):
            raise ValueError("frozen failed forward model evidence drift")
        previous.validate_sources(terminal,horwasp)
        db=a.corpus_db_root/DB_GENERATION
        if not db.is_file():raise ValueError("explicit immutable public100 missing")
        progress(f"verifying immutable SHA256: {db.name}")
        t=time.monotonic()
        with db.open("rb") as f: sha=hashlib.file_digest(f,"sha256").hexdigest()
        if sha!=DB_SHA256:raise ValueError("pinned SHA256 mismatch")
        progress(f"SHA256 verified in {time.monotonic()-t:.1f}s")
        conn,path=connect_compact_generation_read_only(DB_GENERATION,a.corpus_db_root)
        try:report=run_audit(horwasp,terminal,conn)
        finally:conn.close()
        report["source_db_path"]=str(path)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (KeyError,ValueError,TypeError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== HORWASP PRE-2021 VS 2021 FEEDBACK RULE GATE V1 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    for x in report["all_five_transition_version_controls"]:
        print(f"G{x['game_id']} V{x['from_VCR']}->{x['to_VCR']}",
              "gate:",x["gate_selected_mode"],
              "OFF err:",x["after_forecast_comparisons"]["OFF"]["mass_error_factual_minus_candidate_KT"],
              "ON err:",x["after_forecast_comparisons"]["ON"]["mass_error_factual_minus_candidate_KT"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
