from __future__ import annotations

import importlib.util
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/"tools"/"diagnostics"/"combat_mass_prestate_projection_v4.py"
SPEC=importlib.util.spec_from_file_location("mass_prestate_projection_v4",MODULE)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _prestate(*, race=4, hull=96, hull_id=39, engine=7, cost=170,
              clans=0, cap=40, ngens=2, side="left"):
    return {
        "race_id":race,"catalog_hull_mass":hull,
        "catalog_cargo_capacity":cap,"hull_id":hull_id,
        "side":side,"vcr_site":[100,200],
        "owner_tminus1":{
            "archive_turn":155,
            "participant":{
                "raw":{"x":100,"y":200,"targetx":100,"targety":200},
                "engine_id":engine,"engine_cost_mc":cost,"clans":clans,
            },
            "owner_shield_generators_at_vcr_coordinates":[
                {"ship_id":i,"x":100,"y":200} for i in range(ngens)
            ],
        },
    }


def test_quantum7_generator_counterfactual_uses_half_engine_mc() -> None:
    state=_prestate()
    untouched=deepcopy(state)
    outcome=M.project_mass_candidates(state)
    assert state==untouched
    assert outcome["projection_status"]=="SHIELD_GENERATOR_TMINUS1_SITE_CANDIDATES"
    assert outcome["candidate_masses"]==[96,266]
    assert outcome["shield_generator_prestate_support"]["per_generator_mass"]==85
    assert outcome["shield_generator_prestate_support"]["n_generators_capped_at_2"]==2


def test_transwarp_two_generators_and_possible_right_360() -> None:
    result=M.project_mass_candidates(_prestate(
        hull=451,hull_id=35,engine=9,cost=300,side="right"
    ))
    assert result["candidate_masses"]==[451,751,811,1111]
    assert result["shield_generator_prestate_support"]["per_generator_mass"]==150


def test_horwasp_fully_loaded_catalog_mismatch_is_explicit_reference_alternative() -> None:
    state=_prestate(race=12,hull=125,hull_id=117,cap=900,clans=900,
                    side="left",ngens=0)
    result=M.project_mass_candidates(state)
    assert result["candidate_masses"]==[250,290]
    assert result["horwasp_reference_alternative"] is True
    assert any(
        r["scenario"]=="external_reference_brood_145"
        for r in result["candidate_details"]
    )


def test_horwasp_hive_partial_clans_numeric_hypothesis() -> None:
    result=M.project_mass_candidates(_prestate(
        race=12,hull=475,hull_id=115,cap=24000,clans=7752,
        side="left",ngens=0
    ))
    assert result["candidate_masses"]==[628]
    assert result["candidate_details"][0]["rule_status"]=="unverified_linear_clan_fraction"


def test_missing_tminus1_owner_is_not_assumed_to_be_empty() -> None:
    state=_prestate()
    state["owner_tminus1"]=None
    result=M.project_mass_candidates(state)
    assert result["projection_status"]=="TMINUS1_OWNER_SHIP_UNAVAILABLE"
    assert result["candidate_masses"]==[]


def test_moved_ship_cannot_prove_generator_bonus_while_at_different_tminus1_xy() -> None:
    state=_prestate()
    state["owner_tminus1"]["participant"]["raw"]["x"]=10
    result=M.project_mass_candidates(state)
    assert result["projection_status"]=="NO_VALID_TMINUS1_GENERATOR_SITE_PROJECTION"
    assert result["candidate_masses"]==[96]


def test_observed_mass_is_never_an_input_of_projection(monkeypatch) -> None:
    rows=[]
    for i in range(14):
        state=_prestate()
        rows.append({
            "game_id":371631,"turn":156,"vcr_id":1000+i,
            "side":"left","ship_id":262+i,
            "race_id":4,"catalog_hull_mass":96,
            "catalog_cargo_capacity":40,"hull_id":39,"vcr_site":[100,200],
            "signature":"unresolved_nonadditive" if i<6 else "two_transwarp_shield_generators_numeric_candidate",
            "factual_combat_mass":266 if i!=7 else 500,
            "owner_perspective_snapshots":[state["owner_tminus1"]],
        })
    src={"schema":M.SOURCE_SCHEMA,"observations":rows}
    original=M.project_mass_candidates
    passed=[]
    def check_without_mass(value):
        assert "factual_combat_mass" not in value
        assert "factual_mass" not in value
        passed.append(1)
        return original(value)
    monkeypatch.setattr(M,"project_mass_candidates",check_without_mass)
    report=M.build_report(src,path="fixture")
    assert len(passed)==14
    assert report["summary"]["evaluated_factual_sides"]==14
    assert report["summary"]["original_six_match"]==6
    assert report["summary"]["numeric_candidate_nonmatch"]==1
    assert report["summary"]["distinct_ship_game_turn_groups"]==14


def test_truncated_source_or_bad_clan_input_fails_closed() -> None:
    with pytest.raises(ValueError,match="14 published"):
        M.build_report({"schema":M.SOURCE_SCHEMA,"observations":[]},path="x")
    with pytest.raises(ValueError,match="clans exceed"):
        M.project_mass_candidates(_prestate(
            race=12,hull=145,hull_id=117,cap=900,clans=901
        ))


def test_shell_runners_use_explicit_db_and_previous_v3_json():
    runner=ROOT/"tools"/"run-combat-mass-prestate-projection-v4.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-prestate-projection-v4-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    s=runner.read_text(encoding="utf-8")
    assert '--input "$INPUT"' in s
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in s
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
