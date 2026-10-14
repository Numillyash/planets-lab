"""C5 general parent-NO_PAIR soundness gate with independent T-1 arrival risk.

Unlike a held-out next-battle forecast, this report does not change any
frozen V2 predictions. It diagnoses whether V2's "no remaining pair" is
unsafe to promote as complete Host queue exhaustion while T-1 ships with
unknown movement MAY arrive at the known current-N site.

No future VCR N+1 is accessed. Ship candidate roster comes solely from
T-1 owner snapshots and current VCR N identity/owner for a conservative
lower-bound guard; it never creates new ship battles or positions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter,defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT/"src",Path(__file__).resolve().parent):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.rules.combat.site_input_adapter import (
    potential_tminus1_site_arrivals,
)
import combat_c5_ordinary_parent_forward_v1 as v1
import combat_c5_current_n_roster_bridge_v2 as v2
import combat_public_capture_o_layer_probe as context_builder

SCHEMA="planets-lab.combat-c5-parent-queue-arrival-uncertainty.v4"
STATUS="PARENT_NO_PAIR_IS_SITE_ROSTER_CONDITIONAL_NOT_HOST_EXHAUSTION"
CENSUS_SHA1="fda92475988d2f7dfbc7b93606de4f8cec909806"
V2_SHA1="dd641864dc3bd541098ea2c21cf21fb8ff03d5ce"
GENERATION=v1.GENERATION
SHA256=v1.SHA256


def integer(v:Any)->int|None:
    return v if isinstance(v,int) and not isinstance(v,bool) else None


def pinned(path:Path,sha1:str)->dict[str,Any]:
    raw=path.read_bytes()
    if v1.blob_sha1(raw)!=sha1:
        raise ValueError("published source Git blob SHA1 mismatch")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("frozen report not mapping")
    return obj


def frozen_sites(census:Mapping[str,Any],v2report:Mapping[str,Any]):
    sites=v1.freeze_sites(census)
    if (v2report.get("schema")!=v2.SCHEMA or
        v2report.get("status")!=v2.STATUS or
        v2report.get("source_census_git_blob_sha1")!=CENSUS_SHA1 or
        v2report.get("source_db_sha256")!=SHA256):
        raise ValueError("V2 frozen source identity/status mismatch")
    summary=v2report.get("summary")
    want={"frozen_sites":27,"frozen_adjacent_ID_transitions":63,
          "attempted_transitions":56,"site_failure_transitions":7,
          "conditional_predictions_made":9,
          "conditional_pair_and_sides_exact":7,
          "conditional_pair_or_sides_mismatch":2}
    if not isinstance(summary,Mapping) or any(summary.get(k)!=v for k,v in want.items()):
        raise ValueError("V2 frozen population drift")
    bysite={}
    for s in v2report.get("site_evaluations",[]):
        key=(s["game_id"],s["turn"],s["x"],s["y"])
        if key in bysite:raise ValueError("duplicate frozen V2 site")
        bysite[key]=s
    if len(bysite)!=27 or set(bysite)!={
        (s["game_id"],s["turn"],s["x"],s["y"]) for s in sites
    }:
        raise ValueError("frozen V2 sites differ from census")
    for s in sites:
        o=bysite[(s["game_id"],s["turn"],s["x"],s["y"])]
        pairs={(t["from_vcr_id"],t["to_vcr_id"]) for t in o["transitions"]}
        if len(pairs)+o["missing"]!=len(s["adjacent_pairs"]) or not pairs.issubset(set(s["adjacent_pairs"])):
            raise ValueError("frozen transition membership drift")
    return sites,bysite


def guarded_transition(
    *,frozen:Mapping[str,Any],
    predictions:Mapping[int,Mapping[str,Any]],
    current_vcr_payload:Mapping[str,Any],site:tuple[int,int],
)->dict[str,Any]:
    """This function has NO next-VCR or future opponent argument."""
    current={}
    for side in ("left","right"):
        body=current_vcr_payload.get(side)
        owner=integer(current_vcr_payload.get(side+"ownerid"))
        sid=integer(body.get("objectid")) if isinstance(body,Mapping) else None
        if sid is None or owner is None or sid<=0 or owner<=0:
            raise ValueError("current VCR N owner/ship not known")
        current[sid]={"owner_id":owner}
    if len(current)!=2:
        raise ValueError("same ship N both sides")
    risk=potential_tminus1_site_arrivals(
        predictions=predictions,active_ships=current,site=site)
    rows=[{
        "ship_id":r.ship_id,"owner_id":r.owner_id,
        "position_source":r.position_source,
        "start_at_site":r.start_at_site,
        "waypoint_at_site":r.waypoint_at_site,
    } for r in risk]
    status=frozen.get("status")
    if status=="ABSTAIN_PARENT_STANDARD_NO_PAIR":
        verdict=("ABSTAIN_PLAUSIBLE_UNRESOLVED_TMINUS1_ARRIVALS"
                 if rows else "NO_PAIR_NOT_PROVEN_NO_ARRIVALS_IN_LIMITED_TMINUS1_INDEX")
    else:
        verdict="ORIGINAL_VERDICT_UNCHANGED_OBSERVATIONAL_RISK"
    return {
        "from_vcr_id":frozen["from_vcr_id"],
        "original_conditional_v2_status":status,
        "original_conditional_v2_exact":frozen.get("factual_comparison",{}).get("exact"),
        "risk_status":verdict,
        "independent_Tminus1_plausible_arrival_count":len(rows),
        "Tminus1_plausible_arrivals":rows,
        "only_known_current_N_active_owners_used":True,
        "future_Nplus1_used":False,
        "original_next_pair_or_side_changed":False,
    }


def build_report(census:Mapping[str,Any],v2report:Mapping[str,Any],conn:Any)->dict[str,Any]:
    sites,by_site=frozen_sites(census,v2report)
    groups=defaultdict(list)
    for s in sites:groups[(s["game_id"],s["turn"])].append(s)
    results=[]
    for i,((game,turn),window_sites) in enumerate(sorted(groups.items()),1):
        print(f"[c5-arrival-guard] [{i}/{len(groups)}] G{game} T{turn} sites={len(window_sites)}",flush=True)
        contexts={}
        error=None
        cases={}
        try:
            appearances,_=context_builder._collect_targeted_appearances_from_db(
                connection=conn,game_id=game,battle_turns={turn})
            context_builder._visit_targeted_site_contexts(
                connection=conn,game_id=game,
                targets={(game,turn,s["x"],s["y"]):() for s in window_sites},
                appearances=appearances,
                observer=lambda ctx:contexts.__setitem__(
                    (ctx["game_id"],ctx["battle_turn"],ctx["x"],ctx["y"]),dict(ctx)))
            cases=combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
        except (ValueError,TypeError,KeyError) as exc:
            error=f"{type(exc).__name__}:{exc}"
        for site in window_sites:
            key=(game,turn,site["x"],site["y"])
            frozen=by_site[key]
            ctx=contexts.get(key)
            rows=[]
            missed=0
            for tr in frozen["transitions"]:
                n=tr["from_vcr_id"]
                case=cases.get((turn,n))
                if ctx is None or case is None:
                    missed+=1
                    continue
                try:
                    row=guarded_transition(
                        frozen=tr,predictions=ctx["predictions"],
                        current_vcr_payload=case.payload,
                        site=(site["x"],site["y"]))
                except (ValueError,KeyError,TypeError) as exc:
                    row={
                        "from_vcr_id":n,
                        "original_conditional_v2_status":tr["status"],
                        "risk_status":"ABSTAIN_RISK_EVIDENCE_MISSING",
                        "reason":f"{type(exc).__name__}:{exc}",
                        "independent_Tminus1_plausible_arrival_count":None,
                        "Tminus1_plausible_arrivals":[],
                        "future_Nplus1_used":False,
                        "original_next_pair_or_side_changed":False}
                rows.append(row)
            results.append({
                "game_id":game,"turn":turn,"x":site["x"],"y":site["y"],
                "original_site_status":frozen["status"],
                "original_unattempted_transitions":frozen["missing"],
                "additional_risk_unavailable":missed,
                "context_error":error,
                "preselected_frozen_vcr_pairs":site["adjacent_pairs"],
                "transition_risks":rows,
            })
    observed=[r for s in results for r in s["transition_risks"]]
    missed=sum(s["original_unattempted_transitions"]+s["additional_risk_unavailable"] for s in results)
    if len(results)!=27 or len(observed)+missed!=63:
        raise ValueError("63-transition site-accounting mismatch")
    orig=Counter(r["original_conditional_v2_status"] for r in observed)
    risks=Counter(r["risk_status"] for r in observed)
    per_source=Counter(
        a["position_source"] for r in observed
        for a in r["Tminus1_plausible_arrivals"])
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_census_git_blob_sha1":CENSUS_SHA1,
        "source_conditional_v2_git_blob_sha1":V2_SHA1,
        "source_db_generation":GENERATION,"source_db_sha256":SHA256,
        "summary":{
            "frozen_sites":27,"frozen_adjacent_transitions":63,
            "original_V2_conditional_predictions":9,
            "original_V2_conditional_exact":7,
            "risk_evaluations":len(observed),
            "not_inspected_due_to_missing_context":missed,
            "original_V2_status_counts_on_evaluated":dict(sorted(orig.items())),
            "guard_status_counts":dict(sorted(risks.items())),
            "plausible_arrival_Tminus1_source_counts":dict(sorted(per_source.items())),
            "new_combat_pair_predictions":0,
            "changed_original_V2_predictions":0,
            "Host_site_exhaustion_proven":False,
            "Nplus1_used_in_risk_guard":False,
            "race12_Horwasp_promoted":False,
        },
        "site_evaluations":results,
        "boundary":(
            "Potential arrival = unresolved T-1 position plus independent "
            "owner/raw ship identity with T-1 start or waypoint at the already "
            "known current-N site, and a distinct current-N owner. This is a "
            "bounded lower-bound uncertainty witness only; tow or mine behavior "
            "is NOT reconstructed. Does not use N+1 identities, outcomes or "
            "positions. Original V2 prediction score 9/7 remains frozen. "
            "A NO_PAIR without a witness does NOT prove complete Host queue "
            "exhaustion. No new pair, seed, combat or movement rule prediction."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-census",type=Path,required=True)
    p.add_argument("--frozen-conditional-v2",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        census=pinned(a.frozen_census,CENSUS_SHA1)
        v2report=pinned(a.frozen_conditional_v2,V2_SHA1)
        frozen_sites(census,v2report)
        db=a.corpus_db_root/GENERATION
        if not db.is_file():raise ValueError("immutable public100 missing")
        st=time.monotonic()
        print("[c5-arrival-guard] verifying pinned public100 SHA256",flush=True)
        with db.open("rb") as f:dig=hashlib.file_digest(f,"sha256").hexdigest()
        if dig!=SHA256:raise ValueError("pinned public100 SHA256 mismatch")
        print(f"[c5-arrival-guard] verified in {time.monotonic()-st:.1f}s; read-only DB",flush=True)
        conn,path=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try:report=build_report(census,v2report,conn)
        finally:conn.close()
        report["db_path"]=str(path)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.output.with_suffix(a.output.suffix+".tmp")
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        tmp.replace(a.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2
    print("===== ORDINARY C5 PARENT QUEUE UNKNOWN ARRIVAL GUARD V4 =====")
    print("status:",report["status"])
    print("summary:",report["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
