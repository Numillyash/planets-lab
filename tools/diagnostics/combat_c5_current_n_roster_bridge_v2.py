"""C5 parent queue current-VCR-N conditional roster bridge (research V2).

This is NOT a repaired independent T-1 location predictor. Only a missing
current VCR N participant may be *conditioned* on its factual N start vector,
and ONLY if independently present in the owner's T-1 archive with the same
ship/owner/race/hull identity, and not previously fought at this site.

The previous frozen V1 strict result (3 predictions / 63 transitions, 2
correct), all 27 site identities, and 63 adjacent VCR-ID opportunities remain
immutable comparators. This experiment tries to disentangle incorrect
pre-combat SITE MEMBERSHIP from subsequent parent-queue selection.

NEVER load current VCR N+1 inside prediction. No retroactive correction of
existing carried ships, no capture fixture, no Horwasp. Conditional results
must never be relabeled as independent complete Host predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping,Sequence
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/"src",Path(__file__).resolve().parent):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.rules.combat.site_state import (
    SiteCombatState,apply_site_terminal_batch,record_factual_site_pair
)
from planets_lab.rules.combat.site_input_adapter import build_parent_standard_pair_inputs
from planets_lab.rules.combat.site_executor import select_parent_resume
from planets_lab.rules.combat.site_terminal_adapter import _CARRIED_SIDE_FIELDS

import combat_c5_ordinary_parent_forward_v1 as v1
import combat_c5_public100_site_coverage_v1 as coverage
import combat_site_state_differential_v1 as differential
import combat_public_capture_o_layer_probe as o_layer

SCHEMA="planets-lab.combat-c5-current-n-roster-bridge.v2"
STATUS="CURRENT_N_ROSTER_CONDITIONAL_C5_NOT_INDEPENDENT_TMINUS1"
CENSUS_BLOB=v1.CENSUS_GIT_BLOB_SHA1
STRICT_V1_BLOB="1ed69919f38fbc7d09b2e890162c1a25a3f677bd"
GENERATION=v1.GENERATION
SHA256=v1.SHA256


def int_strict(x:Any)->int|None:
    return x if type(x) is int else None


def progress(msg:str)->None:
    print("[c5-current-N] "+msg,flush=True)


def read_pinned(path:Path,git_blob:str)->dict[str,Any]:
    raw=path.read_bytes()
    if v1.blob_sha1(raw)!=git_blob:
        raise ValueError("frozen report Git blob identity mismatch: "+str(path))
    decoded=json.loads(raw)
    if not isinstance(decoded,dict):
        raise ValueError("expected frozen JSON mapping")
    return decoded


def strict_v1_index(source:Mapping[str,Any],frozen_sites:Sequence[Mapping[str,Any]])->dict[tuple[int,int,int,int,int,int],dict[str,Any]]:
    """Strict V1 frozen outcome is metadata/checkpoint only, never predictor."""
    if (source.get("schema")!=v1.SCHEMA or
        source.get("status")!=v1.STATUS or
        source.get("source_c5_site_census_git_blob_sha1")!=CENSUS_BLOB or
        source.get("source_db_sha256")!=SHA256):
        raise ValueError("strict V1 status or prerequisite drift")
    summary=source.get("summary",{})
    for name,want in (("frozen_sites",27),("frozen_adjacent_VCR_ID_transitions",63),
                      ("transition_trials",56),("unattempted_due_to_site_failure",7),
                      ("parent_queue_predictions_made",3),
                      ("exact_next_pair_and_sides",2),
                      ("mismatched_next_pair_or_sides",1)):
        if summary.get(name)!=want:
            raise ValueError("strict V1 published summary drift: "+name)
    sites=source.get("site_evaluations")
    if not isinstance(sites,list) or len(sites)!=27:
        raise ValueError("strict site evaluations missing")
    expected={
        (s["game_id"],s["turn"],s["x"],s["y"],n,n_next)
        for s in frozen_sites for n,n_next in s["adjacent_pairs"]
    }
    found={}
    for site in sites:
        root=(site["game_id"],site["turn"],site["x"],site["y"])
        trs=site.get("transitions",[])
        if not isinstance(trs,list):
            raise ValueError("strict transitions malformed")
        for tr in trs:
            key=(*root,tr["from_vcr_id"],tr["to_vcr_id"])
            if key in found: raise ValueError("duplicate strict transition")
            found[key]={"status":tr["status"],"reason":tr.get("reason"),
                        "prediction":tr.get("prediction"),
                        "factual_comparison":tr.get("factual_comparison")}
        if site.get("missed_transitions",0):
            for n,n_next in site["adjacent_pairs"]:
                key=(*root,n,n_next)
                if key in found:continue
                found[key]={
                    "status":site["status"],"reason":site.get("reason"),
                    "prediction":None,"factual_comparison":None
                }
    if set(found)!=expected or len(found)!=63:
        raise ValueError("strict frozen 63-transition denominator drift")
    return found


def participants_N(payload:Mapping[str,Any])->list[tuple[str,int,int,int,int]]:
    """Only current N participant identity and starting state."""
    result=[]
    for side in ("left","right"):
        raw=payload.get(side)
        owner=int_strict(payload.get(side+"ownerid"))
        if not isinstance(raw,Mapping):
            raise ValueError("current VCR N participant missing: "+side)
        sid=int_strict(raw.get("objectid"))
        hull=int_strict(raw.get("hullid"))
        race=int_strict(raw.get("raceid"))
        if any(x is None or x<=0 for x in (sid,hull,race,owner)):
            raise ValueError("current VCR N participant identity invalid")
        if race==12:
            raise ValueError("Horwasp outside ordinary scope")
        result.append((side,sid,owner,hull,race))
    if result[0][1]==result[1][1]:
        raise ValueError("same ship on both sides of N")
    return result


def anchored_ship_from_N(
    *,side:str,ship_id:int,owner_id:int,hull_id:int,race_id:int,
    payload:Mapping[str,Any],entry:Mapping[str,Any],
    site:tuple[int,int],
)->tuple[dict[str,Any],dict[str,Any]]:
    """T-1 owner/order identity must agree; dynamic state comes ONLY from N."""
    if (int_strict(entry.get("owner_id"))!=owner_id or
        int_strict(entry.get("hull_id"))!=hull_id or
        int_strict(entry.get("race_id"))!=race_id or
        not isinstance(entry.get("raw"),Mapping) or
        int_strict(entry["raw"].get("id"))!=ship_id or
        int_strict(entry["raw"].get("ownerid"))!=owner_id):
        raise ValueError("Tminus1_owner_ship_identity_inconsistent_with_N")
    n=payload[side]
    state={
        "id":ship_id,"owner_id":owner_id,
        "hull_id":hull_id,"race_id":race_id,
        "federation_crew_bonus":race_id==1,
        "lizard_crew_bonus":race_id==2,
    }
    for field,vcr_key in _CARRIED_SIDE_FIELDS:
        value=int_strict(n.get(vcr_key))
        if value is None or (field in ("hull_id","race_id") and value<=0) or (
            field not in ("hull_id","race_id") and value<0
        ):
            raise ValueError("current_N_anchored_start_field_missing_"+field)
        if field in ("hull_id","race_id") and value!=state[field]:
            raise ValueError("current_N_anchored_identity_conflict")
        state[field]=value
    for f in ("beam","launcher","bay"):
        state["physical_"+f+"_count"]=state[f+"_count"]
    old_position=entry.get("position")
    trace={
        "ship_id":ship_id,
        "source":"CURRENT_VCR_N_START_WITH_TMINUS1_OWNER_IDENTITY",
        "Tminus1_predicted_position":old_position,
        "current_N_site":list(site),
        "Tminus1_predicted_at_current_N_site":old_position==site or old_position==list(site),
        "dynamic_state_independently_predicted":False,
        "Nplus1_fields_used":False,
    }
    return state,trace


def prepare_current_state(
    *,state:SiteCombatState,
    current_case:Any,context:Mapping[str,Any],
    history:Sequence[Mapping[str,Any]],
)->tuple[SiteCombatState,list[dict[str,Any]]]:
    """Anchor only missing N participants. Existing carried mismatch ABSTAINS."""
    party=participants_N(current_case.payload)
    already_seen=set()
    for row in history:
        ids=(row.get("left_ship_id"),row.get("right_ship_id"))
        already_seen.update(x for x in ids if int_strict(x) is not None)
    active=dict(state.active_ships)
    anchored=[]
    for side,sid,owner,hull,race in party:
        if sid in active:continue
        if sid in already_seen:
            raise ValueError("ship_seen_before_N_and_now_missing_no_resurrection")
        entry=context.get("predictions",{}).get(sid)
        if not isinstance(entry,Mapping):
            raise ValueError("current_N_ship_absent_from_Tminus1_owner_orders")
        one,detail=anchored_ship_from_N(
            side=side,ship_id=sid,owner_id=owner,hull_id=hull,
            race_id=race,payload=current_case.payload,entry=entry,
            site=(context["x"],context["y"]))
        active[sid]=one
        anchored.append(detail)
    return SiteCombatState(
        active_ships=active,
        standard_queue_state=state.standard_queue_state,
        parent_queue_excluded_ship_ids=state.parent_queue_excluded_ship_ids,
        temporary_capture_order=state.temporary_capture_order
    ),anchored


def predict_bridge(*,context:Mapping[str,Any],appearances:Mapping,
                   cases:Mapping,game:int,turn:int,n:int)->dict[str,Any]:
    """No future N+1 argument. Factual N start can condition roster only."""
    queue=context.get("factual_queue")
    if (not isinstance(queue,Sequence) or isinstance(queue,(str,bytes))
        or any(not isinstance(r,Mapping) or
               int_strict(r.get("vcr_id")) is None or r["vcr_id"]>n for r in queue)):
        raise ValueError("future VCR leaked into predictor")
    current=cases.get((turn,n))
    if current is None:
        return {**v1._abstain("ABSTAIN_CURRENT_VCR_REPLAY_INPUT_MISSING"),
                "anchored_ships":[]}
    history_context=v1.context_without_future(context,through_vcr_id=n-1)
    try:
        state=differential._initial_state_before_window(
            context=history_context,appearances=appearances,
            start_vcr_id=n)
        current_row=differential._row_by_vcr(queue,n)
        state,bridges=prepare_current_state(
            state=state,current_case=current,context=context,
            history=history_context["factual_queue"])
        state=record_factual_site_pair(
            state,left_ship_id=int(current_row["left_ship_id"]),
            right_ship_id=int(current_row["right_ship_id"]))
        replay=differential.build_site_terminal_replay_batch(
            state,vcr_payload=current.payload,beams=current.beams,
            torpedoes=current.torpedoes,settings=current.settings)
        if replay.resolved is not True:
            return {**v1._abstain("ABSTAIN_N_REPLAY_OR_CARRIED_START",
                                replay.reason),"anchored_ships":bridges}
        mutated=apply_site_terminal_batch(
            state,terminals_by_ship_id=replay.terminals_by_ship_id,
            capture_transfers_by_ship_id=replay.capture_transfers_by_ship_id)
        if mutated.resolved is not True:
            return {**v1._abstain("ABSTAIN_CURRENT_SITE_MUTATION",
                                 str(mutated.mutation.unresolved_reasons)),
                    "anchored_ships":bridges}
        if replay.capture_transfers_by_ship_id:
            return {**v1._abstain("ABSTAIN_CAPTURE_TEMPORARY_ORDER_NOT_INDEPENDENT"),
                    "anchored_ships":bridges}
        adapted=build_parent_standard_pair_inputs(
            state=mutated.state,context=context,target_battle_turn=turn,
            through_vcr_id=n,
            requests_combat=differential._requests_combat,
            relation_signature=differential._relation_signature,
            independent_permission=differential._independent_permission,
            interference_state=differential.baseline_module._interference_state,
            candidate_input=differential.baseline_module._candidate_input,
        )
        chosen=select_parent_resume(
            mutated.state,pair_inputs=adapted.pair_inputs)
        if (chosen.status!="resolved" or chosen.pair is None or
            chosen.left_ship_id is None or chosen.right_ship_id is None):
            return {
                **v1._abstain("ABSTAIN_PARENT_STANDARD_"+str(chosen.status).upper(),
                            chosen.reason),"anchored_ships":bridges}
        return {
            "status":"CONDITIONAL_PARENT_STANDARD_N_TO_NPLUS1",
            "reason":None,
            "prediction":{
                "pair":list(chosen.pair),
                "left_ship_id":chosen.left_ship_id,
                "right_ship_id":chosen.right_ship_id,
                "occurrence_index":chosen.occurrence_index,
                "pair_input_count":len(adapted.pair_inputs),
                "diplomacy_controls_through_vcr_id":n,
                "capture_fixture_order_used":False,
                "current_N_roster_conditioned":bool(bridges)
            },
            "anchored_ships":bridges,
            "factual_comparison":None,"no_next_vcr_oracle":True,
        }
    except (ValueError,TypeError,KeyError) as exc:
        return {**v1._abstain(
            "ABSTAIN_TMINUS1_OR_CURRENT_N_BRIDGE_UNRESOLVED",
            f"{type(exc).__name__}:{exc}"),"anchored_ships":[]}


def evaluate_site(*,site:Mapping[str,Any],context:Mapping[str,Any],
                  appearances:Mapping,cases:Mapping,
                  baseline:Mapping)->dict[str,Any]:
    old=context.get("factual_queue")
    if not isinstance(old,Sequence) or isinstance(old,(str,bytes)):
        return {"status":"ABSTAIN_NO_SITE_QUEUE",
                "missing":len(site["adjacent_pairs"]),"transitions":[]}
    if sorted(int_strict(x.get("vcr_id")) for x in old)!=site["vcr_ids"]:
        return {"status":"ABSTAIN_SITE_MEMBERSHIP_NOT_FROZEN",
                "missing":len(site["adjacent_pairs"]),"transitions":[]}
    result=[]
    for n,nplus1 in site["adjacent_pairs"]:
        key=(site["game_id"],site["turn"],site["x"],site["y"],n,nplus1)
        prior=baseline[key]
        prefix=v1.context_without_future(context,through_vcr_id=n)
        predicted=predict_bridge(
            context=prefix,appearances=appearances,cases=cases,
            game=site["game_id"],turn=site["turn"],n=n)
        # Only now read factual N+1.
        factual=differential._row_by_vcr(old,nplus1)
        comparator=v1.compare_after_selection(predicted,factual)
        result.append({
            "from_vcr_id":n,"to_vcr_id":nplus1,
            **predicted,"factual_comparison":comparator,
            "original_strict_V1_status":prior["status"],
            "original_strict_V1_exact":prior.get("factual_comparison",{}).get("exact")
                if isinstance(prior.get("factual_comparison"),Mapping) else None,
            "current_N_roster_evidence_conditioned":bool(predicted["anchored_ships"]),
            "Nplus1_used_only_as_comparator":True,
        })
    return {"status":"ALL_FROZEN_TRANSITIONS_ATTEMPTED",
            "missing":0,"transitions":result}


def build_report(census:Mapping[str,Any],strict:Mapping[str,Any],conn:Any)->dict[str,Any]:
    frozen=v1.freeze_sites(census)
    baseline=strict_v1_index(strict,frozen)
    windows=defaultdict(list)
    for s in frozen:windows[(s["game_id"],s["turn"])].append(s)
    all_sites=[]
    for i,((game,turn),sites) in enumerate(sorted(windows.items()),1):
        progress(f"[{i}/{len(windows)}] G{game} T{turn}: {len(sites)} frozen sites")
        targets={(game,turn,s["x"],s["y"]):() for s in sites}
        contexts={}
        window_error=None
        try:
            appearances,_=o_layer._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns={turn})
            index=differential._appearance_map(appearances)
            o_layer._visit_targeted_site_contexts(
                connection=conn,game_id=game,targets=targets,
                appearances=appearances,
                observer=lambda c:contexts.__setitem__(
                    (c["game_id"],c["battle_turn"],c["x"],c["y"]),dict(c)))
            cases=combat_vcr_cases_for_turns(
                conn,game_id=game,battle_turns={turn})
        except (ValueError,TypeError,KeyError) as exc:
            index={};contexts={};cases={}
            window_error=f"{type(exc).__name__}:{exc}"
        for s in sites:
            context=contexts.get((game,turn,s["x"],s["y"]))
            if context is None:
                entry={
                    "status":"ABSTAIN_TMINUS1_SITE_CONTEXT_MISSING",
                    "reason":window_error or "site context not reconstructed",
                    "missing":len(s["adjacent_pairs"]),"transitions":[]
                }
            else:
                try: entry=evaluate_site(
                    site=s,context=context,appearances=index,
                    cases=cases,baseline=baseline)
                except (ValueError,KeyError,TypeError) as exc:
                    entry={
                        "status":"ABSTAIN_SITE_EVALUATION_FAILED",
                        "reason":f"{type(exc).__name__}:{exc}",
                        "missing":len(s["adjacent_pairs"]),"transitions":[]
                    }
            all_sites.append({**s,**entry})
        progress(f"[{i}/{len(windows)}] completed {len(sites)} sites")
    transitions=[t for site in all_sites for t in site["transitions"]]
    total_missing=sum(s["missing"] for s in all_sites)
    if len(all_sites)!=27 or len(transitions)+total_missing!=63:
        raise ValueError("frozen 27-site/63-transition denominator drift")
    predicted=[t for t in transitions if t["prediction"] is not None]
    conditioned=[t for t in predicted if t["current_N_roster_evidence_conditioned"]]
    strict_unavailable=[t for t in predicted if t["original_strict_V1_status"]!="PREDICTED_NEXT_PARENT_STANDARD"]
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_census_git_blob_sha1":CENSUS_BLOB,
        "source_strict_v1_git_blob_sha1":STRICT_V1_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_sites":27,"frozen_adjacent_ID_transitions":63,
            "attempted_transitions":len(transitions),
            "site_failure_transitions":total_missing,
            "status_counts":dict(sorted(Counter(t["status"] for t in transitions).items())),
            "conditional_predictions_made":len(predicted),
            "conditional_current_N_roster_anchored_predictions":len(conditioned),
            "strict_V1_previously_unavailable_now_conditional_predictions":len(strict_unavailable),
            "conditional_pair_and_sides_exact":sum(t["factual_comparison"]["exact"] is True for t in predicted),
            "conditional_pair_or_sides_mismatch":sum(t["factual_comparison"]["exact"] is False for t in predicted),
            "independent_full_Host_predictions_made":0,
            "unverified_capture_temporary_order_promoted":False,
            "future_Nplus1_used_in_predictor":False,
            "ordinary_non_Horwasp_only":True,
        },
        "site_evaluations":all_sites,
        "boundary":(
            "Factual current N participant dynamic state can be used to "
            "anchor only T-1 independently known owner+ship+races+catalog "
            "identities missing from inferred T-1 site roster. Existing "
            "carried ships are never overwritten. Prior-site participants "
            "cannot be resurrected. Captures abstain. All conditional "
            "predictions measure next-queue selection GIVEN factual N "
            "membership/state, NOT ability to predict N itself. The "
            "original V1 strict population and outcomes are immutable. "
            "N+1 is strictly post-selection comparator. Already open sites "
            "remain exploratory, not new held-out validation. No "
            "Horwasp, production or executor promotion."
        ),
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-census",type=Path,required=True)
    parser.add_argument("--frozen-strict-v1",type=Path,required=True)
    parser.add_argument("--corpus-db-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    try:
        census=read_pinned(a.frozen_census,CENSUS_BLOB)
        strict=read_pinned(a.frozen_strict_v1,STRICT_V1_BLOB)
        frozen=v1.freeze_sites(census)
        strict_v1_index(strict,frozen)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 unavailable")
        before=time.monotonic()
        progress("verifying pinned public100 SHA256 once")
        with db.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
        if sha!=SHA256:raise ValueError("pinned corpus SHA256 mismatch")
        progress(f"SHA256 verified in {time.monotonic()-before:.1f}s")
        conn,path=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(census,strict,conn)
        finally:conn.close()
        report["database_path"]=str(path)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2
    print("===== C5 CURRENT-VCR-N ROSTER BRIDGE CONDITIONAL V2 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
