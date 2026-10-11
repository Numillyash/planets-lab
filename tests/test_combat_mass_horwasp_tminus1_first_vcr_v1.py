from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/diagnostics/combat_mass_horwasp_tminus1_first_vcr_v1.py"
SPEC = importlib.util.spec_from_file_location("horwasp_first_vcr", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def sample_row(*, vcr_id=7, mass=950, ship=513, clans=24000,
               cap=24000, h=475, side="left"):
    return {
        "game_id": 350094, "turn": 153, "vcr_id": vcr_id,
        "side": side, "owner_id": 30, "ship_id": ship,
        "hull_id": 115, "cohort": "LATE_85TH_PERCENTILE",
        "Tminus1_static_hull_mass": h,
        "Tminus1_owner_race": 12,
        "original_conditional_candidate_KT": h,
        "factual_current_VCR_mass_KT": mass,
        "observational_residual": {
            "delta_KT": mass-h,
            "VCR_left_baycount_observed": 9,
        },
        "historical_Tminus1_owner_ship": {
            "status": "RESOLVED_TMINUS1_OWNER_SHIP",
            "tminus1_hull": {"id": 115, "mass": h, "cargo": cap},
            "tminus1_ship": {"id": ship, "clans": clans, "hullid": 115},
        },
        "independent_Tminus1_clan_and_capacity": {
            "clans": clans,
            "hull_cargo_capacity": cap,
            "independently_precombat_seen": True,
        },
    }


def test_exact_integer_floor_hypothesis_and_full_load_controls():
    full = M.hypothetical_clan_component(
        hull_mass=475, clans=24000, cargo_capacity=24000,
        catalog_mass=475,
    )
    assert full["hypothetical_clan_component_KT"] == 475
    assert full["hypothetical_no_carrier_mass_KT"] == 950
    assert full["is_full_load_Tminus1"] is True
    assert full["full_mass_prediction_KT"] is None
    assert full["linear_floor_rule_independently_proven"] is False

    partial = M.hypothetical_clan_component(
        hull_mass=200, clans=228, cargo_capacity=300, catalog_mass=200
    )
    assert partial["hypothetical_clan_component_KT"] == 152
    assert partial["hypothetical_no_carrier_mass_KT"] == 352
    assert partial["is_full_load_Tminus1"] is False
    # Floor vs ceiling matters: 31*100/1600 = 1.9375.
    sparse = M.hypothetical_clan_component(
        hull_mass=31, clans=100, cargo_capacity=1600, catalog_mass=31
    )
    assert sparse["hypothetical_clan_component_KT"] == 1
    assert sparse["hypothetical_no_carrier_mass_KT"] == 32


@pytest.mark.parametrize("h,cargo,clans,catalog,reason", [
    (145, 900, None, 145, "ABSTAIN_INCOMPLETE_TMINUS1_CLAN_OR_CATALOG"),
    (145, 900, True, 145, "ABSTAIN_INCOMPLETE_TMINUS1_CLAN_OR_CATALOG"),
    (145, 0, 900, 145, "ABSTAIN_INVALID_TMINUS1_CLAN_RANGE"),
    (145, 900, 901, 145, "ABSTAIN_INVALID_TMINUS1_CLAN_RANGE"),
    (145, 900, -1, 145, "ABSTAIN_INVALID_TMINUS1_CLAN_RANGE"),
    (145, 900, 900, 125, "ABSTAIN_TMINUS1_HULL_CATALOG_MISMATCH"),
])
def test_invalid_owner_prestate_fails_closed(h,cargo,clans,catalog,reason):
    p = M.hypothetical_clan_component(
        hull_mass=h,clans=clans,cargo_capacity=cargo,catalog_mass=catalog
    )
    assert p["status"] == reason
    assert p["hypothetical_no_carrier_mass_KT"] is None


def test_predictor_ignores_factual_current_vcr_mass_and_bays():
    a=sample_row(vcr_id=1778,mass=950)
    b=sample_row(vcr_id=1778,mass=725)
    b["observational_residual"]["VCR_left_baycount_observed"] = 0
    assert M.no_mass_oracle_forecast(a) == M.no_mass_oracle_forecast(b)
    assert M.evaluate_after_forecast(
        M.no_mass_oracle_forecast(a), factual_vcr_mass=a["factual_current_VCR_mass_KT"],
        side="left",left_vcr_bays_ANNOTATION_ONLY=0
    )["hypothetical_no_carrier_equals_factual_mass"] is True
    assert M.evaluate_after_forecast(
        M.no_mass_oracle_forecast(b), factual_vcr_mass=b["factual_current_VCR_mass_KT"],
        side="left",left_vcr_bays_ANNOTATION_ONLY=0
    )["hypothetical_no_carrier_equals_factual_mass"] is False


def test_carrier_branch_only_retrospective_and_never_predicted():
    p=M.no_mass_oracle_forecast(sample_row(h=75,cap=300,clans=300,mass=510))
    assert p["hypothetical_no_carrier_mass_KT"] == 150
    e=M.evaluate_after_forecast(p, factual_vcr_mass=510, side="right",
                                left_vcr_bays_ANNOTATION_ONLY=6)
    assert e["hypothetical_plus360_equals_factual_mass"] is True
    assert e["plus360_is_a_counterfactual_not_a_predicted_RNG_outcome"] is True
    assert p["carrier_plus360_RNG_predicted"] is False
    control=M.evaluate_after_forecast(p, factual_vcr_mass=510, side="left",
                                       left_vcr_bays_ANNOTATION_ONLY=6)
    assert control["hypothetical_plus360_equals_factual_mass"] is None


def test_missing_tminus1_owner_ship_never_backsolved_from_mass():
    row=sample_row()
    row["historical_Tminus1_owner_ship"]["status"] = "ABSTAIN_TMINUS1_OWNER_SHIP_NOT_SEEN"
    assert M.no_mass_oracle_forecast(row)["status"] == "ABSTAIN_TMINUS1_OWNER_SHIP_UNRESOLVED"


def test_frozen_horwasp_population_must_be_complete(monkeypatch):
    monkeypatch.setattr(M,"freeze_census",lambda source:[
        sample_row(vcr_id=1778,mass=950)
    ])
    with pytest.raises(ValueError,match="incomplete Horwasp cohort"):
        M.build_report({},"synthetic")


def test_vcr_id_chain_hypothetical_separation_by_full_population(monkeypatch):
    rows=[
        sample_row(vcr_id=1780,mass=725),
        sample_row(vcr_id=1779,mass=893),
        sample_row(vcr_id=1778,mass=950),
    ]
    # Add 23 other distinct ship IDs: full 26-side synthetic cohort.
    rows += [
        sample_row(vcr_id=2000+i,mass=950,ship=10000+i)
        for i in range(23)
    ]
    monkeypatch.setattr(M,"freeze_census",lambda source: rows)
    report=M.build_report({}, "example-git-blob")
    assert report["summary_all_26"]["sides"] == 26
    assert report["summary_first_by_VCR_ID"]["sides"] == 24
    assert report["summary_repeated_by_VCR_ID"]["sides"] == 2
    assert report["summary_first_by_VCR_ID"]["no_carrier_numeric_matches"] == 24
    assert report["summary_repeated_by_VCR_ID"]["no_carrier_numeric_matches"] == 0
    chain=report["repeated_ship_VCR_ID_chains"][0]
    assert chain["VCR_ID_order_is_proven_host_execution_order"] is False
    assert [c["vcr_id"] for c in chain["VCRs_by_id_NOT_proven_execution_sequence"]]==[
        1778,1779,1780
    ]
    assert [c["factual_minus_preceding_VCR_mass_KT"] for c in chain[
        "VCRs_by_id_NOT_proven_execution_sequence"
    ]] == [None,-57,-168]


def test_blob_pin_and_runner(tmp_path):
    raw=b"immutable Horwasp evidence"
    assert M.git_blob_sha1(raw)==hashlib.sha1(
        b"blob "+str(len(raw)).encode()+b"\0"+raw
    ).hexdigest()
    assert M.git_blob_sha1(raw+b"!")!=M.git_blob_sha1(raw)
    run=ROOT/"tools/run-combat-mass-horwasp-tminus1-first-vcr-v1.sh"
    wrapper=ROOT/"tools/run-combat-mass-horwasp-tminus1-first-vcr-v1-with-evidence.sh"
    for s in (run,wrapper):
        subprocess.run(["bash","-n",str(s)],check=True)
    assert "mass-late-residual-prestate-audit-v1/published/report.json" in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrapper.read_text()
    assert "CURRENT" not in run.read_text()
