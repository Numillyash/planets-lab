from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
DIAG=ROOT/"tools"/"diagnostics"
if str(DIAG) not in sys.path:
    sys.path.insert(0,str(DIAG))
SOURCE=DIAG/"combat_mass_complete_residuals_v1.py"
SPEC=importlib.util.spec_from_file_location("complete_mass_residuals",SOURCE)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _sources():
    survey={
        "schema":M.SURVEY_SCHEMA,
        "status":"COMPLETE_OBSERVATIONAL_NOT_PROMOTED",
        "identity_sha256":"a"*64,
        "config":{"source_sha":"sourcehead","selection":[[123,[8]]],
                  "max_vcrs_per_turn":150,"db_generation":"test.db"},
    }
    digest={
        "schema":M.DIGEST_SCHEMA,
        "status":"COMPLETE_DIGEST_OBSERVATIONAL_NOT_PROMOTED",
        "source":{"identity_sha256":"a"*64,"source_sha":"sourcehead"},
        "counts":{"unresolved_mass_sides":1,"unresolved_VCR_details_saved":0,
                  "unresolved_VCR_details_unsaved":1},
        "ranked_turns":[{"game_id":123,"turn":8,"unresolved":1}],
    }
    return survey,digest


def _specs():
    return SimpleNamespace(
        hulls={
            1:SimpleNamespace(mass=100,name="Left",cargo_capacity=10,special=""),
            2:SimpleNamespace(mass=125,name="Right",cargo_capacity=15,special=""),
            3:SimpleNamespace(mass=173,name="Saber Shield Generator",cargo_capacity=50,
                              special="Shield Generator"),
        },
        engines={
            1:SimpleNamespace(name="Stardrive 1",cost=SimpleNamespace(megacredits=1)),
        },
    )


def test_strict_selection_fails_closed_on_incomplete_identity():
    survey,digest=_sources()
    assert M.selected_targets(survey,digest)=={(123,8):1}
    digest["source"]["source_sha"]="wrong"
    with pytest.raises(ValueError,match="source commit conflict"):
        M.selected_targets(survey,digest)


def test_ceil_rounding_is_numeric_not_host_activation():
    geo={
        "status":"TMINUS1_OWNER_GEOMETRY_ONLY",
        "engine_cost_mc":1,
        "exact_site_generators":2,
        "same_origin_and_waypoint_generators":2,
        "tminus1_participant_at_site":True,
    }
    result=M.rounding_control(mass=127,base=125,side="right",
                              left_bays=0,geometry=geo)
    assert result["per_generator_floor"]==0
    assert result["per_generator_ceil"]==1
    assert result["status"]=="TMINUS1_SITE_SUPPORT"
    assert any(x["generator_count_assumed"]==2
               and x["same_site_support_for_n"] is True
               for x in result["match_candidates"])
    assert M.rounding_control(mass=127,base=125,side="right",
                              left_bays=0,geometry={})["match_candidates"]==[]
    assert M.rounding_control(mass=487,base=125,side="left",
                              left_bays=0,geometry=geo)["match_candidates"]==[]


def test_horwasp_catalog_alternative_is_not_silently_applied():
    actual=M.horwasp_constraints(mass=290,hull_id=117,hullmass=125,
                                 capacity=900,side="left",left_bays=0)
    assert len(actual)==1
    assert actual[0]["base_source"]=="EXTERNAL_REFERENCE_145_HYPOTHESIS"
    assert [actual[0]["clan_min"],actual[0]["clan_max"]]==[900,900]


def test_full_recovery_of_unsaved_side_with_original_classifier(monkeypatch,tmp_path):
    survey,digest=_sources()
    checkpoint=tmp_path/"checks"
    checkpoint.mkdir()
    (checkpoint/"game-123.json").write_text(json.dumps({
        "schema":M.SURVEY_SCHEMA,"identity":"a"*64,
        "result":{"game_id":123,"status":"ok","turns":[{
            "turn":8,"counts":{
                "side_observations":2,"unique_vcrs_examined":1,
                "class:classic_baseline":1,
                "class:unexplained_with_available_owner_geometry":1,
            },"examples":[],
        }]}
    }),encoding="utf-8")
    payload={
        "x":10,"y":20,"leftownerid":8,"rightownerid":7,
        "left":{"objectid":11,"hullid":1,"raceid":4,"mass":100,"baycount":0},
        "right":{"objectid":99,"hullid":2,"raceid":4,"mass":127,"baycount":0},
    }
    monkeypatch.setattr(M,"combat_vcr_cases_for_turns",lambda *args,**kwargs:{
        (8,1):SimpleNamespace(payload=payload,vcr_id=1,observation_count=2),
    })
    own={
        7:{
            99:{"id":99,"ownerid":7,"hullid":2,"engineid":1,
                "x":10,"y":20,"targetx":10,"targety":20},
            101:{"id":101,"ownerid":7,"hullid":3,"x":10,"y":20,"targetx":10,"targety":20},
            102:{"id":102,"ownerid":7,"hullid":3,"x":10,"y":20,"targetx":10,"targety":20},
        }
    }
    monkeypatch.setattr(M,"_owner_records",lambda *args,**kwargs:
                        (own,set(),Counter()))
    monkeypatch.setattr(M,"_independent_hull_specs",lambda *args:_specs())
    report=M.build_report(conn=object(),survey=survey,digest=digest,
                          checkpoint_dir=checkpoint,db_path="test.db")
    assert report["summary"]["all_residual_vcr_sides_recovered"]==1
    assert report["summary"]["newly_recovered_ids"]==1
    assert report["summary"]["ceil_half_engine_cost_numeric_matches_in_residuals"]==1
    assert report["summary"]["ceil_half_with_tminus1_site_support"]==1
    assert report["all_residual_vcr_sides"][0]["observed_delta_from_base"]==2
    digest["counts"]["unresolved_mass_sides"]=2
    with pytest.raises(ValueError,match="target anomalies"):
        M.build_report(conn=object(),survey=survey,digest=digest,
                       checkpoint_dir=checkpoint,db_path="test.db")


def test_shell_runner_sha_pins_and_publishes_only_bounded_report():
    runner=ROOT/"tools"/"run-combat-mass-complete-residuals-v1.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-complete-residuals-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    s=runner.read_text(encoding="utf-8")
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in s
    assert '--corpus-db-generation "$GENERATION"' in s
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
