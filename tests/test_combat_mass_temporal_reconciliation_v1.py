from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"diagnostics"/"combat_mass_temporal_reconciliation_v1.py"
S=importlib.util.spec_from_file_location("temporal_mass_check",SCRIPT)
assert S is not None and S.loader is not None
M=importlib.util.module_from_spec(S)
sys.modules[S.name]=M
S.loader.exec_module(M)


def _control(changes):
    return {
        "status":"SAME_CHANGE_SET_ACROSS_AVAILABLE_TMINUS1_PERSPECTIVES",
        "perspectives":2,"max_mass_changed_hulls":len(changes),
        "per_perspective":[{
            "change_details_truncated":False,"changed_hull_count":len(changes),
            "changed_hulls":[{"hull_id":hid,"first_mass":old,"Tminus1_mass":new}
                             for hid,old,new in changes],
        } for _ in range(2)],
        "per_perspective_truncated":False,
    }


def test_independent_per_perspective_hull_changes():
    control=_control([(117,125,145),(119,165,185),(1039,96,46)])
    value=M._control_mass_map(control)
    assert value[117]=={"first_mass":125,"Tminus1_mass":145}
    assert value[1039]["Tminus1_mass"]==46
    control["per_perspective"][1]["changed_hulls"][0]["Tminus1_mass"]=150
    with pytest.raises(ValueError,match="disagree"):
        M._control_mass_map(control)


def test_horwasp_full_load_known_and_unknown_clans():
    base={
        "game_id":217591,"turn":149,"vcr_id":2405,"side":"left",
        "ship_id":119,"race":12,"hull_id":117,
        "observed_vcr_mass":290,"catalog_hull_mass":125,
        "catalog_cargo_capacity":900,"VCR_left_baycount":0,
        "tminus1_owner_clans":900,
        "tminus1_owner_engine_id":7,
        "original_class":"horwasp_other_or_catalog_conflict",
    }
    result=M._classify_temporal(base,145)
    assert result["arithmetic_candidates"][0]["mass_candidate"]==290
    assert result["arithmetic_candidates"][0]["Tminus1_full_load_independently_seen"] is True
    other={**base,"side":"right","vcr_id":2421,"ship_id":253,
           "observed_vcr_mass":650,"VCR_left_baycount":10,
           "tminus1_owner_clans":None}
    candidate=M._classify_temporal(other,145)["arithmetic_candidates"][0]
    assert candidate["right_carrier_bonus_assumed"]==360
    assert candidate["Tminus1_full_load_independently_seen"] is None


def test_D19c_uses_Tminus1_static_not_earliest_catalog():
    row={
        "game_id":325434,"turn":149,"vcr_id":1075,"side":"left",
        "ship_id":274,"race":4,"hull_id":1039,
        "catalog_hull_mass":96,"observed_vcr_mass":48,
        "tminus1_owner_engine_id":1,"VCR_left_baycount":0,
        "geometry":{"exact_site_generators":2,
                    "tminus1_participant_at_site":True},
        "original_class":"unexplained_with_available_owner_geometry",
    }
    got=M._classify_temporal(row,46)
    assert got["Tminus1_static_mass"]==46
    assert got["arithmetic_candidates"][0]["mass_candidate"]==48
    assert got["arithmetic_candidates"][0]["Tminus1_site_support_for_assumed_n"] is True


def test_capture_inputs_not_inferred_from_post_battle_Victorious():
    case0={"vcr_id":1016,"owner_id":5,"same_site":[1455,2615],
           "factual_mass":645,
           "rush_start_state":{"hullid":94,"objectid":27,"crew":28,"mass":645}}
    case1={"vcr_id":1017,"owner_id":4,"same_site":[1455,2615],
           "factual_mass":795,
           "rush_start_state":{"hullid":94,"objectid":27,"crew":10,"mass":795}}
    obj={
        "Rush_VCR_sequence":{"VCRs":[case0,case1]},
        "Rush_owner_snapshots":{
            "owner5_Tminus1_Rush27":[{"engineid":9,"hullid":94}],
            "owner4_Tminus1_Saber_at_site":[{"ship_id":406}],
        },
    }
    out=M.capture_candidate(obj)
    assert out["independent_candidate_formula"]["candidate_second_combat_mass_KT"]==795
    assert out["later_T201_id27_Victorious_is_NOT_assumed_continuous_with_Rush"]
    obj["Rush_owner_snapshots"]["owner5_Tminus1_Rush27"][0]["engineid"]=1
    with pytest.raises(ValueError,match="original Rush engine"):
        M.capture_candidate(obj)


def test_runner_uses_existing_files_without_database():
    a=ROOT/"tools"/"run-combat-mass-temporal-reconciliation-v1.sh"
    b=ROOT/"tools"/"run-combat-mass-temporal-reconciliation-v1-with-evidence.sh"
    subprocess.run(["bash","-n",str(a)],check=True)
    subprocess.run(["bash","-n",str(b)],check=True)
    assert "mass-capture-phase-controls-v1/published/report.json" in a.read_text()
    assert "mass-residual-complete-v1/published/residuals.json" in a.read_text()
    assert "run-with-runtime-evidence.sh" in b.read_text()
