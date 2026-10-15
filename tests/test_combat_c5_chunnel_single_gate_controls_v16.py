from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/diagnostics/combat_c5_chunnel_single_gate_controls_v16.py"
SPEC=importlib.util.spec_from_file_location("chunnel_single_gate_v16",SCRIPT)
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def ship(x,y,*,hull=56,code="abc",warp=0,fuel=100,mission=0,mission_target=0):
    return {
        "x":x,"y":y,"hullid":hull,"friendlycode":code,
        "warp":warp,"neutronium":fuel,
        "mission":mission,"mission1target":mission_target,
    }


def pair(*,fuel=100,target_fuel=20,target_warp=0,distance=200,actor_warp=0,tow=False):
    rows={
        293:(10,ship(100,100,code="646",fuel=fuel,warp=actor_warp)),
        646:(10,ship(100+distance,100,warp=target_warp,fuel=target_fuel)),
    }
    if tow:
        rows[701]=(10,ship(100,100,mission=M.TOW_MISSION_ID,
                           mission_target=646))
    return rows


def test_positive_exact_gate_and_numeric_code_safety():
    candidates,reason=M.potential_stock_edges(pair())
    assert len(candidates)==1
    assert candidates[0]["cohort"]=="ALL_TMINUS1_GATES_PASS"
    assert candidates[0]["target_ship_id"]==646
    assert candidates[0]["single_failing_gate"] is None
    assert candidates[0]["actual_Chunnel_activation_proven"] is False
    assert reason["ALL_TMINUS1_GATES_PASS"]==1
    assert not any("friendlycode" in key for key in candidates[0])


@pytest.mark.parametrize("changes,failed",[
    ({"fuel":49},"INITIATOR_FUEL_LT50"),
    ({"target_fuel":0},"TARGET_NO_FUEL"),
    ({"target_warp":2},"TARGET_WARP_NONZERO_AT_TMINUS1"),
    ({"distance":99},"DISTANCE_BELOW_100_AT_TMINUS1"),
    ({"tow":True},"TOW_REQUEST_ON_ENDPOINT_AT_TMINUS1"),
])
def test_single_failed_gate_preselects_negative_before_T(changes,failed):
    candidates,counts=M.potential_stock_edges(pair(**changes))
    assert len(candidates)==1
    assert candidates[0]["cohort"]=="ONE_TMINUS1_GATE_FAILS"
    assert candidates[0]["single_failing_gate"]==failed
    assert counts[failed]==1


def test_multiple_failed_gates_and_nonstationary_actor_abstain():
    rows,counts=M.potential_stock_edges(pair(fuel=10,target_warp=2))
    assert rows==()
    assert counts["MULTIPLE_GATES_FAIL_ABSTAIN"]==1
    rows,counts=M.potential_stock_edges(pair(actor_warp=1))
    assert rows==()
    assert counts["MOVING_INITIATOR_PHASE_POSITION_UNKNOWN_ABSTAIN"]==1


def test_ambiguous_same_owner_suffix_fails_closed():
    rows=pair()
    rows[1646]=(10,ship(400,400))
    outcome,reason=M.potential_stock_edges(rows)
    assert outcome==()
    assert reason["AMBIGUOUS_TARGET_IDS_ABSTAIN"]==1


def test_owner_mismatch_and_non_firecloud_hull_not_assumed_target():
    rows=pair()
    rows[646]=(9,rows[646][1])
    outcome,reason=M.potential_stock_edges(rows)
    assert outcome==()
    assert reason["NO_SAME_OWNER_STOCK_TARGET"]==1
    rows=pair()
    rows[646]=(10,ship(300,100,hull=14))
    outcome,reason=M.potential_stock_edges(rows)
    assert outcome==()
    assert reason["NO_SAME_OWNER_STOCK_TARGET"]==1


def test_posthost_at_target_not_proof_and_abstentions():
    candidate=M.potential_stock_edges(pair())[0][0]
    actual={
        293:(10,ship(300,100,fuel=50)),
        646:(10,ship(300,100,fuel=20)),
    }
    row=M.compare_observations(candidate,actual,game=1,turn=2)
    assert row["T_actor_observation_status"]=="T_ACTOR_AT_PRESELECTED_TMINUS1_TARGET"
    assert row["T_actor_net_fuel_delta_KT"]==50
    assert row["Host_chunnel_activation_or_failure_proven"] is False
    altered=M.compare_observations(candidate,{
        293:(11,ship(300,100,fuel=50)),646:actual[646]
    },game=1,turn=2)
    assert altered["T_actor_observation_status"]=="ABSTAIN_T_OWNER_DRIFT"
    missing=M.compare_observations(candidate,{646:actual[646]},game=1,turn=2)
    assert missing["T_actor_observation_status"]=="ABSTAIN_OWNER_CURRENT_T_UNAVAILABLE"


def test_frozen_v15_source_enforces_95_positive_rows_and_60_windows():
    keys=[]
    for i in range(95):
        game=100+i//5
        keys.append({
            "game_id":game,"turn":30,"initiator_ship_id":i+1,
            "target_ship_id":i+201,
            "T_actor_observation_status":"T_ACTOR_AT_FROZEN_TARGET",
            "Chunnel_execution_proven":False,
            "T_actor_net_fuel_delta_KT":50,
        })
    meta=[{"game_id":game,"turn":turn}
          for game in range(100,120) for turn in (30,60,90)]
    doc={
        "schema":M.v15.SCHEMA,"status":M.v15.STATUS,
        "source_v14_git_blob_sha1":M.v15.V14_BLOB,
        "source_db_sha256":M.SHA256,
        "summary":{
            "frozen_V14_metadata_windows":60,"frozen_V14_games":20,
            "V14_conditional_passenger_comparisons_rechecked":55,
            "Tminus1_actor_edges_rechecked":95,
            "Tminus1_passenger_bearing_actor_edges":22,
            "Tminus1_negative_controls_rechecked":540,
            "T_negative_control_mismatch_count":8,
            "source_context_errors":0,
            "Tminus1_frozen_before_all_T_observations":True,
            "new_Host_movement_or_combat_predictions":0,
            "Chunnel_activation_proven":False,"Nplus1_VCR_used":False,
            "Tminus1_all_actor_target_after_T_outcomes":{
                "T_ACTOR_AT_FROZEN_TARGET":95},
        },
        "actor_target_T_observations":keys,
        "window_denominators":meta,
    }
    windows,originals=M.frozen_v15(doc)
    assert len(windows)==60 and len(originals)==95
    doc["actor_target_T_observations"][0]["Chunnel_execution_proven"]=True
    with pytest.raises(ValueError,match="V15 actor"):
        M.frozen_v15(doc)


def test_runner_wrapper_and_immutable_source():
    run=ROOT/"tools/run-combat-c5-chunnel-single-gate-controls-v16.sh"
    wrap=ROOT/"tools/run-combat-c5-chunnel-single-gate-controls-v16-with-evidence.sh"
    subprocess.run(["bash","-n",str(run)],check=True)
    subprocess.run(["bash","-n",str(wrap)],check=True)
    assert M.V15_BLOB in run.read_text()
    assert M.GENERATION in run.read_text()
    assert "/CURRENT" not in run.read_text()
    assert "run-with-runtime-evidence.sh" in wrap.read_text()
