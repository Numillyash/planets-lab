"""M2: posthoc four-family archival stock-balance interpretation (one run).

Reads ONLY previously published V1 reports, pinned by Git blob and SHA256
manifest. Does not reread or mutate NuHost corpus or source simulator.
Strict cross-family tuple join prevents cherry-picking a denominator.
All residuals are observational and remain unattributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/"src") not in sys.path:sys.path.insert(0,str(ROOT/"src"))

from planets_lab.sim.planetary_evidence_gates import (
    FAMILIES,join_four,summarize_joint,summarize_resource,
    summarize_population,
)

SCHEMA="planets-lab.m2-four-family-evidence-gate.v1"
STATUS="M2_HISTORICAL_STOCK_RESIDUALS_ATTRIBUTION_UNPROVEN"
BASELINE_SCHEMA="planets-lab.planetary-historical-differential.v1"
BASELINE_STATUS="M2_ARCHIVAL_OWNER_CURRENT_CONDITIONAL_TMINUS1_TO_T_NOT_CAUSAL"
CORPUS_SHA256="af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a"
PUBLISHED_BLOBS={
    "manifest":"c2d95b1c50d89895a30497f0008c0e0f486d12ef",
    "supplies":"984f481fdafcd797aa388fb14557d22962021675",
    "taxes":"fd28daed75e486f3f9c19e125009c589f03ac9a5",
    "minerals":"638de25e2417e07bcd3a8ab8be3cf0acb3b046d4",
    "populations":"e3dcc585ca5d00617136069e8d8060e2618296a1",
}
OUTPUTS=("joint_controls","resource_balances","population_balances")
EXPECTED_EXACT={"supplies":312,"taxes":358,"minerals":440,"populations":481}
EXPECTED_MISMATCH={"supplies":305,"taxes":259,"minerals":177,"populations":136}
EXPECTED_STATUS={"ABSTAIN_MODEL_UNSUPPORTED":16,"ABSTAIN_OWNER_CHANGED":5,
                 "ABSTAIN_T_ARCHIVE_IDENTITY_UNTRUSTED":11,
                 "ABSTAIN_T_OWNER_CURRENT_MISSING":1}


def pinned_json(path:Path,sha:str)->tuple[dict[str,Any],bytes]:
    data=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
    if actual!=sha:raise ValueError("source published Git blob changed: "+str(path))
    obj=json.loads(data)
    if not isinstance(obj,dict):raise ValueError("source report is not JSON object")
    return obj,data


def check_sources(reports:dict[str,dict[str,Any]],data:dict[str,bytes]):
    manifest=reports["manifest"]
    if (manifest.get("schema")!=BASELINE_SCHEMA
        or manifest.get("status")!="M2_FOUR_FAMILY_HISTORICAL_ARCHIVE_COMPARISONS_COMPLETE"
        or manifest.get("all_four_complete") is not True
        or manifest.get("causal_NuHost_parity_claimed") is not False
        or manifest.get("C5_frozen_not_reopened") is not True
        or manifest.get("new_corpus_sha256")!=CORPUS_SHA256):
        raise ValueError("V1 original evidence manifest drift")
    arrays={}
    for fam in FAMILIES:
        r=reports[fam]
        m=manifest.get("reports",{}).get(fam)
        if (r.get("schema")!=BASELINE_SCHEMA
            or r.get("status")!=BASELINE_STATUS
            or r.get("family")!=fam
            or r.get("source_corpus_sha256")!=CORPUS_SHA256
            or r.get("all_Tminus1_windows_frozen_before_first_T") is not True
            or r.get("real_Host_phase_mechanism_proven") is not False
            or r.get("conditional_simulation_not_true_Host_causal_attribution") is not True
            or not isinstance(m,dict) or
            m.get("sha256")!=hashlib.sha256(data[fam]).hexdigest()):
            raise ValueError("original source family/manifest integrity drift: "+fam)
        summary=r.get("summary",{})
        if (summary.get("metadata_selected_games")!=8
            or summary.get("metadata_selected_windows")!=32
            or summary.get("Tminus1_authentic_owner_planet_rows")!=650
            or summary.get("comparable_qualified_rows")!=617
            or summary.get("abstention_count")!=33
            or summary.get("conditionally_all_field_exact")!=EXPECTED_EXACT[fam]
            or summary.get("conditionally_all_field_mismatch")!=EXPECTED_MISMATCH[fam]):
            raise ValueError("published original exact/mismatch/abstain denominator drift: "+fam)
        for state,count in EXPECTED_STATUS.items():
            if summary.get("status_counts",{}).get(state)!=count:
                raise ValueError("archive integrity/unsupported status drift: "+fam)
        rows=r.get("Tminus1_frozen_conditional_predictions_and_archived_T")
        if not isinstance(rows,list) or len(rows)!=650:
            raise ValueError("published 650 planet rows absent: "+fam)
        arrays[fam]=rows
    joined=join_four(arrays)
    joint=summarize_joint(joined)
    if (joint["all_source_planet_rows"]!=650 or
        joint["qualified_four_family_planets"]!=617 or
        joint["abstained_four_family_planets"]!=33):
        raise ValueError("cross-family joined original population drift")
    return joined


def cluster_counts(joined):
    by_window=defaultdict(Counter)
    by_game=defaultdict(Counter)
    unique=defaultdict(set)
    for r in joined:
        key=(r["game_id"],r["turn"])
        label="ABSTAIN" if not r["qualified"] else (
            "FOUR_FAMILY_EXACT" if r["signature"]=="EEEE" else
            "AT_LEAST_ONE_FAMILY_DIFFERS")
        by_window[key][label]+=1
        by_game[r["game_id"]][label]+=1
        unique[r["game_id"]].add(r["planet_id"])
    return {
        "by_game_turn":{
            f"{g}/{t}":dict(sorted(x.items()))
            for (g,t),x in sorted(by_window.items())
        },
        "by_game":{
            str(g):{
                **dict(sorted(x.items())),
                "distinct_planet_ids":len(unique[g]),
            }
            for g,x in sorted(by_game.items())
        },
    }


def build(reports,data):
    joined=check_sources(reports,data)
    common={
        "schema":SCHEMA,"status":STATUS,
        "source_4_family_manifest_git_blob_sha1":PUBLISHED_BLOBS["manifest"],
        "source_corpus_sha256":CORPUS_SHA256,
        "new_archival_records_or_NuHost_reads":0,
        "original_frozen_predictions_or_denominators_modified":False,
        "C5_mechanic_or_executor_changed":False,
        "causal_Host_phase_attribution_proven":False,
        "same_public8_archive_not_new_independent_validation":True,
    }
    clusters=cluster_counts(joined)
    joint={
        **common,"phase":"joint_controls",
        "summary":summarize_joint(joined),
        "game_and_window_cluster_counts":clusters,
        "joined_original_qualified_and_abstained_planets":joined,
    }
    resource={
        **common,"phase":"resource_balances",
        "summary":summarize_resource(joined),
        "residual_signatures_are_not_proof_of_cargo_transfers":True,
    }
    population={
        **common,"phase":"population_balances",
        "summary":summarize_population(joined),
        "population_deltas_do_not_identify_colonist_transport_or_growth_causally":True,
    }
    return (joint,resource,population)


def publish(folder:Path,documents):
    folder.mkdir(parents=True,exist_ok=True)
    entries={}
    for name,doc in zip(OUTPUTS,documents,strict=True):
        dest=folder/(name+".json")
        temp=dest.with_suffix(".json.tmp")
        temp.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(dest)
        entries[name]={
            "file":dest.name,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
            "summary":doc["summary"],
        }
        print("===== M2 FOUR-FAMILY EVIDENCE GATE",name,"=====")
        print("status:",doc["status"])
        print("summary:",doc["summary"])
        print("output:",dest)
    manifest={
        "schema":SCHEMA,
        "status":"M2_FOUR_FAMILY_EVIDENCE_TRIANGULATION_BATCH_COMPLETE",
        "all_three_reports_complete":len(entries)==3,
        "source_manifest_git_blob_sha1":PUBLISHED_BLOBS["manifest"],
        "source_corpus_sha256":CORPUS_SHA256,
        "research_C5_reopened":False,
        "causal_Host_formula_or_order_explanation_proven":False,
        "reports":entries,
    }
    dest=folder/"manifest.json"
    temp=dest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    temp.replace(dest)
    print("===== M2 EVIDENCE GATES ALL THREE REPORTS COMPLETE =====")
    print("status:",manifest["status"])
    print("output:",dest)


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    try:
        docs={}
        data={}
        for name,sha in PUBLISHED_BLOBS.items():
            docs[name],data[name]=pinned_json(args.source_dir/(name+".json"),sha)
        results=build(docs,data)
        publish(args.output_dir,results)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as error:
        print("ERROR M2 evidence gate:",error,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
