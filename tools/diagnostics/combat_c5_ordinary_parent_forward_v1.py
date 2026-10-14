"""Exploratory ordinary C5 parent-queue N -> N+1 forward evaluation.

All 27 ordinary multi-VCR sites are pinned BEFORE this run by the
pre-registered public100 census. 63 adjacent-ID site transitions are a
factual opportunity population, NOT an independently held-out test set.

For each transition, independently rebuild site state from T-1 + factual
history STRICTLY BEFORE N. Replay current VCR N, predict N+1 parent
STANDARD pair/sides from the carried state and T-1 orders/diplomacy.
Only after this selection may factual VCR N+1 enter the comparator.
Captures do NOT get the older fixture-based temporary order; they ABSTAIN.
No Horwasp, no production/executor/CURRENT mutations.
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
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.rules.combat.site_state import (
    apply_site_terminal_batch, record_factual_site_pair,
)
from planets_lab.rules.combat.site_executor import select_parent_resume
from planets_lab.rules.combat.site_input_adapter import (
    build_parent_standard_pair_inputs,
)

import combat_c5_public100_site_coverage_v1 as coverage
import combat_site_state_differential_v1 as differential
import combat_public_capture_o_layer_probe as o_layer

SCHEMA="planets-lab.combat-c5-ordinary-parent-forward.v1"
STATUS="EXPLORATORY_PARENT_STANDARD_FORWARD_C5_NOT_PROMOTED"
CENSUS_GIT_BLOB_SHA1="fda92475988d2f7dfbc7b93606de4f8cec909806"
GENERATION=coverage.GENERATION
SHA256=coverage.SHA256


def integer(v:Any)->int|None:
    return v if type(v) is int else None


def blob_sha1(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def progress(s:str)->None:
    print("[c5-forward] "+s,flush=True)


def freeze_sites(source:Mapping[str,Any])->list[dict[str,Any]]:
    """Reject modified source population; no outcome-based site reselection."""
    if (source.get("schema")!=coverage.SCHEMA or
        source.get("status")!=coverage.STATUS or
        source.get("source_db_sha256")!=SHA256):
        raise ValueError("frozen public100 site-census status/db drift")
    summary=source.get("summary")
    windows=source.get("preselected_window_evaluations")
    if (not isinstance(summary,Mapping) or not isinstance(windows,list)
        or summary.get("games")!=48 or summary.get("windows")!=96
        or summary.get("current_VCR_observations")!=809
        or summary.get("ordinary_ship_only_multi_VCR_sites")!=27
        or len(windows)!=96):
        raise ValueError("frozen 48-game/96-window/27-site population changed")
    selected=[]
    seen=set()
    for w in windows:
        for row in w.get("sites",[]):
            if not row.get("candidate_multi_ship_site"):continue
            if row.get("category")!="ORDINARY_SHIP_ONLY_MULTIVCR_SITE":
                raise ValueError("candidate site changed scope")
            key=(w["game_id"],w["turn"],row["x"],row["y"])
            if key in seen or any(integer(v) is None for v in key):
                raise ValueError("duplicate/invalid site key")
            seen.add(key)
            ids=row.get("ordinary_ship_vcr_ids")
            all_ids=row.get("all_vcr_ids")
            if (not isinstance(ids,list) or ids!=all_ids or
                len(ids)<2 or any(integer(v) is None or v<=0 for v in ids)
                or ids!=sorted(set(ids))):
                raise ValueError("non-ordinary/faulty frozen VCR IDs")
            adjacent=[(a,b) for a,b in zip(ids,ids[1:]) if b==a+1]
            if len(adjacent)!=row["observed_ship_VCR_ID_adjacent_pairs"]:
                raise ValueError("frozen adjacent transitions changed")
            selected.append({
                "game_id":key[0],"turn":key[1],"x":key[2],"y":key[3],
                "cohort":w["cohort"],"vcr_ids":ids,"adjacent_pairs":adjacent,
            })
    if len(selected)!=27 or sum(len(x["adjacent_pairs"]) for x in selected)!=63:
        raise ValueError("expected complete 27-site, 63-transition census")
    return selected


def context_without_future(
    context:Mapping[str,Any],*,through_vcr_id:int,
)->dict[str,Any]:
    """Remove factual queue N+1 and beyond BEFORE any selector is invoked.

    Site roster comes from independent T-1 position prediction. Other
    independent controls are restricted by adapter through_vcr_id.
    """
    queue=context.get("factual_queue")
    if not isinstance(queue,Sequence) or isinstance(queue,(str,bytes)):
        raise ValueError("site factual history missing")
    truncated=[row for row in queue if
               isinstance(row,Mapping) and
               integer(row.get("vcr_id")) is not None and
               row["vcr_id"]<=through_vcr_id]
    if any(integer(row["vcr_id"]) is None for row in truncated):
        raise ValueError("invalid factual history")
    return {**context,"factual_queue":truncated}


def _abstain(code:str,details:str|None=None)->dict[str,Any]:
    return {"status":code,"reason":details,"prediction":None,
            "factual_comparison":None,"no_next_vcr_oracle":True}


def predict_from_prefix(
    *,context:Mapping[str,Any],
    appearances:Mapping[tuple[int,int,int,int],Mapping[str,Any]],
    cases:Mapping[tuple[int,int],Any],
    game:int,turn:int,n:int,
)->dict[str,Any]:
    """Only current/before-N state may enter this function.

    Caller must pass a context with factual_queue truncated at N.
    No next VCR ID or next-case argument exists in this signature.
    """
    queue=context.get("factual_queue")
    if not isinstance(queue,Sequence) or any(
        not isinstance(r,Mapping) or integer(r.get("vcr_id")) is None
        or r["vcr_id"]>n for r in queue
    ):
        raise ValueError("future factual VCR reached parent queue predictor")
    try:
        # Explicitly remove current N as well from historical reconstruction;
        # current VCR N is accessed separately only for its replay.
        history_context=context_without_future(context,through_vcr_id=n-1)
        state=differential._initial_state_before_window(
            context=history_context,appearances=appearances,start_vcr_id=n
        )
        current=differential._row_by_vcr(queue,n)
        state=record_factual_site_pair(
            state,left_ship_id=int(current["left_ship_id"]),
            right_ship_id=int(current["right_ship_id"]),
        )
        current_case=cases.get((turn,n))
        if current_case is None:
            return _abstain("ABSTAIN_CURRENT_VCR_REPLAY_INPUT_MISSING")
        replay=differential.build_site_terminal_replay_batch(
            state,vcr_payload=current_case.payload,
            beams=current_case.beams,torpedoes=current_case.torpedoes,
            settings=current_case.settings
        )
        if replay.resolved is not True:
            return _abstain("ABSTAIN_CURRENT_REPLAY_OR_CARRIED_START",
                            replay.reason)
        transition=apply_site_terminal_batch(
            state,terminals_by_ship_id=replay.terminals_by_ship_id,
            capture_transfers_by_ship_id=replay.capture_transfers_by_ship_id
        )
        if transition.resolved is not True:
            return _abstain("ABSTAIN_CURRENT_SITE_MUTATION",
                            str(transition.mutation.unresolved_reasons))
        state=transition.state
        if replay.capture_transfers_by_ship_id:
            # Never use a game-specific fixture order or N+1 opponent identity.
            return _abstain("ABSTAIN_CAPTURE_TEMPORARY_ORDER_NOT_INDEPENDENT")
        adapter=build_parent_standard_pair_inputs(
            state=state,context=context,target_battle_turn=turn,
            through_vcr_id=n,
            requests_combat=differential._requests_combat,
            relation_signature=differential._relation_signature,
            independent_permission=differential._independent_permission,
            interference_state=differential.baseline_module._interference_state,
            candidate_input=differential.baseline_module._candidate_input
        )
        selected=select_parent_resume(state,pair_inputs=adapter.pair_inputs)
        if (selected.status!="resolved" or selected.pair is None
            or selected.left_ship_id is None
            or selected.right_ship_id is None):
            return _abstain(
                "ABSTAIN_PARENT_STANDARD_"+str(selected.status).upper(),
                selected.reason
            )
        return {
            "status":"PREDICTED_NEXT_PARENT_STANDARD",
            "reason":None,
            "prediction":{
                "pair":list(selected.pair),
                "left_ship_id":selected.left_ship_id,
                "right_ship_id":selected.right_ship_id,
                "occurrence_index":selected.occurrence_index,
                "pair_input_count":len(adapter.pair_inputs),
                "diplomacy_controls_through_vcr_id":n,
                "capture_fixture_order_used":False,
            },
            "factual_comparison":None,
            "no_next_vcr_oracle":True
        }
    except (ValueError,TypeError,KeyError) as exc:
        return _abstain("ABSTAIN_SITE_HISTORY_OR_SELECTOR_UNRESOLVED",
                        f"{type(exc).__name__}:{exc}")


def compare_after_selection(pred:Mapping[str,Any],
                            factual:Mapping[str,Any])->dict[str,Any]:
    """Next VCR accessed only outside predict_from_prefix after prediction."""
    actual_pair=factual.get("pair")
    left,right=integer(factual.get("left_ship_id")),integer(factual.get("right_ship_id"))
    if (not isinstance(actual_pair,tuple) or len(actual_pair)!=2 or
        left is None or right is None):
        return {"status":"ABSTAIN_MALFORMED_FUTURE_COMPARATOR",
                "pair_exact":None,"sides_exact":None,"exact":None}
    choice=pred.get("prediction")
    if not isinstance(choice,Mapping):
        return {"status":"NOT_PREDICTED","pair_exact":None,
                "sides_exact":None,"exact":None}
    match_pair=list(actual_pair)==choice["pair"]
    match_sides=left==choice["left_ship_id"] and right==choice["right_ship_id"]
    return {"status":"COMPARATOR_AVAILABLE",
            "actual_pair":list(actual_pair),
            "actual_left_ship_id":left,"actual_right_ship_id":right,
            "pair_exact":match_pair,"sides_exact":match_sides,
            "exact":match_pair and match_sides}


def evaluate_site(
    *,site:Mapping[str,Any],context:Mapping[str,Any],
    appearances:Mapping[tuple[int,int,int,int],Mapping[str,Any]],
    cases:Mapping[tuple[int,int],Any],
)->dict[str,Any]:
    """Fixed denominator: every frozen adjacent-ID transition recorded."""
    game,turn=site["game_id"],site["turn"]
    original=context.get("factual_queue")
    if not isinstance(original,Sequence) or isinstance(original,(str,bytes)):
        return {"status":"ABSTAIN_NO_SITE_QUEUE","transitions":[],
                "missed_transitions":len(site["adjacent_pairs"])}
    observed=[integer(x.get("vcr_id")) for x in original if isinstance(x,Mapping)]
    if sorted(observed)!=site["vcr_ids"]:
        return {"status":"ABSTAIN_FROZEN_VCR_SITE_MEMBERSHIP_MISMATCH",
                "observed_vcr_ids":observed,"transitions":[],
                "missed_transitions":len(site["adjacent_pairs"])}
    trials=[]
    for n,nplus1 in site["adjacent_pairs"]:
        truncated=context_without_future(context,through_vcr_id=n)
        pred=predict_from_prefix(
            context=truncated,appearances=appearances,cases=cases,
            game=game,turn=turn,n=n
        )
        # First read the next factual VCR here; no earlier function accepts it.
        factual=differential._row_by_vcr(original,nplus1)
        cmp=compare_after_selection(pred,factual)
        trials.append({
            "from_vcr_id":n,"to_vcr_id":nplus1,
            **pred,"factual_comparison":cmp,
            "history_carries_only_prior_current_VCRs":True,
        })
    return {"status":"ALL_FROZEN_TRANSITIONS_EVALUATED",
            "missed_transitions":0,"transitions":trials}


def build_report(source:Mapping[str,Any],conn:Any)->dict[str,Any]:
    frozen=freeze_sites(source)
    grouped:dict[tuple[int,int],list[dict[str,Any]]]=defaultdict(list)
    for s in frozen:grouped[(s["game_id"],s["turn"])].append(s)
    results=[]
    for i,((game,turn),sites) in enumerate(sorted(grouped.items()),1):
        progress(f"[{i}/{len(grouped)}] G{game} T{turn}: {len(sites)} frozen sites")
        targets={(game,turn,s["x"],s["y"]):() for s in sites}
        context_map={}
        try:
            appearances,_=o_layer._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns={turn})
            appearance_index=differential._appearance_map(appearances)
            o_layer._visit_targeted_site_contexts(
                connection=conn,game_id=game,targets=targets,
                appearances=appearances,
                observer=lambda c:context_map.__setitem__(
                    (c["game_id"],c["battle_turn"],c["x"],c["y"]),dict(c)
                ))
            vcr_cases=combat_vcr_cases_for_turns(
                conn,game_id=game,battle_turns={turn})
            window_error=None
        except (ValueError,TypeError,KeyError) as exc:
            context_map={}
            appearance_index={}
            vcr_cases={}
            window_error=f"{type(exc).__name__}:{exc}"
        for site in sites:
            key=(game,turn,site["x"],site["y"])
            c=context_map.get(key)
            if c is None:
                evaluated={"status":"ABSTAIN_SITE_CONTEXT_UNAVAILABLE",
                           "reason":window_error or "target T-1 site context not reconstructed",
                           "transitions":[],"missed_transitions":len(site["adjacent_pairs"])}
            else:
                try:evaluated=evaluate_site(
                    site=site,context=c,appearances=appearance_index,cases=vcr_cases)
                except (ValueError,KeyError,TypeError) as exc:
                    evaluated={"status":"ABSTAIN_SITE_EVALUATION_UNRESOLVED",
                               "reason":f"{type(exc).__name__}:{exc}",
                               "transitions":[],"missed_transitions":len(site["adjacent_pairs"])}
            results.append({**site,**evaluated})
        progress(f"[{i}/{len(grouped)}] processed {len(sites)} sites")
    trials=[tr for r in results for tr in r["transitions"]]
    statuses=Counter(t["status"] for t in trials)
    compared=[t for t in trials if t["factual_comparison"]["exact"] is not None]
    predicted=[t for t in trials if t["status"]=="PREDICTED_NEXT_PARENT_STANDARD"]
    skipped=sum(x["missed_transitions"] for x in results)
    assert len(results)==27 and len(trials)+skipped==63
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_c5_site_census_git_blob_sha1":CENSUS_GIT_BLOB_SHA1,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_sites":len(results),"frozen_adjacent_VCR_ID_transitions":63,
            "transition_trials":len(trials),"unattempted_due_to_site_failure":skipped,
            "status_counts":dict(sorted(statuses.items())),
            "parent_queue_predictions_made":len(predicted),
            "available_factual_comparators":len(compared),
            "exact_next_pair_and_sides":sum(
                tr["factual_comparison"]["exact"] is True for tr in compared),
            "mismatched_next_pair_or_sides":sum(
                tr["factual_comparison"]["exact"] is False for tr in compared),
            "Horwasp_cases_predicted":0,
            "game_specific_capture_fixture_order_used":False,
            "truly_independent_holdout":False,
            "full_NuHost_executor_promotion":False,
        },
        "site_evaluations":results,
        "boundary":(
            "Frozen 48-game/96-window site census was designed without VCR "
            "outcome selection; its 27 multi-fight sites are exploratory "
            "factual site-shape-conditioned cases, NOT a fresh holdout. "
            "T-1 site membership is independently predicted, but current "
            "VCR N replay includes its factual seed/static setup; historical "
            "prior-to-N VCRs provide anchored state. The N+1 comparator "
            "is opened only after parent STANDARD selection. Special "
            "capture temporary orders are explicitly ABSTAIN, never "
            "reconstructed from N+1, fixture sequences or inferred outcomes. "
            "Only adjacent-ID transitions are attempted, without proving "
            "the Host VCR-ID scheduling rule. No race12, production or "
            "corpus mutation."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-c5-census",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        raw=args.frozen_c5_census.read_bytes()
        if blob_sha1(raw)!=CENSUS_GIT_BLOB_SHA1:
            raise ValueError("frozen published C5 census blob SHA1 mismatch")
        source=json.loads(raw)
        freeze_sites(source)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 corpus unavailable")
        started=time.monotonic()
        progress("verifying immutable public100 SHA256 once")
        with db.open("rb") as f:actual=hashlib.file_digest(f,"sha256").hexdigest()
        if actual!=SHA256:raise ValueError("public100 SHA256 drift")
        progress(f"SHA256 verified in {time.monotonic()-started:.1f}s")
        conn,path=connect_compact_generation_read_only(
            GENERATION,args.corpus_db_root)
        try:result=build_report(source,conn)
        finally:conn.close()
        result["database_path"]=str(path)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=args.output.with_suffix(args.output.suffix+".tmp")
        tmp.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(args.output)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== ORDINARY C5 PARENT STANDARD N-TO-N+1 FORWARD V1 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
