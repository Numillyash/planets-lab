from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"diagnostics"/"combat_mass_composition_signatures_v2.py"
SPEC=importlib.util.spec_from_file_location("combat_mass_composition_signatures_v2", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def _side(*, side="right", race=4, hull=451, mass=751, carrier=True,
          orig="unresolved_mass_residual", ship=1):
    return {
        "category":orig,
        "race_id":race, "hull_mass":hull,
        "federation_adjusted_base":hull+(50 if race==1 else 0),
        "factual_mass":mass,
        "side":side, "left_carrier_observed":carrier,
        "hull_id":99, "ship_id":ship,
    }


@pytest.mark.parametrize("given,expected",[
    (_side(mass=751), "two_transwarp_shield_generators_numeric_candidate"),
    (_side(mass=601,carrier=False), "one_transwarp_shield_generator_numeric_candidate"),
    (_side(mass=1111), "two_generators_plus_360_numeric_candidate"),
    (_side(mass=961), "one_generator_plus_360_numeric_candidate"),
    (_side(race=12,hull=145,mass=650), "horwasp_double_plus_360_candidate"),
    (_side(race=12,hull=145,mass=287), "horwasp_partial_load_numeric_candidate"),
    (_side(race=12,hull=31,mass=34), "horwasp_partial_load_numeric_candidate"),
    (_side(race=12,hull=145,mass=647), "horwasp_partial_plus_360_numeric_candidate"),
    (_side(race=12,hull=125,mass=650), "unresolved_nonadditive"),
    (_side(race=1,hull=120,mass=530,orig="federation_adjusted_threshold_candidate"),
     "fed_threshold_ordering_hypothesis"),
    (_side(race=12,hull=145,mass=290,orig="horwasp_full_load_endpoint_candidate"),
     "horwasp_full_cargo_endpoint_candidate"),
    (_side(race=4,hull=451,mass=451,orig="classic_hull_threshold"),
     "original_classic_candidate"),
])
def test_numeric_signatures_never_promote_a_host_rule(given,expected):
    got=M.classify_side(given)
    assert got["signature"]==expected
    assert got["factual_mass"]==given["factual_mass"]
    assert got["hull_mass"]==given["hull_mass"]
    assert "NOT independent observation" in got["evidence_boundary"]


def test_additive_plus_360_is_not_inferred_if_not_on_right_vs_carrier():
    result=M.classify_side(_side(side="left",mass=1111,carrier=True))
    assert result["signature"]=="unresolved_nonadditive"
    result=M.classify_side(_side(side="right",mass=1111,carrier=False))
    assert result["signature"]=="unresolved_nonadditive"


def test_signature_report_preserves_original_side_counts():
    original={
        "schema":M.INPUT_SCHEMA,
        "summary":{
            "ship_vs_ship_vcrs_compared":2,
            "classic_hull_threshold":1,
            "federation_adjusted_threshold_candidate":1,
            "horwasp_full_load_endpoint_candidate":0,
            "unresolved_mass_residual":2,
        },
        "per_turn":[{
            "game_id":217591,"turn":149,
            "rows":[
                {"vcr_id":2390,"sides":[
                    _side(orig="classic_hull_threshold",race=8,
                          hull=980,mass=980,side="left",ship=16),
                    _side(orig="federation_adjusted_threshold_candidate",
                          race=1,hull=120,mass=530,ship=220),
                ]},
                {"vcr_id":2391,"sides":[
                    _side(race=4, hull=451,mass=751,ship=434,side="left"),
                    _side(race=12,hull=125,mass=650,ship=119),
                ]},
            ],
        }],
    }
    result=M.build_signature_report(original,source_path="test.json")
    assert result["status"]=="OBSERVATIONAL_NUMERIC_SIGNATURES_NOT_PROMOTED"
    assert result["summary"]["ship_side_observations"]==4
    assert result["summary"]["original_unresolved_mass_sides"]==2
    assert result["summary"]["remaining_unresolved_numeric_sides"]==1
    assert result["summary"]["newly_grouped_as_numeric_candidates"]==1
    assert result["by_race"]["4"]["two_transwarp_shield_generators_numeric_candidate"]==1
    assert len(result["examples_by_signature"]["fed_threshold_ordering_hypothesis"])==1
    original["summary"]["ship_vs_ship_vcrs_compared"]=3
    with pytest.raises(ValueError,match="counted VCRs mismatch"):
        M.build_signature_report(original,source_path="test.json")


def test_classification_fails_closed_on_missing_or_invalid_fields():
    item=_side()
    item.pop("factual_mass")
    with pytest.raises(ValueError,match="required provenance"):
        M.classify_side(item)
    item=_side()
    item["factual_mass"]=True
    with pytest.raises(ValueError,match="integer"):
        M.classify_side(item)


def test_mass_signatures_runner_is_read_only_and_sha_pinned():
    runner=ROOT/"tools"/"run-combat-mass-composition-signatures-v2.sh"
    wrapper=ROOT/"tools"/"run-combat-mass-composition-signatures-v2-with-evidence.sh"
    subprocess.run(["bash","-n",str(runner)],check=True)
    subprocess.run(["bash","-n",str(wrapper)],check=True)
    script=runner.read_text(encoding="utf-8")
    assert 'GENERATION="generations/corpus-v2compact-public100-' in script
    assert 'EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"' in script
    assert "artifacts/combat/mass-crossgame-controls-v1/public100-mass-controls.json" in script
    assert "run-with-runtime-evidence.sh" in wrapper.read_text(encoding="utf-8")
