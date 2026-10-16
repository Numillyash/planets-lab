from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from planets_lab.sim import planetary_evidence_gates as G

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/planetary_evidence_triangulation_v1.py"
SPEC=importlib.util.spec_from_file_location("m2_evidence_triangulation_v1",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def one(family,*,idx=1,exact=True,status=None):
    fields={
        "supplies":("supplies",),
        "taxes":("megacredits",),
        "minerals":G.MINERALS+G.GROUND,
        "populations":("clans","nativeclans"),
    }[family]
    r={
        "game_id":233802,"turn":2,"planet_id":idx,
        "owner_id":1,"race_id":1,"family":family,
        "status":status or (G.EXACT if exact else G.MISMATCH),
        "Tminus1_to_T_phase_attribution_proven":False,
    }
    if status is not None and status not in G.COMPARABLE:return r
    r["Tminus1"]={f:9 for f in fields}
    r["model_T"]={f:10 for f in fields}
    r["archive_T"]={f:10+(0 if exact else 1 if f==fields[0] else 0)
                    for f in fields}
    r["delta_model"]={f:1 for f in fields}
    r["delta_archive"]={f:r["archive_T"][f]-9 for f in fields}
    return r


def test_strict_complete_join_and_causality_boundary():
    data={fam:[
        one(fam,idx=1),
        one(fam,idx=2,exact=False),
        one(fam,idx=3,status="ABSTAIN_OWNER_CHANGED"),
    ] for fam in G.FAMILIES}
    joined=G.join_four(data)
    assert len(joined)==3
    summary=G.summarize_joint(joined)
    assert summary["qualified_four_family_planets"]==2
    assert summary["four_family_conditional_exact"]==1
    assert summary["abstained_four_family_planets"]==1
    assert summary["signature_counts"]=={"EEEE":1,"MMMM":1}
    assert all(not item["causal_Host_formula_explanation_proven"] for item in joined)
    assert G.summarize_resource(joined)["mineral_8_field_quadrants"]=={
        "ALL_EIGHT_MINERAL_FIELDS_EXACT":1,"SURFACE_ONLY_DEVIATES":1}
    assert G.summarize_population(joined)["population_2_field_quadrants"]=={
        "BOTH_POPULATION_FIELDS_EXACT":1,"COLONIST_ONLY_DEVIATES":1}
    assert G.summarize_resource(joined)["stock_change_cause_attributed_to_player_actions"] is False


def test_fail_on_missing_duplicate_misaligned_or_relabelled_rows():
    data={fam:[one(fam)] for fam in G.FAMILIES}
    data["taxes"]=[]
    with pytest.raises(ValueError,match="coverage mismatch"):
        G.join_four(data)
    data["taxes"]=[one("taxes")]
    data["minerals"].append(one("minerals"))
    with pytest.raises(ValueError,match="duplicate"):
        G.join_four(data)
    data["minerals"]=[one("minerals")]
    data["populations"][0]["owner_id"]=2
    with pytest.raises(ValueError,match="coverage mismatch"):
        G.join_four(data)
    data["populations"][0]["owner_id"]=1
    data["taxes"][0]["family"]="minerals"
    with pytest.raises(ValueError,match="source label drift"):
        G.join_four(data)


def test_frozen_stock_delta_reconciliation_mandatory():
    row=one("supplies",exact=False)
    assert G.signed_residual(row,"supplies")==1
    row["delta_archive"]["supplies"]=666
    with pytest.raises(ValueError,match="reconcile"):
        G.signed_residual(row,"supplies")
    row=one("supplies")
    row["status"]=G.MISMATCH
    data={fam:[one(fam)] for fam in G.FAMILIES}
    data["supplies"]=[row]
    with pytest.raises(ValueError,match="exact/mismatch"):
        G.join_four(data)


def test_source_report_manifest_validation_and_full_650_denominator():
    docs={}
    raw={}
    abstentions=(
        ["ABSTAIN_MODEL_UNSUPPORTED"]*16+
        ["ABSTAIN_OWNER_CHANGED"]*5+
        ["ABSTAIN_T_ARCHIVE_IDENTITY_UNTRUSTED"]*11+
        ["ABSTAIN_T_OWNER_CURRENT_MISSING"]
    )
    for fam in G.FAMILIES:
        rows=[]
        for idx in range(650):
            status=abstentions[idx] if idx<33 else None
            exact=idx-33<M.EXPECTED_EXACT[fam]
            row=one(fam,idx=idx//32+1,exact=exact,status=status)
            row["game_id"]=233802+(idx%8)
            row["turn"]=2+((idx//8)%4)*11
            rows.append(row)
        assert len({G.identity(r) for r in rows})==650
        d={
            "schema":M.BASELINE_SCHEMA,"status":M.BASELINE_STATUS,
            "family":fam,"source_corpus_sha256":M.CORPUS_SHA256,
            "all_Tminus1_windows_frozen_before_first_T":True,
            "real_Host_phase_mechanism_proven":False,
            "conditional_simulation_not_true_Host_causal_attribution":True,
            "summary":{
                "metadata_selected_games":8,"metadata_selected_windows":32,
                "Tminus1_authentic_owner_planet_rows":650,
                "comparable_qualified_rows":617,"abstention_count":33,
                "conditionally_all_field_exact":M.EXPECTED_EXACT[fam],
                "conditionally_all_field_mismatch":M.EXPECTED_MISMATCH[fam],
                "status_counts":{
                    **M.EXPECTED_STATUS,
                    G.EXACT:M.EXPECTED_EXACT[fam],
                    G.MISMATCH:M.EXPECTED_MISMATCH[fam],
                },
            },
            "Tminus1_frozen_conditional_predictions_and_archived_T":rows,
        }
        docs[fam]=d
        raw[fam]=json.dumps(d,sort_keys=True).encode()
    docs["manifest"]={
        "schema":M.BASELINE_SCHEMA,
        "status":"M2_FOUR_FAMILY_HISTORICAL_ARCHIVE_COMPARISONS_COMPLETE",
        "all_four_complete":True,"causal_NuHost_parity_claimed":False,
        "C5_frozen_not_reopened":True,
        "new_corpus_sha256":M.CORPUS_SHA256,
        "reports":{f:{"sha256":hashlib.sha256(raw[f]).hexdigest()}
                   for f in G.FAMILIES},
    }
    joined=M.check_sources(docs,raw)
    assert len(joined)==650
    results=M.build(docs,raw)
    assert len(results)==3
    assert results[0]["summary"]["qualified_four_family_planets"]==617
    assert results[0]["summary"]["four_family_conditional_exact"]==M.EXPECTED_EXACT["supplies"]
    docs["manifest"]["reports"]["supplies"]["sha256"]="tampered"
    with pytest.raises(ValueError,match="integrity drift"):
        M.check_sources(docs,raw)


def test_one_evidence_run_three_signed_report_sha256_manifest(tmp_path):
    joined=G.join_four({fam:[
        one(fam,idx=1),one(fam,idx=2,exact=False),
        one(fam,idx=3,status="ABSTAIN_MODEL_UNSUPPORTED"),
    ] for fam in G.FAMILIES})
    stub={
        "schema":M.SCHEMA,"status":M.STATUS,
        "causal_Host_phase_attribution_proven":False,
        "same_public8_archive_not_new_independent_validation":True,
    }
    trio=(
        {**stub,"phase":"joint_controls",
         "summary":G.summarize_joint(joined),
         "joined_original_qualified_and_abstained_planets":joined},
        {**stub,"phase":"resource_balances",
         "summary":G.summarize_resource(joined)},
        {**stub,"phase":"population_balances",
         "summary":G.summarize_population(joined)},
    )
    M.publish(tmp_path,trio)
    manifest=json.loads((tmp_path/"manifest.json").read_text())
    assert manifest["all_three_reports_complete"] is True
    assert manifest["causal_Host_formula_or_order_explanation_proven"] is False
    for name in M.OUTPUTS:
        assert manifest["reports"][name]["sha256"]==hashlib.sha256(
            (tmp_path/(name+".json")).read_bytes()).hexdigest()
    runner=ROOT/"tools/run-planetary-evidence-triangulation-v1.sh"
    wrapper=ROOT/"tools/run-planetary-evidence-triangulation-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    assert M.PUBLISHED_BLOBS["manifest"] in runner.read_text()
    assert "planetary_evidence_triangulation_v1.py" in runner.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "--include artifacts/planetary/evidence-triangulation-v1/published" in wrapper.read_text()
    assert "/CURRENT" not in runner.read_text()
