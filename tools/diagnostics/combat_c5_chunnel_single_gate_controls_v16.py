"""V16: independent T-1 necessary-condition discriminators on V15 60-window cohort.

We examine stock Firecloud -> stock Firecloud *intent* where a unique
same-owner last-three-digit FC target exists; compare a fully eligible
stationary pair with single-failed-gate candidates. This is NOT a
Chunnel activation oracle. T archive is an after-Host comparator; T-1
Tow order, target Warp and positional changes may be phase dependent.

ALL T-1 lists and failure categories freeze before the FIRST T archive
read. V15's 95 original valid Firecloud pairs are checked exactly.
No N+1 VCR, production Host movement rule or combat executor changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping
from math import hypot
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for d in (ROOT/"src",Path(__file__).resolve().parent):
    if str(d) not in sys.path:sys.path.insert(0,str(d))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.reconstruction import group_perspective_records
from combat_host_candidate_set_audit import _owner_rows_for_turn,TOW_MISSION_ID
import combat_c5_chunnel_actor_outcome_audit_v15 as v15
import combat_c5_chunnel_endpoint_screen_v11 as v11
import combat_c5_site_disjoint_movement_validation_v9 as v9

SCHEMA="planets-lab.combat-c5-chunnel-single-gate-controls.v16"
STATUS="TMINUS1_SINGLE_FAILED_CHUNNEL_GATES_OBSERVATIONAL_CONTROLS"
V15_BLOB="59f39fdb73779a80c14148d07e30c84e27d699d3"
GENERATION=v15.GENERATION
SHA256=v15.SHA256
HULL_ID=56


def strict_int(x:Any)->int|None:
    return x if type(x) is int else None


def xy(x:Any)->tuple[int,int]|None:
    return v11.coordinate(x)


def git_pinned(path:Path)->dict[str,Any]:
    blob=path.read_bytes()
    digest=hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\x00"+blob).hexdigest()
    if digest!=V15_BLOB:raise ValueError("V15 pinned report Git blob changed")
    src=json.loads(blob)
    if not isinstance(src,dict):raise ValueError("V15 source not JSON object")
    return src


def frozen_v15(source:Mapping[str,Any]):
    if (source.get("schema")!=v15.SCHEMA or
        source.get("status")!=v15.STATUS or
        source.get("source_v14_git_blob_sha1")!=v15.V14_BLOB or
        source.get("source_db_sha256")!=SHA256):
        raise ValueError("V15 source schema/provenance changed")
    s=source.get("summary")
    checks={
        "frozen_V14_metadata_windows":60,"frozen_V14_games":20,
        "V14_conditional_passenger_comparisons_rechecked":55,
        "Tminus1_actor_edges_rechecked":95,
        "Tminus1_passenger_bearing_actor_edges":22,
        "Tminus1_negative_controls_rechecked":540,
        "T_negative_control_mismatch_count":8,
        "source_context_errors":0,
        "Tminus1_frozen_before_all_T_observations":True,
        "new_Host_movement_or_combat_predictions":0,
        "Chunnel_activation_proven":False,
        "Nplus1_VCR_used":False,
    }
    if not isinstance(s,Mapping) or any(s.get(k)!=v for k,v in checks.items()):
        raise ValueError("V15 frozen cohort denominators changed")
    if s.get("Tminus1_all_actor_target_after_T_outcomes")!={"T_ACTOR_AT_FROZEN_TARGET":95}:
        raise ValueError("V15 actor outcomes changed")
    original=source.get("actor_target_T_observations")
    windows=source.get("window_denominators")
    if not isinstance(original,list) or len(original)!=95 or not isinstance(windows,list) or len(windows)!=60:
        raise ValueError("V15 published case/window records missing")
    keys=set()
    originals={}
    for case in original:
        if not isinstance(case,Mapping):raise ValueError("malformed V15 actor result")
        key=tuple(strict_int(case.get(k)) for k in
                  ("game_id","turn","initiator_ship_id","target_ship_id"))
        if (None in key or min(key)<=0 or key in keys or
            case.get("T_actor_observation_status")!="T_ACTOR_AT_FROZEN_TARGET" or
            case.get("Chunnel_execution_proven") is not False):
            raise ValueError("invalid/duplicated V15 actor")
        keys.add(key)
        originals[key]=case
    selected=set()
    for item in windows:
        if not isinstance(item,Mapping):raise ValueError("malformed V15 window")
        g,t=strict_int(item.get("game_id")),strict_int(item.get("turn"))
        if g is None or t is None or g<=0 or t<2 or (g,t) in selected:
            raise ValueError("V15 window identity duplicated")
        selected.add((g,t))
    if len({g for g,_ in selected})!=20 or any((g,t) not in selected for g,t,_,_ in keys):
        raise ValueError("V15 game/window population changed")
    return tuple(sorted(selected)),originals


def potential_stock_edges(ship_rows:Mapping[int,tuple[int,Mapping[str,Any]]]):
    """Build ALL unique target intents without consulting later outcomes.

    Single-gate controls have exactly one T-1 failure of a conventional
    necessary condition, not a demonstrated Host activation failure.
    """
    by_owner_mod=defaultdict(list)
    actors=[]
    towed=set()
    for sid,(owner,raw) in ship_rows.items():
        if (strict_int(sid) is None or sid<=0 or
            strict_int(owner) is None or owner<=0 or
            not isinstance(raw,Mapping)):
            raise ValueError("invalid Tminus1 ship roster")
        if strict_int(raw.get("mission"))==TOW_MISSION_ID:
            target=strict_int(raw.get("mission1target"))
            if target is not None and target>0:towed.add(target)
        if strict_int(raw.get("hullid",raw.get("hull_id")))==HULL_ID:
            by_owner_mod[(owner,sid%1000)].append(sid)
            actors.append((sid,owner,raw))
    rows=[]
    reason=Counter()
    for sid,owner,raw in sorted(actors):
        fc=v11.numeric_target(raw.get("friendlycode",raw.get("friendly_code")))
        if fc is None:
            reason["NO_NUMERIC_FRIENDLY_CODE"]+=1
            continue
        candidates=sorted(x for x in by_owner_mod.get((owner,fc),[]) if x!=sid)
        if not candidates:
            reason["NO_SAME_OWNER_STOCK_TARGET"]+=1
            continue
        if len(candidates)!=1:
            reason["AMBIGUOUS_TARGET_IDS_ABSTAIN"]+=1
            continue
        target=candidates[0]
        t_owner,tar=ship_rows[target]
        start=xy((raw.get("x"),raw.get("y")))
        dest=xy((tar.get("x"),tar.get("y")))
        if start is None or dest is None:
            reason["START_OR_TARGET_POSITION_UNKNOWN_ABSTAIN"]+=1
            continue
        actor_fuel=strict_int(raw.get("neutronium"))
        target_fuel=strict_int(tar.get("neutronium"))
        actor_warp=strict_int(raw.get("warp"))
        target_warp=strict_int(tar.get("warp"))
        if (actor_fuel is None or target_fuel is None or
            actor_warp is None or target_warp is None):
            reason["TMINUS1_FUEL_OR_WARP_UNKNOWN_ABSTAIN"]+=1
            continue
        if actor_warp!=0:
            reason["MOVING_INITIATOR_PHASE_POSITION_UNKNOWN_ABSTAIN"]+=1
            continue
        distance=hypot(dest[0]-start[0],dest[1]-start[1])
        failed=[]
        if actor_fuel<50:failed.append("INITIATOR_FUEL_LT50")
        if target_fuel<1:failed.append("TARGET_NO_FUEL")
        if target_warp!=0:failed.append("TARGET_WARP_NONZERO_AT_TMINUS1")
        if distance<100:failed.append("DISTANCE_BELOW_100_AT_TMINUS1")
        if sid in towed or target in towed:
            failed.append("TOW_REQUEST_ON_ENDPOINT_AT_TMINUS1")
        if len(failed)==0:cohort="ALL_TMINUS1_GATES_PASS"
        elif len(failed)==1:cohort="ONE_TMINUS1_GATE_FAILS"
        else:
            reason["MULTIPLE_GATES_FAIL_ABSTAIN"]+=1
            continue
        rows.append({
            "initiator_ship_id":sid,"target_ship_id":target,
            "owner_id":owner,"source":list(start),"target":list(dest),
            "actor_Tminus1_fuel":actor_fuel,
            "target_Tminus1_fuel":target_fuel,
            "actor_Tminus1_warp":actor_warp,
            "target_Tminus1_warp":target_warp,
            "Tminus1_distance_ly":round(distance,5),
            "cohort":cohort,"single_failing_gate":failed[0] if failed else None,
            "Tminus1_target_not_selected_using_outcome":True,
            "actual_Chunnel_activation_proven":False,
        })
        reason[cohort if not failed else failed[0]]+=1
    return tuple(rows),dict(sorted(reason.items()))


def compare_observations(edge:Mapping[str,Any],observed:Mapping[int,Any],
                         *,game:int,turn:int):
    owner=edge["owner_id"]
    actor_id=edge["initiator_ship_id"]
    target_id=edge["target_ship_id"]
    astatus,actor=v15.get_observation(observed,actor_id,owner)
    tstatus,target=v15.get_observation(observed,target_id,owner)
    actor_after=xy((actor.get("x"),actor.get("y"))) if actor is not None else None
    target_after=xy((target.get("x"),target.get("y"))) if target is not None else None
    destination=xy(edge["target"])
    original=xy(edge["source"])
    if actor is None:status=astatus
    elif actor_after==destination:status="T_ACTOR_AT_PRESELECTED_TMINUS1_TARGET"
    elif actor_after==original:status="T_ACTOR_AT_PRESELECTED_TMINUS1_SOURCE"
    else:status="T_ACTOR_ELSEWHERE_AFTER_HOST"
    fuel_after=strict_int(actor.get("neutronium")) if actor is not None else None
    fuel_delta=edge["actor_Tminus1_fuel"]-fuel_after if fuel_after is not None else None
    return {
        **edge,"game_id":game,"turn":turn,
        "T_actor_observation_status":status,
        "T_target_observation_status":tstatus,
        "T_actor_position":list(actor_after) if actor_after is not None else None,
        "T_target_position":list(target_after) if target_after is not None else None,
        "T_target_at_frozen_destination":target_after==destination if target_after is not None else None,
        "T_actor_net_fuel_delta_KT":fuel_delta,
        "T_actor_fuel_delta_50KT":fuel_delta==50 if fuel_delta is not None else None,
        "Host_chunnel_activation_or_failure_proven":False,
        "Nplus1_VCR_used":False,
    }


def build_report(conn:Any,source:Mapping[str,Any]):
    windows,originals=frozen_v15(source)
    pre={}
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v16] PRE [{n}/{len(windows)}] G{g} T{t}",flush=True)
        snapshots,_=v9.pre_snapshots(conn,game=g,before=t-1)
        roster=_owner_rows_for_turn(group_perspective_records(snapshots,"ship"),t-1)
        edges,reason=potential_stock_edges(roster)
        pre[g,t]=(edges,reason)
    # Explicit strict barrier: T archives first accessed below.
    valid={
        (g,t,e["initiator_ship_id"],e["target_ship_id"])
        for (g,t),(rows,_reason) in pre.items() for e in rows
        if e["cohort"]=="ALL_TMINUS1_GATES_PASS"
    }
    if valid!=set(originals):
        missing=sorted(set(originals)-valid)[:6]
        unexpected=sorted(valid-set(originals))[:6]
        raise ValueError(
            f"v15 95 originally eligible actors differ under Tminus1 gate screen: "
            f"missing={missing} unexpected={unexpected}")
    results=[]
    total_reason=Counter()
    for n,(g,t) in enumerate(windows,1):
        print(f"[c5-v16] POST [{n}/{len(windows)}] G{g} T{t}",flush=True)
        current=v9.after_owner_current(conn,game=g,turn=t)
        edges,reason=pre[g,t]
        total_reason.update(reason)
        for edge in edges:
            row=compare_observations(edge,current,game=g,turn=t)
            key=(g,t,row["initiator_ship_id"],row["target_ship_id"])
            if key in originals:
                orig=originals[key]
                expected=orig["T_actor_observation_status"]
                if (expected!="T_ACTOR_AT_FROZEN_TARGET" or
                    row["T_actor_observation_status"]!="T_ACTOR_AT_PRESELECTED_TMINUS1_TARGET" or
                    row["T_actor_net_fuel_delta_KT"]!=orig["T_actor_net_fuel_delta_KT"]):
                    raise ValueError("V15 published positive comparator drift")
            results.append(row)
    valid_obs=[r for r in results if r["cohort"]=="ALL_TMINUS1_GATES_PASS"]
    neg_obs=[r for r in results if r["cohort"]=="ONE_TMINUS1_GATE_FAILS"]
    if len(valid_obs)!=95:raise ValueError("V15 positive sample denominator changed")
    by_gate=defaultdict(Counter)
    games=defaultdict(lambda:defaultdict(Counter))
    for r in neg_obs:
        by_gate[r["single_failing_gate"]][r["T_actor_observation_status"]]+=1
        games[str(r["game_id"])][r["single_failing_gate"]][r["T_actor_observation_status"]]+=1
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v15_git_blob_sha1":V15_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "fixed_V14_windows":60,"fixed_V14_games":20,
            "frozen_original_V15_positive_actor_edges":95,
            "Tminus1_single_failed_gate_candidates":len(neg_obs),
            "Tminus1_candidate_gate_and_abstain_counts":dict(sorted(total_reason.items())),
            "positive_actor_after_T_counts":dict(sorted(Counter(
                x["T_actor_observation_status"] for x in valid_obs).items())),
            "negative_single_gate_after_T_counts":dict(sorted(Counter(
                x["T_actor_observation_status"] for x in neg_obs).items())),
            "negative_by_failed_gate":{
                k:dict(sorted(v.items())) for k,v in sorted(by_gate.items())},
            "negative_distinct_game_turns":len({(r["game_id"],r["turn"]) for r in neg_obs}),
            "negative_distinct_games":len({r["game_id"] for r in neg_obs}),
            "all_forecasts_frozen_before_T":True,
            "future_VCR_used":False,"Host_Chunnel_activation_proven":False,
            "new_canonical_movement_or_combat_predictions":0,
        },
        "per_game_negative_counts":{
            g:{k:dict(sorted(v.items())) for k,v in sorted(groups.items())}
            for g,groups in sorted(games.items())},
        "negative_single_failed_gate_cases":neg_obs,
        "positive_Tminus1_gate_controls":[{
            "game_id":r["game_id"],"turn":r["turn"],
            "initiator_ship_id":r["initiator_ship_id"],
            "target_ship_id":r["target_ship_id"],
            "T_actor_observation_status":r["T_actor_observation_status"],
            "T_actor_net_fuel_delta_KT":r["T_actor_net_fuel_delta_KT"],
        } for r in valid_obs],
        "boundary":(
            "This V16 study reuses the V14/V15 sixty-window historical"
            " cohort; it is not a new holdout or a new data collection. "
            "Single Tminus1 failed necessary conditions are observational "
            "risk flags, not proof that Host had the same conditions at the "
            "later Chunnel phase. In particular Tow request != tow lock, "
            "target Warp at Tminus1 may change, and distance below100 may "
            "be altered by ordinary movement. Initiators with nonzero "
            "Tminus1 Warp are abstained entirely rather than called negatives. "
            "Numeric-code target ID aliases are abstained rather than "
            "retroactively applying the documented lowest-ID target rule. "
            "After-Host actor-at-target is observational, and return to "
            "the Tminus1 source does not prove absence of a Chunnel. "
            "No VCR Nplus1, Host mechanics promotion, or combat queue changes."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v15",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        source=git_pinned(a.frozen_v15)
        frozen_v15(source)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("pinned public100 corpus missing")
        print("[c5-v16] checking immutable public100 SHA256 once",flush=True)
        ts=time.monotonic()
        with db.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("pinned public100 SHA256 mismatch")
        print(f"[c5-v16] checksum verified in {time.monotonic()-ts:.1f}s",flush=True)
        conn,_=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:result=build_report(conn,source)
        finally:conn.close()
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 T-1 SINGLE FAILED CHUNNEL GATES V16 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
