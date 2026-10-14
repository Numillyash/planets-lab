"""Read-only C5 V5: distinguish unresolved arrivals from PRE-N site participants.

V4's potential arrivals include T-1 ships with unresolved movement whose
start/waypoint touches a factual current-N site. A potential arrival may,
however, have ALREADY appeared in a prior same-site VCR. This diagnostic
separates those explanations without modifying V4, predicting a battle, or
using N+1 owner/identity, combat results, mass, or selection as features.

The population is the exact V4 public100 frozen cohort, not a holdout.
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
import combat_c5_parent_queue_arrival_uncertainty_v4 as v4

SCHEMA="planets-lab.combat-c5-pre-n-site-presence-partition.v5"
STATUS="UNRESOLVED_TMINUS1_ARRIVALS_PARTITIONED_BY_PRE_N_SITE_HISTORY_NOT_PREDICTED"
V4_BLOB="847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610"
CENSUS_BLOB=v4.CENSUS_SHA1
GENERATION=v4.GENERATION
SHA256=v4.SHA256
NO_PAIR="ABSTAIN_PARENT_STANDARD_NO_PAIR"


def integer(value:Any)->int|None:
    return value if type(value) is int else None


def frozen_sources(census:Mapping[str,Any],previous:Mapping[str,Any]):
    """Validate all site keys and source accounting before reading any VCR."""
    sites=v4.v1.freeze_sites(census)
    if (previous.get("schema")!=v4.SCHEMA or
        previous.get("status")!=v4.STATUS or
        previous.get("source_census_git_blob_sha1")!=CENSUS_BLOB or
        previous.get("source_conditional_v2_git_blob_sha1")!=v4.V2_SHA1 or
        previous.get("source_db_sha256")!=SHA256):
        raise ValueError("V4 frozen source identity/status drift")
    expected={
        "frozen_sites":27,"frozen_adjacent_transitions":63,
        "risk_evaluations":56,"not_inspected_due_to_missing_context":7,
        "original_V2_conditional_predictions":9,"original_V2_conditional_exact":7,
        "new_combat_pair_predictions":0,"changed_original_V2_predictions":0,
    }
    summary=previous.get("summary")
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in expected.items()):
        raise ValueError("V4 frozen denominator/prediction drift")
    source=previous.get("site_evaluations")
    if not isinstance(source,list) or len(source)!=27:
        raise ValueError("V4 site observations incomplete")
    index={}
    for row in source:
        if not isinstance(row,Mapping):raise ValueError("V4 site row invalid")
        key=tuple(row.get(k) for k in ("game_id","turn","x","y"))
        if any(integer(v) is None for v in key) or key in index:
            raise ValueError("V4 duplicate/malformed site")
        index[key]=row
    if set(index)!={tuple(s[k] for k in ("game_id","turn","x","y")) for s in sites}:
        raise ValueError("V4 site cohort changed")
    total=0
    missing=0
    for s in sites:
        key=tuple(s[k] for k in ("game_id","turn","x","y"))
        row=index[key]
        expected_pairs=[list(pair) for pair in s["adjacent_pairs"]]
        if row.get("preselected_frozen_vcr_pairs")!=expected_pairs:
            raise ValueError("V4 preselected transition membership changed")
        records=row.get("transition_risks")
        nmissing=integer(row.get("original_unattempted_transitions"))
        ncontext=integer(row.get("additional_risk_unavailable"))
        if (not isinstance(records,list) or nmissing is None or nmissing<0
            or ncontext is None or ncontext<0 or
            len(records)+nmissing+ncontext!=len(expected_pairs)):
            raise ValueError("V4 transition accounting invalid")
        from_ids=[integer(t.get("from_vcr_id")) if isinstance(t,Mapping) else None
                  for t in records]
        if (None in from_ids or len(set(from_ids))!=len(from_ids)
            or not set(from_ids).issubset({a for a,_ in s["adjacent_pairs"]})):
            raise ValueError("V4 duplicate/foreign current VCR")
        total+=len(records)
        missing+=nmissing+ncontext
    if total!=56 or missing!=7:
        raise ValueError("V4 56/7 source accounting drift")
    return sites,index


def pre_n_site_history(
    *, cases:Mapping[tuple[int,int],Any],turn:int,
    frozen_vcr_ids:Sequence[int],through_vcr_id:int,
)->tuple[dict[int,int],frozenset[int]]:
    """Use ONLY the source site's factual VCR prefix at or before N.

    The frozen VCR ID census defines site membership, but future ship
    identities and bodies are never accessed or read by this function.
    """
    if (integer(turn) is None or integer(through_vcr_id) is None or
        not isinstance(frozen_vcr_ids,(list,tuple)) or
        through_vcr_id not in frozen_vcr_ids or
        list(frozen_vcr_ids)!=sorted(set(frozen_vcr_ids))):
        raise ValueError("invalid frozen VCR site prefix")
    prior={}
    current=frozenset()
    current_seen=0
    for vid in frozen_vcr_ids:
        if integer(vid) is None or vid<=0:
            raise ValueError("invalid frozen VCR ID")
        if vid>through_vcr_id:
            continue  # DO NOT access the corresponding future VCR payload
        case=cases.get((turn,vid))
        if case is None or not isinstance(case.payload,Mapping):
            raise ValueError("T-1/site VCR-prefix historical case missing")
        ids=[]
        for side in ("left","right"):
            raw=case.payload.get(side)
            sid=integer(raw.get("objectid")) if isinstance(raw,Mapping) else None
            if sid is None or sid<=0:
                raise ValueError("historical site VCR participant invalid")
            ids.append(sid)
        if len(set(ids))!=2:
            raise ValueError("historical VCR contains duplicate participant")
        if vid==through_vcr_id:
            current=frozenset(ids)
            current_seen+=1
        else:
            for sid in ids:prior.setdefault(sid,vid)
    if current_seen!=1 or len(current)!=2:
        raise ValueError("current VCR site prefix absent")
    return prior,current


def partition_transition(
    frozen:Mapping[str,Any], *, prior:Mapping[int,int],
    current_ids:frozenset[int],
)->dict[str,Any]:
    """Cannot call a selector; classify existing V4 witnesses only."""
    rows=frozen.get("Tminus1_plausible_arrivals")
    n=integer(frozen.get("from_vcr_id"))
    if n is None or n<=0 or not isinstance(rows,list):
        raise ValueError("invalid V4 transition evidence")
    if frozen.get("future_Nplus1_used") is not False or frozen.get("original_next_pair_or_side_changed") is not False:
        raise ValueError("V4 prediction/nonleakage boundary changed")
    unique=set()
    partition=[]
    for r in rows:
        if not isinstance(r,Mapping):
            raise ValueError("invalid V4 candidate row")
        ship=integer(r.get("ship_id"))
        owner=integer(r.get("owner_id"))
        if ship is None or ship<=0 or owner is None or owner<=0 or ship in unique:
            raise ValueError("invalid/duplicate V4 candidate")
        if ship in current_ids:
            raise ValueError("V4 candidate is already in current VCR N")
        unique.add(ship)
        previous=prior.get(ship)
        classification=("PRIOR_SAME_SITE_VCR_PARTICIPANT_CARRY_UNRESOLVED"
                        if previous is not None else
                        "NOT_SEEN_IN_PRIOR_SITE_VCR_TMINUS1_ARRIVAL_UNRESOLVED")
        partition.append({
            "ship_id":ship,"owner_id":owner,
            "position_source":r.get("position_source"),
            "first_prior_site_vcr_id":previous,
            "class":classification,
            "site_history_not_terminal_survival_evidence":True,
        })
    prior_count=sum(x["first_prior_site_vcr_id"] is not None for x in partition)
    unseen=len(partition)-prior_count
    if frozen.get("original_conditional_v2_status")==NO_PAIR:
        if unseen:
            verdict="ABSTAIN_UNSEEN_TMINUS1_SITE_ARRIVAL_REMAINS"
        elif prior_count:
            verdict="ABSTAIN_ONLY_PRIOR_SITE_PARTICIPANTS_CARRY_UNRESOLVED"
        else:
            verdict="NO_PAIR_NOT_PROVEN_SITE_EXHAUSTED_WITH_NO_INDEXED_WITNESS"
    else:
        verdict="ORIGINAL_V2_NON_NO_PAIR_VERDICT_UNCHANGED"
    return {
        "from_vcr_id":n,
        "original_v2_status":frozen.get("original_conditional_v2_status"),
        "original_v4_risk_status":frozen.get("risk_status"),
        "partition_status":verdict,
        "V4_potential_arrival_count":len(rows),
        "prior_site_VCR_participant_count":prior_count,
        "not_seen_in_prior_site_VCR_count":unseen,
        "witnesses":partition,
        "Nplus1_ship_identity_used":False,
        "new_battle_prediction":False,
        "terminal_outcome_or_survival_inferred":False,
    }


def build_report(census:Mapping[str,Any],previous:Mapping[str,Any],conn:Any):
    sites,source=frozen_sources(census,previous)
    windows=defaultdict(list)
    for site in sites:windows[(site["game_id"],site["turn"])].append(site)
    evaluations=[]
    for i,((game,turn),site_list) in enumerate(sorted(windows.items()),1):
        print(f"[c5-site-prefix] [{i}/{len(windows)}] G{game} T{turn} sites={len(site_list)}",flush=True)
        # Reader returns a turn's VCR cases; access ONLY ids <= current N.
        cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
        for site in site_list:
            key=(game,turn,site["x"],site["y"])
            frozen=source[key]
            output=[]
            for transition in frozen["transition_risks"]:
                n=transition["from_vcr_id"]
                prior,current=pre_n_site_history(
                    cases=cases,turn=turn,
                    frozen_vcr_ids=site["vcr_ids"],through_vcr_id=n)
                output.append(partition_transition(
                    transition,prior=prior,current_ids=current))
            evaluations.append({
                "game_id":game,"turn":turn,"x":site["x"],"y":site["y"],
                "V4_original_uninspected":(
                    frozen["original_unattempted_transitions"]+
                    frozen["additional_risk_unavailable"]),
                "transition_partitions":output,
            })
    rows=[r for site in evaluations for r in site["transition_partitions"]]
    original=Counter(r["original_v2_status"] for r in rows)
    split=Counter(r["partition_status"] for r in rows)
    if len(rows)!=56 or original[NO_PAIR]!=25 or len(evaluations)!=27:
        raise ValueError("V4 observational case population changed")
    if sum(r["V4_potential_arrival_count"] for r in rows)!=219:
        raise ValueError("V4 219 witness appearances changed")
    dedup={}
    for site in evaluations:
        for row in site["transition_partitions"]:
            for w in row["witnesses"]:
                key=(site["game_id"],site["turn"],site["x"],site["y"],w["ship_id"])
                entry=dedup.setdefault(key,(w["class"],w["position_source"]))
                if entry!=(w["class"],w["position_source"]):
                    # Same T-1 ship at the same site can become "prior" as
                    # VCR history advances; preserve both temporal classes.
                    dedup[key]=("MULTIPHASE_SITE_HISTORY",w["position_source"])
    no=[r for r in rows if r["original_v2_status"]==NO_PAIR]
    no_sites=[s for s in evaluations if any(
        r["original_v2_status"]==NO_PAIR for r in s["transition_partitions"])]
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v4_git_blob_sha1":V4_BLOB,
        "source_census_git_blob_sha1":CENSUS_BLOB,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_sites":27,"frozen_transitions":63,
            "evaluated_transitions":56,"source_uninspected":7,
            "NO_PAIR_transitions":25,
            "NO_PAIR_sites":len(no_sites),
            "NO_PAIR_partition_counts":dict(sorted(Counter(
                r["partition_status"] for r in no).items())),
            "all_partition_counts":dict(sorted(split.items())),
            "original_V4_witness_appearances":219,
            "V4_unique_site_ship_witnesses":len(dedup),
            "NO_PAIR_witness_appearances":sum(r["V4_potential_arrival_count"] for r in no),
            "NO_PAIR_prior_site_witness_appearances":sum(r["prior_site_VCR_participant_count"] for r in no),
            "NO_PAIR_unseen_prior_site_witness_appearances":sum(r["not_seen_in_prior_site_VCR_count"] for r in no),
            "new_battle_predictions":0,"changed_V2_predictions":0,
            "Nplus1_comparator_used":False,"Host_queue_exhaustion_proven":False,
        },
        "site_evaluations":evaluations,
        "boundary":(
            "Uses ONLY immutable V4 potential arrivals and site-census-VCR "
            "ship identities at or BEFORE current N. Earlier site combat "
            "participation is not proof of survival, removal, ownership "
            "continuity, or eligibility for the next battle. Absence of "
            "prior VCR is not proof of newly arrived physical presence. "
            "No N+1 body, ship IDs, mass, outcomes or next-pair selection "
            "enter this research-only report. Zero Host predictions made."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v4",type=Path,required=True)
    p.add_argument("--frozen-census",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        previous=v4.pinned(args.frozen_v4,V4_BLOB)
        census=v4.pinned(args.frozen_census,CENSUS_BLOB)
        frozen_sources(census,previous)
        db=args.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 database missing")
        print("[c5-site-prefix] verifying pinned public100 SHA256 once",flush=True)
        started=time.monotonic()
        with db.open("rb") as f:
            digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=SHA256:raise ValueError("pinned public100 SHA256 mismatch")
        print(f"[c5-site-prefix] SHA verified in {time.monotonic()-started:.1f}s; read-only",flush=True)
        conn,path=connect_compact_generation_read_only(GENERATION,args.corpus_db_root)
        try:report=build_report(census,previous,conn)
        finally:conn.close()
        report["db_path"]=str(path)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=args.output.with_suffix(args.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(args.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== ORDINARY C5 PRE-N SITE HISTORY PARTITION V5 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
