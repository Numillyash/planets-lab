"""Research-only C5 V6: distinguish T-1 site residence from waypoint-only ingress.

Joins the exact immutable V4 T-1 site-risk observations with V5
strictly-pre-N factual same-site history. Unlike V5, there is NO corpus
database/VCR reading in this experiment. All source reports are pinned by
their Git blob hashes. No new N+1 target or Host pair is predicted.

"Unseen" means absent in site VCRs strictly before N, not physical arrival.
A ship already at this site on T-1 may later leave or fight; a ship whose
waypoint points to the site may be blocked by Tow/mines/other effects.
Neither is proven eligible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter,defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA="planets-lab.combat-c5-tminus1-ingress-residence.v6"
STATUS="PRE_N_SITE_INGRESS_VS_RESIDENCE_OBSERVATIONAL_NOT_PROMOTED"
V4_BLOB="847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610"
V5_BLOB="bd293c573c85bd849c9e6add06af661bfe519ee9"
V4_SCHEMA="planets-lab.combat-c5-parent-queue-arrival-uncertainty.v4"
V5_SCHEMA="planets-lab.combat-c5-pre-n-site-presence-partition.v5"
V4_STATUS="PARENT_NO_PAIR_IS_SITE_ROSTER_CONDITIONAL_NOT_HOST_EXHAUSTION"
V5_STATUS="UNRESOLVED_TMINUS1_ARRIVALS_PARTITIONED_BY_PRE_N_SITE_HISTORY_NOT_PREDICTED"
NO_PAIR="ABSTAIN_PARENT_STANDARD_NO_PAIR"
PRIOR="PRIOR_SAME_SITE_VCR_PARTICIPANT_CARRY_UNRESOLVED"
UNSEEN="NOT_SEEN_IN_PRIOR_SITE_VCR_TMINUS1_ARRIVAL_UNRESOLVED"
SITE_FIELDS=("game_id","turn","x","y")


def integer(x:Any)->int|None:
    return x if type(x) is int else None


def read_pinned(path:Path, expected_blob:str)->dict[str,Any]:
    raw=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    if actual!=expected_blob:
        raise ValueError(f"published source Git blob SHA1 mismatch: {path}")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("pinned report root must be mapping")
    return obj


def _site_key(site:Mapping[str,Any])->tuple[int,int,int,int]:
    values=tuple(integer(site.get(k)) for k in SITE_FIELDS)
    if None in values or values[0]<=0 or values[1]<1:
        raise ValueError("invalid frozen V4/V5 site identity")
    return values


def _sites(report:Mapping[str,Any], label:str)->dict[tuple[int,int,int,int],Mapping[str,Any]]:
    records=report.get("site_evaluations")
    if not isinstance(records,list) or len(records)!=27:
        raise ValueError(f"{label} site population unavailable")
    index={}
    for s in records:
        if not isinstance(s,Mapping):
            raise ValueError(f"{label} site row is not mapping")
        key=_site_key(s)
        if key in index:
            raise ValueError(f"{label} site duplicated")
        index[key]=s
    return index


def validate_sources(v4:Mapping[str,Any],v5:Mapping[str,Any]):
    if v4.get("schema")!=V4_SCHEMA or v4.get("status")!=V4_STATUS:
        raise ValueError("published V4 identity/status changed")
    if (v5.get("schema")!=V5_SCHEMA or v5.get("status")!=V5_STATUS
            or v5.get("source_v4_git_blob_sha1")!=V4_BLOB
            or v5.get("source_census_git_blob_sha1")!=v4.get("source_census_git_blob_sha1")
            or v5.get("source_db_sha256")!=v4.get("source_db_sha256")):
        raise ValueError("published V5 identity/provenance changed")
    sv4=v4.get("summary")
    sv5=v5.get("summary")
    checks4={
        "frozen_sites":27,"frozen_adjacent_transitions":63,
        "risk_evaluations":56,"not_inspected_due_to_missing_context":7,
        "original_V2_conditional_predictions":9,
        "original_V2_conditional_exact":7,
        "new_combat_pair_predictions":0,
        "changed_original_V2_predictions":0,
        "Nplus1_used_in_risk_guard":False,
    }
    checks5={
        "frozen_sites":27,"frozen_transitions":63,
        "evaluated_transitions":56,"source_uninspected":7,
        "NO_PAIR_transitions":25,"NO_PAIR_sites":12,
        "original_V4_witness_appearances":219,
        "NO_PAIR_witness_appearances":157,
        "NO_PAIR_prior_site_witness_appearances":50,
        "NO_PAIR_unseen_prior_site_witness_appearances":107,
        "new_battle_predictions":0,"changed_V2_predictions":0,
        "Nplus1_comparator_used":False,
    }
    if (not isinstance(sv4,Mapping) or not isinstance(sv5,Mapping)
            or any(sv4.get(k)!=v for k,v in checks4.items())
            or any(sv5.get(k)!=v for k,v in checks5.items())):
        raise ValueError("frozen V4/V5 cohort or prediction-count drift")
    a,b=_sites(v4,"V4"),_sites(v5,"V5")
    if set(a)!=set(b):
        raise ValueError("V4/V5 frozen site membership differs")
    return a,b


def spatial_classification(raw:Mapping[str,Any],prior_id:Any,*,through_n:int)->str:
    """Classify a risk witness without inferring movement or terminal survival."""
    start=raw.get("start_at_site")
    waypoint=raw.get("waypoint_at_site")
    if type(start) is not bool or type(waypoint) is not bool or not (start or waypoint):
        raise ValueError("invalid T-1 site evidence flags")
    if prior_id is not None:
        if integer(prior_id) is None or prior_id<=0 or prior_id>=through_n:
            raise ValueError("prior VCR must be strictly earlier than current N")
        return "PRIOR_SITE_VCR_CARRY_UNRESOLVED"
    if start and waypoint:
        return "UNSEEN_TMINUS1_START_AND_WAYPOINT_AT_SITE"
    if start:
        return "UNSEEN_TMINUS1_START_AT_SITE_ONLY"
    return "UNSEEN_TMINUS1_WAYPOINT_AT_SITE_ONLY"


def merge_transition(a:Mapping[str,Any],b:Mapping[str,Any])->dict[str,Any]:
    n=integer(a.get("from_vcr_id"))
    if n is None or n<1 or b.get("from_vcr_id")!=n:
        raise ValueError("V4/V5 current N identity mismatch")
    if (a.get("original_conditional_v2_status")!=b.get("original_v2_status")
            or a.get("risk_status")!=b.get("original_v4_risk_status")
            or a.get("future_Nplus1_used") is not False
            or a.get("original_next_pair_or_side_changed") is not False
            or b.get("Nplus1_ship_identity_used") is not False
            or b.get("new_battle_prediction") is not False
            or b.get("terminal_outcome_or_survival_inferred") is not False):
        raise ValueError("V4/V5 nonleakage/prediction invariant violated")
    v4rows=a.get("Tminus1_plausible_arrivals")
    v5rows=b.get("witnesses")
    if not isinstance(v4rows,list) or not isinstance(v5rows,list):
        raise ValueError("V4/V5 witness list missing")
    if (len(v4rows)!=len(v5rows)
            or a.get("independent_Tminus1_plausible_arrival_count")!=len(v4rows)
            or b.get("V4_potential_arrival_count")!=len(v4rows)):
        raise ValueError("V4/V5 witness denominator differs")
    aindex={}
    for w in v4rows:
        if not isinstance(w,Mapping):
            raise ValueError("invalid V4 witness")
        sid,owner=integer(w.get("ship_id")),integer(w.get("owner_id"))
        if sid is None or sid<=0 or owner is None or owner<=0 or sid in aindex:
            raise ValueError("duplicate/invalid V4 witness")
        aindex[sid]=w
    out=[]
    ids=set()
    for w in v5rows:
        if not isinstance(w,Mapping):
            raise ValueError("invalid V5 witness")
        sid,owner=integer(w.get("ship_id")),integer(w.get("owner_id"))
        if sid in ids or sid not in aindex or owner is None or owner<=0:
            raise ValueError("duplicate/foreign V5 witness")
        ids.add(sid)
        origin=aindex[sid]
        if (owner!=origin.get("owner_id")
                or w.get("position_source")!=origin.get("position_source")
                or w.get("site_history_not_terminal_survival_evidence") is not True):
            raise ValueError("V4/V5 witness owner/source drift")
        prior=w.get("first_prior_site_vcr_id")
        expected=(PRIOR if prior is not None else UNSEEN)
        if w.get("class")!=expected:
            raise ValueError("V5 historical witness class drift")
        cls=spatial_classification(origin,prior,through_n=n)
        out.append({
            "ship_id":sid,"owner_id":owner,
            "position_source":w["position_source"],
            "first_prior_site_vcr_id":prior,
            "Tminus1_start_at_site":origin["start_at_site"],
            "Tminus1_waypoint_at_site":origin["waypoint_at_site"],
            "class":cls,
        })
    prior_count=sum(x["first_prior_site_vcr_id"] is not None for x in out)
    if (len(ids)!=len(aindex)
            or prior_count!=b.get("prior_site_VCR_participant_count")
            or len(out)-prior_count!=b.get("not_seen_in_prior_site_VCR_count")):
        raise ValueError("V5 temporal/witness count drift")
    spatial=[x["class"] for x in out]
    if a["original_conditional_v2_status"]==NO_PAIR:
        if "UNSEEN_TMINUS1_WAYPOINT_AT_SITE_ONLY" in spatial:
            verdict="ABSTAIN_WAYPOINT_ONLY_INGRESS_UNRESOLVED"
        elif any(v.startswith("UNSEEN_TMINUS1_") for v in spatial):
            verdict="ABSTAIN_TMINUS1_START_RESIDENCE_UNRESOLVED"
        elif prior_count:
            verdict="ABSTAIN_ONLY_PRIOR_SITE_CARRY_UNRESOLVED"
        else:
            verdict="NO_PAIR_NOT_PROVEN_NO_INDEXED_WITNESS"
    else:
        verdict="ORIGINAL_NON_NO_PAIR_VERDICT_UNCHANGED"
    return {
        "from_vcr_id":n,
        "original_v2_status":a["original_conditional_v2_status"],
        "original_v4_status":a["risk_status"],
        "original_v5_status":b["partition_status"],
        "spatial_guard_status":verdict,
        "Tminus1_witnesses":out,
        "Nplus1_used":False,
        "new_pair_predictions":0,
    }


def build_report(v4:Mapping[str,Any],v5:Mapping[str,Any])->dict[str,Any]:
    sites4,sites5=validate_sources(v4,v5)
    results=[]
    for key in sorted(sites4):
        a,b=sites4[key],sites5[key]
        if (b.get("V4_original_uninspected")!=
                a.get("original_unattempted_transitions",0)+a.get("additional_risk_unavailable",0)):
            raise ValueError("uninspected V4/V5 count drift")
        rows4,rows5=a.get("transition_risks"),b.get("transition_partitions")
        if not isinstance(rows4,list) or not isinstance(rows5,list):
            raise ValueError("source transition list missing")
        index={}
        for t in rows4:
            if not isinstance(t,Mapping):
                raise ValueError("invalid V4 transition")
            n=integer(t.get("from_vcr_id"))
            if n is None or n in index:
                raise ValueError("duplicate/invalid V4 transition")
            index[n]=t
        got=[]
        for t in rows5:
            if not isinstance(t,Mapping):
                raise ValueError("invalid V5 transition")
            n=integer(t.get("from_vcr_id"))
            if n not in index or any(r["from_vcr_id"]==n for r in got):
                raise ValueError("duplicate/foreign V5 transition")
            got.append(merge_transition(index[n],t))
        if len(index)!=len(got):
            raise ValueError("source V4/V5 transitions incomplete")
        results.append({**dict(zip(SITE_FIELDS,key)),
                        "source_uninspected":b["V4_original_uninspected"],
                        "transition_evaluations":got})
    allrows=[x for s in results for x in s["transition_evaluations"]]
    no=[t for t in allrows if t["original_v2_status"]==NO_PAIR]
    if len(results)!=27 or len(allrows)!=56 or len(no)!=25 or sum(s["source_uninspected"] for s in results)!=7:
        raise ValueError("V4/V5 population changed")
    if sum(len(t["Tminus1_witnesses"]) for t in allrows)!=219:
        raise ValueError("V4 219 witness appearances drift")
    if sum(len(t["Tminus1_witnesses"]) for t in no)!=157:
        raise ValueError("V4 157 NO_PAIR witness appearances drift")
    unseen=[(s,t,w) for s in results for t in s["transition_evaluations"]
            if t["original_v2_status"]==NO_PAIR
            for w in t["Tminus1_witnesses"] if w["first_prior_site_vcr_id"] is None]
    prior=[w for t in no for w in t["Tminus1_witnesses"]
           if w["first_prior_site_vcr_id"] is not None]
    if len(unseen)!=107 or len(prior)!=50:
        raise ValueError("V5 NO_PAIR prior/unseen source population drift")
    dedup={}
    per_source=Counter()
    for site,t,w in unseen:
        key=tuple(site[k] for k in SITE_FIELDS)+(w["ship_id"],)
        val=(w["owner_id"],w["position_source"],w["class"])
        if key in dedup and dedup[key]!=val:
            raise ValueError("T-1 identity/source/spatial geometry changed across site transitions")
        dedup[key]=val
        per_source[w["position_source"]]+=1
    unique_cls=Counter(x[2] for x in dedup.values())
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_v4_git_blob_sha1":V4_BLOB,"source_v5_git_blob_sha1":V5_BLOB,
        "source_db_generation":v4.get("source_db_generation"),
        "source_db_sha256":v4.get("source_db_sha256"),
        "summary":{
            "frozen_sites":27,"frozen_adjacent_transitions":63,
            "evaluated_transitions":56,"source_uninspected":7,
            "NO_PAIR_transitions":25,
            "V4_witness_appearances":219,
            "NO_PAIR_witness_appearances":157,
            "NO_PAIR_prior_site_witness_appearances":50,
            "NO_PAIR_unseen_prior_site_witness_appearances":107,
            "NO_PAIR_unique_unseen_site_ship_witnesses":len(dedup),
            "NO_PAIR_unique_unseen_spatial_classes":dict(sorted(unique_cls.items())),
            "NO_PAIR_unseen_appearance_spatial_classes":dict(sorted(
                Counter(w["class"] for _,_,w in unseen).items())),
            "NO_PAIR_unseen_appearance_source_counts":dict(sorted(per_source.items())),
            "NO_PAIR_transition_spatial_guard_counts":dict(sorted(Counter(
                t["spatial_guard_status"] for t in no).items())),
            "new_battle_predictions":0,
            "changed_original_V2_predictions":0,
            "Nplus1_used":False,
            "Host_site_exhaustion_proven":False,
        },
        "sites":results,
        "boundary":(
            "Join of immutable V4 T-1 raw start/waypoint flags and V5 strictly pre-N "
            "site-history classes. T-1 start-at-site is not confirmed T site presence; "
            "T-1 waypoint-at-site is not confirmed arrival; earlier VCR presence "
            "is not confirmed postbattle survival. Candidate rows repeated across "
            "transitions are deduplicated by (game,turn,x,y,ship). No new Host "
            "mechanic, pair, eligibility or ship position prediction. No future "
            "N+1 observations enter any computation."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-v4",type=Path,required=True)
    p.add_argument("--frozen-v5",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        v4=read_pinned(args.frozen_v4,V4_BLOB)
        v5=read_pinned(args.frozen_v5,V5_BLOB)
        report=build_report(v4,v5)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=args.output.with_suffix(args.output.suffix+".tmp")
        temp.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(args.output)
    except (OSError,TypeError,ValueError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== C5 TMINUS1 INGRESS VERSUS RESIDENCE V6 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
